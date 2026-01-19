"""Web server with support for multiple protocol types."""
from __future__ import annotations

from pathlib import Path

from aiohttp import web

from opcua2uc.config import AppConfig, load_config, save_config
from opcua2uc.core.unified_bridge import UnifiedBridge
from opcua2uc.databricks_auth import DatabricksAuthError, oauth_client_credentials_token
from opcua2uc.databricks_token import fetch_zerobus_token
from opcua2uc.databricks_uc import get_table_schema
from opcua2uc.protocols.factory import create_protocol_client, detect_protocol_type
from opcua2uc.wot.wot_bridge import WoTBridge
from opcua2uc.zerobus_producer import ZerobusConfigError, make_sample_bronze_record, zerobus_test_ingest


class UnifiedWebServer:
    """Web server supporting multiple IoT protocols (OPC-UA, MQTT, Modbus)."""

    def __init__(self, bridge: UnifiedBridge, config_path: str, port: int = 8080) -> None:
        self.bridge = bridge
        self.port = port
        self.config_path = config_path

        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self) -> None:
        static_dir = Path(__file__).parent / "static"

        self.app.router.add_get("/", self._serve_index)
        self.app.router.add_static("/static", static_dir)

        self.app.router.add_get("/api/status", self._get_status)

        self.app.router.add_get("/api/sources", self._get_sources)
        self.app.router.add_post("/api/sources", self._add_source)
        self.app.router.add_delete("/api/sources/{name}", self._delete_source)
        self.app.router.add_post("/api/sources/{name}/test", self._test_source)
        self.app.router.add_post("/api/sources/{name}/start", self._start_source)
        self.app.router.add_post("/api/sources/{name}/stop", self._stop_source)
        self.app.router.add_post("/api/sources/from-td", self._add_source_from_td)

        self.app.router.add_get("/api/config", self._get_config)
        self.app.router.add_post("/api/config", self._set_config)
        self.app.router.add_post("/api/config/patch", self._patch_config)

        self.app.router.add_post("/api/databricks/test_auth", self._test_databricks_auth)
        self.app.router.add_post("/api/databricks/test_zerobus_token", self._test_zerobus_token)
        self.app.router.add_get("/api/databricks/table_schema", self._get_table_schema)
        self.app.router.add_get("/api/databricks/env_status", self._get_env_status)

        self.app.router.add_post("/api/zerobus/test_ingest", self._zerobus_test_ingest)

        # New endpoint for protocol detection
        self.app.router.add_post("/api/protocol/detect", self._detect_protocol)

        self.app.router.add_get("/health/live", self._live)
        self.app.router.add_get("/health/ready", self._ready)

    async def _serve_index(self, request: web.Request) -> web.StreamResponse:
        index_path = Path(__file__).parent / "static" / "index.html"
        return web.FileResponse(index_path)

    async def _get_status(self, request: web.Request) -> web.StreamResponse:
        return web.json_response(self.bridge.get_detailed_status())

    async def _get_sources(self, request: web.Request) -> web.StreamResponse:
        return web.json_response(self.bridge.get_sources())

    async def _add_source(self, request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            body = await request.text()
            return web.json_response({"error": "Invalid JSON", "body": body}, status=400)

        if not isinstance(payload, dict):
            return web.json_response({"error": "Source must be a JSON object"}, status=400)

        name = (payload.get("name") or "").strip()
        endpoint = (payload.get("endpoint") or "").strip()
        protocol_type = (payload.get("protocol_type") or "").strip()

        if not name:
            return web.json_response({"error": "Missing field: name"}, status=400)
        if not endpoint:
            return web.json_response({"error": "Missing field: endpoint"}, status=400)

        cfg = load_config(self.config_path)
        if any((s.get("name") or "").strip() == name for s in cfg.sources):
            return web.json_response({"error": f"Source already exists: {name}"}, status=409)

        # Auto-detect protocol if not provided
        if not protocol_type:
            try:
                protocol_type = str(detect_protocol_type(endpoint).value)
            except ValueError:
                protocol_type = "opcua"  # Default to OPC-UA

        source_config = {
            "name": name,
            "endpoint": endpoint,
            "protocol_type": protocol_type,
        }

        # Copy any additional protocol-specific config
        for key in ["topics", "qos", "unit_id", "registers", "poll_interval_ms", "variable_limit", "publishing_interval_ms"]:
            if key in payload:
                source_config[key] = payload[key]

        cfg.sources.append(source_config)
        save_config(self.config_path, cfg)
        self.bridge.set_config(cfg)
        return web.json_response({"ok": True, "source": source_config})

    async def _delete_source(self, request: web.Request) -> web.StreamResponse:
        name = (request.match_info.get("name") or "").strip()
        if not name:
            return web.json_response({"error": "Missing source name"}, status=400)

        cfg = load_config(self.config_path)
        before = len(cfg.sources)
        cfg.sources = [s for s in cfg.sources if (s.get("name") or "").strip() != name]
        if len(cfg.sources) == before:
            return web.json_response({"error": f"Source not found: {name}"}, status=404)

        save_config(self.config_path, cfg)
        self.bridge.set_config(cfg)
        return web.json_response({"ok": True})

    async def _test_source(self, request: web.Request) -> web.StreamResponse:
        """Test connection to a source (works with all protocol types)."""
        name = (request.match_info.get("name") or "").strip()
        if not name:
            return web.json_response({"error": "Missing source name"}, status=400)

        cfg = load_config(self.config_path)
        match = next((s for s in cfg.sources if (s.get("name") or "").strip() == name), None)
        if not match:
            return web.json_response({"error": f"Source not found: {name}"}, status=404)

        endpoint = str(match.get("endpoint") or "").strip()
        if not endpoint:
            return web.json_response({"error": f"Source {name} is missing endpoint"}, status=400)

        # Detect protocol type
        protocol_type = match.get("protocol_type")
        if not protocol_type:
            try:
                protocol_type = detect_protocol_type(endpoint)
            except ValueError:
                protocol_type = "opcua"

        try:
            # Create a temporary client to test connection
            client = create_protocol_client(
                protocol_type=protocol_type,
                source_name=name,
                endpoint=endpoint,
                config=match,
                on_record=lambda _: None,  # No-op
            )

            res = await client.test_connection()

            if not res.ok:
                return web.json_response(
                    {
                        "ok": False,
                        "name": name,
                        "endpoint": endpoint,
                        "protocol_type": res.protocol_type.value,
                        "error": res.error,
                        "duration_ms": res.duration_ms,
                    },
                    status=502,
                )

            response = {
                "ok": True,
                "name": name,
                "endpoint": endpoint,
                "protocol_type": res.protocol_type.value,
                "duration_ms": res.duration_ms,
            }

            if res.server_info:
                response["server_info"] = res.server_info

            return web.json_response(response)

        except Exception as e:
            return web.json_response(
                {
                    "ok": False,
                    "name": name,
                    "endpoint": endpoint,
                    "error": f"{type(e).__name__}: {e}",
                },
                status=500,
            )

    async def _detect_protocol(self, request: web.Request) -> web.StreamResponse:
        """Detect protocol type from endpoint."""
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        endpoint = (payload.get("endpoint") or "").strip()
        if not endpoint:
            return web.json_response({"error": "Missing endpoint"}, status=400)

        try:
            protocol = detect_protocol_type(endpoint)
            return web.json_response({"ok": True, "protocol_type": protocol.value, "endpoint": endpoint})
        except ValueError as e:
            return web.json_response({"ok": False, "error": str(e), "endpoint": endpoint}, status=400)

    async def _start_source(self, request: web.Request) -> web.StreamResponse:
        name = (request.match_info.get("name") or "").strip()
        if not name:
            return web.json_response({"error": "Missing source name"}, status=400)
        try:
            await self.bridge.start_source(name)
            return web.json_response({"ok": True})
        except Exception as e:
            return web.json_response({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=500)

    async def _stop_source(self, request: web.Request) -> web.StreamResponse:
        name = (request.match_info.get("name") or "").strip()
        if not name:
            return web.json_response({"error": "Missing source name"}, status=400)
        try:
            await self.bridge.stop_source(name)
            return web.json_response({"ok": True})
        except Exception as e:
            return web.json_response({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=500)

    async def _get_config(self, request: web.Request) -> web.StreamResponse:
        cfg = load_config(self.config_path)
        return web.json_response(cfg.to_dict())

    async def _set_config(self, request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            body = await request.text()
            return web.json_response({"error": "Invalid JSON", "body": body}, status=400)

        if not isinstance(payload, dict):
            return web.json_response({"error": "Config must be a JSON object"}, status=400)

        try:
            cfg = AppConfig.from_dict(payload)
            save_config(self.config_path, cfg)
            self.bridge.set_config(cfg)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

        return web.json_response({"ok": True})

    async def _test_databricks_auth(self, request: web.Request) -> web.StreamResponse:
        cfg = load_config(self.config_path)
        databricks_cfg = cfg.databricks if isinstance(cfg.databricks, dict) else {}

        try:
            res = await oauth_client_credentials_token(databricks_cfg)
            return web.json_response(res)
        except DatabricksAuthError as e:
            return web.json_response({"ok": False, "error": str(e)}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=500)

    async def _zerobus_test_ingest(self, request: web.Request) -> web.StreamResponse:
        cfg = load_config(self.config_path)
        databricks_cfg = cfg.databricks if isinstance(cfg.databricks, dict) else {}

        # Pick first source for a sample record (or placeholders)
        sources = cfg.sources if isinstance(cfg.sources, list) else []
        if sources and isinstance(sources[0], dict):
            src_name = str(sources[0].get("name") or "default")
            src_ep = str(sources[0].get("endpoint") or "")
        else:
            src_name = "default"
            src_ep = ""

        record = make_sample_bronze_record(source_name=src_name, endpoint=src_ep)

        try:
            res = await zerobus_test_ingest(databricks_cfg, record)
            return web.json_response({"ok": True, "table_name": res.table_name, "stream_id": res.stream_id})
        except ZerobusConfigError as e:
            return web.json_response({"ok": False, "error": str(e)}, status=400)
        except Exception as e:
            return web.json_response({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=500)

    async def _test_zerobus_token(self, request: web.Request) -> web.StreamResponse:
        cfg = load_config(self.config_path)
        databricks_cfg = cfg.databricks if isinstance(cfg.databricks, dict) else {}

        target = databricks_cfg.get("target") if isinstance(databricks_cfg, dict) else None
        if not isinstance(target, dict):
            return web.json_response({"ok": False, "error": "Missing databricks.target"}, status=400)

        table_name = f"{target.get('catalog')}.{target.get('schema')}.{target.get('table')}"

        try:
            token, exp, url = await fetch_zerobus_token(databricks_cfg, table_name)
            return web.json_response(
                {
                    "ok": True,
                    "token_preview": f"{token[:6]}…{token[-4:]}",
                    "expires_at_unix": exp,
                    "token_endpoint_used": url,
                }
            )
        except Exception as e:
            return web.json_response({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=400)

    async def _get_env_status(self, request: web.Request) -> web.StreamResponse:
        import os

        cfg = load_config(self.config_path)
        databricks_cfg = cfg.databricks if isinstance(cfg.databricks, dict) else {}
        auth = databricks_cfg.get("auth") if isinstance(databricks_cfg.get("auth"), dict) else {}

        client_id_env = str(auth.get("client_id_env") or "DBX_CLIENT_ID")
        client_secret_env = str(auth.get("client_secret_env") or "DBX_CLIENT_SECRET")

        cid = os.environ.get(client_id_env)
        csec = os.environ.get(client_secret_env)

        return web.json_response(
            {
                "ok": True,
                "client_id_env": client_id_env,
                "client_secret_env": client_secret_env,
                "client_id_set": bool(cid),
                "client_secret_set": bool(csec),
                "client_id_len": len(cid) if cid else 0,
                "client_secret_len": len(csec) if csec else 0,
            }
        )

    async def _get_table_schema(self, request: web.Request) -> web.StreamResponse:
        cfg = load_config(self.config_path)
        databricks_cfg = cfg.databricks if isinstance(cfg.databricks, dict) else {}

        target = databricks_cfg.get("target") if isinstance(databricks_cfg, dict) else {}
        if not isinstance(target, dict):
            return web.json_response({"ok": False, "error": "Missing databricks.target"}, status=400)

        full_name = f"{target.get('catalog')}.{target.get('schema')}.{target.get('table')}"

        try:
            meta = await get_table_schema(databricks_cfg, full_name)
            cols = meta.get("columns", [])
            return web.json_response({"ok": True, "full_name": full_name, "columns": cols})
        except Exception as e:
            return web.json_response({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=500)

    async def _patch_config(self, request: web.Request) -> web.StreamResponse:
        """Merge-style config update."""
        try:
            patch = await request.json()
        except Exception:
            body = await request.text()
            return web.json_response({"error": "Invalid JSON", "body": body}, status=400)

        if not isinstance(patch, dict):
            return web.json_response({"error": "Patch must be a JSON object"}, status=400)

        cfg = load_config(self.config_path)
        data = cfg.to_dict()

        def deep_merge(dst, src):
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    deep_merge(dst[k], v)
                else:
                    dst[k] = v

        deep_merge(data, patch)

        try:
            new_cfg = AppConfig.from_dict(data)
            save_config(self.config_path, new_cfg)
            self.bridge.set_config(new_cfg)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

        return web.json_response({"ok": True})

    async def _live(self, request: web.Request) -> web.StreamResponse:
        return web.json_response({"status": "live"})

    async def _ready(self, request: web.Request) -> web.StreamResponse:
        return web.json_response({"status": "ready"})

    async def _add_source_from_td(self, request: web.Request) -> web.StreamResponse:
        """Add source from Thing Description URL (W3C WoT support).

        Request:
        {
          "thing_description": "http://simulator:8000/api/opcua/thing-description",
          "name": "ot-simulator"  # Optional, defaults to TD title
        }

        Response:
        {
          "ok": true,
          "name": "ot-simulator",
          "endpoint": "opc.tcp://simulator:4840",
          "protocol_type": "opcua",
          "thing_id": "urn:dev:ops:databricks-ot-simulator",
          "properties": 379,
          "semantic_types": {"mining/crusher_1_motor_power": "saref:PowerSensor", ...}
        }
        """
        try:
            payload = await request.json()
        except Exception:
            body = await request.text()
            return web.json_response({"error": "Invalid JSON", "body": body}, status=400)

        if not isinstance(payload, dict):
            return web.json_response({"error": "Request must be a JSON object"}, status=400)

        td_url = (payload.get("thing_description") or "").strip()
        if not td_url:
            return web.json_response({"error": "Missing field: thing_description"}, status=400)

        override_name = (payload.get("name") or "").strip()

        try:
            # Fetch and parse Thing Description
            wot_bridge = WoTBridge()
            td = await wot_bridge.td_client.fetch_td(td_url)
            thing_config = wot_bridge.td_client.parse_td(td)

            # Use override name if provided, otherwise use TD title
            source_name = override_name if override_name else thing_config.name

            # Check if source already exists
            cfg = load_config(self.config_path)
            if any((s.get("name") or "").strip() == source_name for s in cfg.sources):
                return web.json_response(
                    {"error": f"Source already exists: {source_name}"},
                    status=409
                )

            # Create source config from Thing Description
            source_config = {
                "name": source_name,
                "endpoint": thing_config.endpoint,
                "protocol_type": thing_config.protocol_type.value,
                "thing_description": td_url,
                "thing_id": thing_config.thing_id,
                "semantic_types": thing_config.semantic_types,
                "unit_uris": thing_config.unit_uris,
            }

            # Add protocol-specific config from ThingConfig
            protocol_config = wot_bridge._create_protocol_config(thing_config)
            for key in ["variable_limit", "publishing_interval_ms", "topics", "qos", "unit_id", "registers", "poll_interval_ms", "node_ids"]:
                if key in protocol_config:
                    source_config[key] = protocol_config[key]

            # Save to config
            cfg.sources.append(source_config)
            save_config(self.config_path, cfg)
            self.bridge.set_config(cfg)

            # Return response
            return web.json_response({
                "ok": True,
                "name": source_name,
                "endpoint": thing_config.endpoint,
                "protocol_type": thing_config.protocol_type.value,
                "thing_id": thing_config.thing_id,
                "properties": len(thing_config.properties),
                "semantic_types": thing_config.semantic_types,
                "unit_uris": thing_config.unit_uris,
            })

        except Exception as e:
            return web.json_response(
                {
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                },
                status=500
            )

    async def start(self) -> None:
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
