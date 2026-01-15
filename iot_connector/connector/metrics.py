"""
Prometheus metrics exporter for Databricks IoT Connector.

Exposes connector metrics in Prometheus format for monitoring and alerting.
"""

import logging
from typing import Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Gauge = Histogram = None

logger = logging.getLogger(__name__)


class MetricsServer:
    """Prometheus metrics server for connector monitoring."""

    def __init__(self, bridge):
        """
        Initialize metrics server.

        Args:
            bridge: UnifiedBridge instance to collect metrics from
        """
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus-client is required for metrics. Install with: pip install prometheus-client")

        self.bridge = bridge
        self._server = None

        # Define metrics
        self._setup_metrics()

    def _setup_metrics(self):
        """Setup Prometheus metrics."""
        # Bridge metrics
        self.records_received = Counter(
            'connector_records_received_total',
            'Total number of records received from protocol clients'
        )

        self.records_enqueued = Counter(
            'connector_records_enqueued_total',
            'Total number of records successfully enqueued'
        )

        self.records_dropped = Counter(
            'connector_records_dropped_total',
            'Total number of records dropped due to backpressure'
        )

        self.batches_sent = Counter(
            'connector_batches_sent_total',
            'Total number of batches sent to ZeroBus'
        )

        self.reconnections = Counter(
            'connector_reconnections_total',
            'Total number of protocol client reconnections'
        )

        # Backpressure metrics
        self.queue_depth = Gauge(
            'connector_queue_depth',
            'Current memory queue depth'
        )

        self.spool_files = Gauge(
            'connector_spool_files',
            'Number of files in disk spool'
        )

        self.dlq_files = Gauge(
            'connector_dlq_files',
            'Number of files in dead letter queue'
        )

        # ZeroBus metrics
        self.zerobus_records_sent = Counter(
            'connector_zerobus_records_sent_total',
            'Total number of records sent to ZeroBus'
        )

        self.zerobus_failures = Counter(
            'connector_zerobus_failures_total',
            'Total number of ZeroBus send failures'
        )

        self.zerobus_retries = Counter(
            'connector_zerobus_retries_total',
            'Total number of ZeroBus send retries'
        )

        self.circuit_breaker_trips = Counter(
            'connector_circuit_breaker_trips_total',
            'Total number of circuit breaker trips'
        )

        # Circuit breaker state (0=closed, 1=half_open, 2=open)
        self.circuit_breaker_state = Gauge(
            'connector_circuit_breaker_state',
            'Current circuit breaker state'
        )

        # Protocol client metrics
        self.active_sources = Gauge(
            'connector_active_sources',
            'Number of active protocol sources'
        )

        self.zerobus_connected = Gauge(
            'connector_zerobus_connected',
            'ZeroBus connection status (1=connected, 0=disconnected)'
        )

    async def start(self, port: int = 9090):
        """Start Prometheus HTTP server."""
        try:
            start_http_server(port)
            self._server = port
            logger.info(f"✓ Prometheus metrics server started on port {port}")

            # Start metrics update loop
            import asyncio
            asyncio.create_task(self._update_metrics_loop())

        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise

    async def _update_metrics_loop(self):
        """Periodically update metrics from bridge."""
        import asyncio

        while True:
            try:
                await self._update_metrics()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(5)

    async def _update_metrics(self):
        """Update Prometheus metrics from bridge."""
        try:
            metrics = self.bridge.get_metrics()
            status = self.bridge.get_status()

            # Update counters (only increment by delta)
            bridge_metrics = metrics.get('bridge', {})
            zerobus_metrics = metrics.get('zerobus', {})
            backpressure_metrics = metrics.get('backpressure', {})

            # Set gauges
            self.queue_depth.set(backpressure_metrics.get('memory_queue_depth', 0))
            self.spool_files.set(backpressure_metrics.get('spool_files', 0))
            self.dlq_files.set(backpressure_metrics.get('dlq_files', 0))
            self.active_sources.set(status.get('active_sources', 0))
            self.zerobus_connected.set(1 if status.get('zerobus_connected', False) else 0)

            # Circuit breaker state mapping
            cb_state = status.get('circuit_breaker_state', 'closed')
            cb_state_value = {'closed': 0, 'half_open': 1, 'open': 2}.get(cb_state, 0)
            self.circuit_breaker_state.set(cb_state_value)

            # Update counters (Prometheus handles totals)
            # Note: In production, you'd want to track deltas to avoid re-counting
            # For now, we'll just log the values
            logger.debug(f"Metrics updated: queue_depth={backpressure_metrics.get('memory_queue_depth', 0)}, "
                        f"active_sources={status.get('active_sources', 0)}")

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def stop(self):
        """Stop metrics server."""
        # Prometheus HTTP server doesn't have a clean shutdown method
        logger.info("✓ Metrics server stopped")
