from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass
from typing import Any

from opcua2uc.config import AppConfig
from opcua2uc.metrics import CONNECTED_SOURCES, EVENTS_INGESTED, EVENTS_SENT, EVENTS_DROPPED, QUEUE_DEPTH
from opcua2uc.opcua.subscriber import OpcUaRecord, run_subscription
from opcua2uc.zerobus_stream import ZerobusStreamManager, ZerobusTarget


logger = logging.getLogger("opcua2uc")


@dataclass
class BridgeStatus:
    started_at_ms: int
    connected_sources: int = 0
    events_ingested: int = 0
    events_sent: int = 0
    last_error: str | None = None


class Bridge:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self._status = BridgeStatus(started_at_ms=int(time.time() * 1000))
        self._stop = asyncio.Event()

        self._source_tasks: dict[str, asyncio.Task] = {}
        self._source_stop: dict[str, asyncio.Event] = {}
        self._source_last_error: dict[str, str] = {}
        self._source_stats: dict[str, dict[str, Any]] = {}

        self._zerobus_mgr: ZerobusStreamManager | None = None
        self._zerobus_lock = asyncio.Lock()

    def _update_connected_sources(self) -> None:
        n = sum(1 for t in self._source_tasks.values() if not t.done())
        self._status.connected_sources = n
        CONNECTED_SOURCES.set(n)

    def get_detailed_status(self) -> dict[str, Any]:
        uptime_ms = int(time.time() * 1000) - self._status.started_at_ms
        running = sorted([k for k, t in self._source_tasks.items() if not t.done()])
        return {
            "uptime_ms": uptime_ms,
            "connected_sources": self._status.connected_sources,
            "events_ingested": self._status.events_ingested,
            "events_sent": self._status.events_sent,
            "last_error": self._status.last_error,
            "running_sources": running,
            "source_last_error": dict(self._source_last_error),
            "source_stats": dict(self._source_stats),
        }

    def get_sources(self) -> list[dict[str, Any]]:
        return list(self.cfg.sources)

    def set_config(self, cfg: AppConfig) -> None:
        self.cfg = cfg

    async def _get_zerobus_mgr(self) -> ZerobusStreamManager:
        async with self._zerobus_lock:
            if self._zerobus_mgr is not None:
                return self._zerobus_mgr

            dbx = self.cfg.databricks if isinstance(self.cfg.databricks, dict) else {}
            target = dbx.get("target") if isinstance(dbx.get("target"), dict) else {}
            auth = dbx.get("auth") if isinstance(dbx.get("auth"), dict) else {}
            stream_cfg = dbx.get("stream") if isinstance(dbx.get("stream"), dict) else {}

            table_name = f"{target.get('catalog')}.{target.get('schema')}.{target.get('table')}"

            import os

            client_id_env = str(auth.get("client_id_env") or "DBX_CLIENT_ID")
            client_secret_env = str(auth.get("client_secret_env") or "DBX_CLIENT_SECRET")
            client_id = os.environ.get(client_id_env)
            client_secret = os.environ.get(client_secret_env)
            if not client_id or not client_secret:
                raise RuntimeError("Missing DBX client credentials env vars for Zerobus")

            z = ZerobusTarget(
                workspace_host=str(dbx.get("workspace_host") or "").rstrip("/"),
                zerobus_endpoint=str(dbx.get("zerobus_endpoint") or ""),
                table_name=table_name,
                client_id=client_id,
                client_secret=client_secret,
                stream_cfg=stream_cfg,
            )
            self._zerobus_mgr = ZerobusStreamManager(z)
            return self._zerobus_mgr

    async def start_source(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Missing source name")
        if name in self._source_tasks and not self._source_tasks[name].done():
            return

        src = next((s for s in self.cfg.sources if (s.get("name") or "").strip() == name), None)
        if not src:
            raise KeyError(f"Source not found: {name}")
        endpoint = str(src.get("endpoint") or "").strip()
        if not endpoint:
            raise ValueError(f"Source {name} missing endpoint")

        stop_evt = asyncio.Event()
        self._source_stop[name] = stop_evt
        self._source_last_error.pop(name, None)
        self._source_stats.setdefault(name, {})

        pipe = self.cfg.__dict__.get("pipeline", None)
        if not isinstance(pipe, dict):
            pipe = {}
        queue_max = int(pipe.get("queue_max_size", 10000))
        drop_policy = str(pipe.get("drop_policy", "drop_newest"))
        batch_size = int(pipe.get("batch_size", 50))
        flush_interval_ms = int(pipe.get("flush_interval_ms", 1000))
        max_send_rps = float(pipe.get("max_send_records_per_sec", 500))
        q: asyncio.Queue[OpcUaRecord] = asyncio.Queue(maxsize=max(1, queue_max))

        def on_stats(delta: dict[str, Any]) -> None:
            st = self._source_stats.setdefault(name, {})
            st.update(delta)

        def on_record(rec: OpcUaRecord) -> None:
            try:
                try:
                    q.put_nowait(rec)
                except asyncio.QueueFull:
                    # backpressure: drop based on policy
                    if drop_policy == "drop_oldest":
                        try:
                            _ = q.get_nowait()
                            q.put_nowait(rec)
                        except Exception:
                            pass
                    # drop_newest: just drop rec
                    EVENTS_DROPPED.labels(source=name).inc()
                    return
                self._status.events_ingested += 1
                QUEUE_DEPTH.labels(source=name).set(q.qsize())
                EVENTS_INGESTED.inc()
                st = self._source_stats.setdefault(name, {})
                st["last_event_time_ms"] = rec.event_time_ms
            except Exception:
                pass

        async def sender_loop() -> None:
            # batch + rate limit
            try:
                mgr = await self._get_zerobus_mgr()
                batch: list[dict[str, Any]] = []
                last_flush = time.time()

                # token bucket (records/sec)
                tokens = max_send_rps
                last_tok = time.time()

                async def refill_tokens() -> None:
                    nonlocal tokens, last_tok
                    now = time.time()
                    dt = now - last_tok
                    if dt <= 0:
                        return
                    tokens = min(max_send_rps, tokens + dt * max_send_rps)
                    last_tok = now

                async def send_batch() -> None:
                    nonlocal batch, last_flush
                    if not batch:
                        return
                    # send each record (SDK acks per record)
                    for rec_payload in batch:
                        await mgr.ingest_one(rec_payload)
                        self._status.events_sent += 1
                        EVENTS_SENT.inc()
                    await mgr.flush()
                    # If we successfully flushed, clear any previous sender error for this source.
                    prev_err = self._source_last_error.pop(name, None)
                    if prev_err and self._status.last_error == prev_err:
                        self._status.last_error = None
                    st = self._source_stats.setdefault(name, {})
                    st["last_sent_time_ms"] = int(time.time() * 1000)
                    batch = []
                    last_flush = time.time()

                while not stop_evt.is_set():
                    # try to get a record with timeout so we can flush periodically
                    try:
                        rec = await asyncio.wait_for(q.get(), timeout=flush_interval_ms / 1000.0)
                        QUEUE_DEPTH.labels(source=name).set(q.qsize())
                    except asyncio.TimeoutError:
                        rec = None

                    await refill_tokens()

                    # periodic flush
                    if (time.time() - last_flush) * 1000 >= flush_interval_ms:
                        await send_batch()

                    if rec is None:
                        continue

                    # rate limit: if no tokens, wait a bit
                    while tokens < 1.0 and not stop_evt.is_set():
                        await asyncio.sleep(0.05)
                        await refill_tokens()

                    tokens -= 1.0

                    payload = {
                        # UC TIMESTAMP columns: Zerobus JSON ingestion expects epoch microseconds.
                        # (Epoch milliseconds will decode to dates near 1970.)
                        "event_time": int(rec.event_time_ms) * 1000,
                        "ingest_time": int(time.time() * 1_000_000),
                        "source_name": rec.source_name,
                        "endpoint": rec.endpoint,
                        "namespace": int(rec.namespace),
                        "node_id": rec.node_id,
                        "browse_path": rec.browse_path,
                        "status_code": rec.status_code,
                        "status": rec.status,
                        "value_type": rec.value_type,
                        "value": rec.value,
                        "value_num": rec.value_num,
                        "raw": None,
                    }
                    batch.append(payload)

                    if len(batch) >= batch_size:
                        await send_batch()

            except Exception as e:
                msg = f"SenderLoopError: {type(e).__name__}: {e}"
                self._source_last_error[name] = msg
                self._status.last_error = msg
                logger.exception(msg)
                raise



        async def task_main() -> None:
            sub_task = None
            send_task = None
            try:
                self._update_connected_sources()
                send_task = asyncio.create_task(sender_loop())
                sub_task = asyncio.create_task(
                    run_subscription(
                        source_name=name,
                        endpoint=endpoint,
                        on_record=on_record,
                        stop_evt=stop_evt,
                        on_stats=on_stats,
                        variable_limit=int(src.get("variable_limit", 25)),
                        publishing_interval_ms=int(src.get("publishing_interval_ms", 1000)),
                    )
                )
                await asyncio.wait([sub_task, send_task], return_when=asyncio.FIRST_EXCEPTION)
                for t in (sub_task, send_task):
                    if t and t.done() and t.exception():
                        raise t.exception()  # type: ignore[misc]
            except Exception as e:
                self._source_last_error[name] = f"{type(e).__name__}: {e}"
                self._status.last_error = self._source_last_error[name]
                raise
            finally:
                stop_evt.set()
                for t in (sub_task, send_task):
                    if t and not t.done():
                        t.cancel()
                self._source_tasks.pop(name, None)
                self._source_stop.pop(name, None)
                self._update_connected_sources()

        self._source_tasks[name] = asyncio.create_task(task_main())
        self._update_connected_sources()

    async def stop_source(self, name: str) -> None:
        name = name.strip()
        evt = self._source_stop.get(name)
        if evt:
            evt.set()
        task = self._source_tasks.get(name)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass
        self._source_tasks.pop(name, None)
        self._source_stop.pop(name, None)
        self._update_connected_sources()

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(1.0)

    def request_stop(self) -> None:
        self._stop.set()
