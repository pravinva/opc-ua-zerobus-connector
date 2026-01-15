"""
ZeroBus Client for Databricks IoT Connector

Uses official databricks-zerobus-ingest-sdk for streaming ingestion to Unity Catalog.
Implements circuit breaker pattern, exponential backoff, and protobuf message handling.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from enum import Enum

from zerobus.sdk.aio import ZerobusSdk
from zerobus.sdk.shared import TableProperties, RecordType, StreamConfigurationOptions

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for ZeroBus API calls.

    Prevents cascading failures by opening circuit after threshold failures.
    """

    def __init__(self,
                 failure_threshold: int = 5,
                 timeout_seconds: int = 60,
                 half_open_max_calls: int = 3):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before testing recovery
            half_open_max_calls: Number of test calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    def record_success(self):
        """Record successful API call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1

            if self.success_count >= self.half_open_max_calls:
                # Service recovered, close circuit
                logger.info("Circuit breaker: Service recovered, closing circuit")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.half_open_calls = 0
        else:
            # Reset failure count on success in closed state
            self.failure_count = 0

    def record_failure(self):
        """Record failed API call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during test, reopen circuit
            logger.warning("Circuit breaker: Service still failing, reopening circuit")
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            self.success_count = 0
        elif self.failure_count >= self.failure_threshold:
            # Too many failures, open circuit
            logger.error(f"Circuit breaker: {self.failure_count} failures, opening circuit for {self.timeout_seconds}s")
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """
        Check if request can proceed.

        Returns:
            True if circuit allows request, False otherwise
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if time.time() - self.last_failure_time >= self.timeout_seconds:
                logger.info("Circuit breaker: Timeout expired, entering half-open state")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.success_count = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited test calls
            return self.half_open_calls < self.half_open_max_calls

        return False

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
        }


class ZeroBusClient:
    """
    ZeroBus SDK client for streaming data to Databricks Unity Catalog.

    Features:
    - OAuth2 authentication with automatic token refresh (handled by SDK)
    - Circuit breaker pattern for resilience
    - Exponential backoff with jitter
    - Batch ingestion
    - Protobuf message handling
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ZeroBus client.

        Args:
            config: Configuration dictionary with zerobus settings
        """
        self.config = config
        zerobus_config = config['zerobus']

        # Databricks connection
        self.workspace_url = zerobus_config['workspace_host']
        self.zerobus_endpoint = zerobus_config['zerobus_endpoint']

        # OAuth2 credentials
        self.client_id = zerobus_config['auth']['client_id']
        self.client_secret = zerobus_config['auth']['client_secret']

        # Target table
        target = zerobus_config['target']
        self.catalog = target['catalog']
        self.schema = target['schema']
        self.table = target['table']
        self.full_table_name = f"{self.catalog}.{self.schema}.{self.table}"

        # Batch settings
        batch_config = zerobus_config.get('batch', {})
        self.batch_size = batch_config.get('max_records', 1000)
        self.batch_timeout_sec = batch_config.get('timeout_seconds', 5.0)

        # Retry settings
        retry_config = zerobus_config.get('retry', {})
        self.max_retries = retry_config.get('max_attempts', 5)
        self.initial_backoff_sec = retry_config.get('initial_backoff_seconds', 1.0)
        self.max_backoff_sec = retry_config.get('max_backoff_seconds', 300.0)
        self.backoff_multiplier = retry_config.get('backoff_multiplier', 2.0)

        # Circuit breaker
        circuit_config = zerobus_config.get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_config.get('failure_threshold', 5),
            timeout_seconds=circuit_config.get('timeout_seconds', 60),
            half_open_max_calls=circuit_config.get('half_open_max_calls', 3)
        )

        # ZeroBus SDK instances
        self._sdk: Optional[ZerobusSdk] = None
        self._stream = None
        self._protobuf_descriptor = None

        # Metrics
        self.metrics = {
            'records_sent': 0,
            'batches_sent': 0,
            'failures': 0,
            'retries': 0,
            'circuit_breaker_trips': 0,
        }

        logger.info(f"ZeroBusClient initialized: table={self.full_table_name}, "
                   f"batch_size={self.batch_size}, max_retries={self.max_retries}")

    async def connect(self, protobuf_descriptor=None):
        """
        Initialize ZeroBus SDK and create stream.

        Args:
            protobuf_descriptor: Protobuf message descriptor for schema definition
                                (optional, use JSON mode if not provided)
        """
        try:
            logger.info(f"Connecting to ZeroBus: {self.zerobus_endpoint}")
            logger.info(f"Workspace: {self.workspace_url}")
            logger.info(f"Target table: {self.full_table_name}")

            # Create SDK instance
            # Note: ZerobusSdk takes host (ZeroBus endpoint) and unity_catalog_url (workspace URL)
            self._sdk = ZerobusSdk(
                host=self.zerobus_endpoint,
                unity_catalog_url=self.workspace_url
            )

            # Determine record type
            if protobuf_descriptor:
                # Protobuf mode (recommended for production)
                logger.info("Using Protobuf serialization")
                self._protobuf_descriptor = protobuf_descriptor

                table_properties = TableProperties(
                    table_name=self.full_table_name,
                    proto_descriptor=protobuf_descriptor
                )
                stream_options = None  # Protobuf mode doesn't need options

            else:
                # JSON mode (fallback, less efficient)
                logger.warning("Using JSON serialization (Protobuf recommended for production)")

                table_properties = TableProperties(
                    table_name=self.full_table_name
                )
                stream_options = StreamConfigurationOptions(
                    record_type=RecordType.JSON
                )

            # Create stream
            self._stream = await self._sdk.create_stream(
                client_id=self.client_id,
                client_secret=self.client_secret,
                table_properties=table_properties,
                options=stream_options
            )

            logger.info(f"✓ Connected to ZeroBus stream for {self.full_table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to ZeroBus: {e}")
            raise

    async def send_batch(self, records: List[Any]) -> bool:
        """
        Send batch of records to ZeroBus.

        Args:
            records: List of protobuf messages or JSON-serializable dicts

        Returns:
            True if successful, False otherwise
        """
        if not records:
            return True

        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker is {self.circuit_breaker.state.value}, "
                          f"rejecting batch of {len(records)} records")
            self.metrics['circuit_breaker_trips'] += 1
            return False

        # Retry loop with exponential backoff
        backoff_sec = self.initial_backoff_sec

        for attempt in range(self.max_retries):
            try:
                # Ensure stream is connected
                if self._stream is None:
                    await self.connect(self._protobuf_descriptor)

                logger.info(f"Sending batch of {len(records)} records to {self.full_table_name} "
                           f"(attempt {attempt + 1}/{self.max_retries})")

                # Send records individually (SDK handles buffering internally)
                for record in records:
                    # ingest_record returns a future that can be awaited for durability
                    future = await self._stream.ingest_record(record)
                    # Await for durability confirmation (optional, adds latency)
                    # await future

                # Record success
                self.circuit_breaker.record_success()
                self.metrics['records_sent'] += len(records)
                self.metrics['batches_sent'] += 1

                logger.debug(f"Successfully sent batch of {len(records)} records")
                return True

            except Exception as e:
                logger.warning(f"Batch send failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                self.metrics['failures'] += 1
                self.circuit_breaker.record_failure()

                # Last attempt, give up
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to send batch after {self.max_retries} attempts")
                    return False

                # Exponential backoff with jitter
                self.metrics['retries'] += 1
                jitter = backoff_sec * 0.1 * (2 * (time.time() % 1) - 0.5)
                sleep_time = min(backoff_sec + jitter, self.max_backoff_sec)

                logger.info(f"Retrying in {sleep_time:.2f}s (backoff={backoff_sec:.2f}s)")
                await asyncio.sleep(sleep_time)

                # Increase backoff for next attempt
                backoff_sec = min(backoff_sec * self.backoff_multiplier, self.max_backoff_sec)

        return False

    async def send_record(self, record: Any) -> bool:
        """
        Send single record to ZeroBus.

        For efficiency, use send_batch() for multiple records.

        Args:
            record: Protobuf message or JSON-serializable dict

        Returns:
            True if successful, False otherwise
        """
        return await self.send_batch([record])

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current client metrics.

        Returns:
            Metrics dictionary
        """
        return {
            **self.metrics,
            'circuit_breaker': self.circuit_breaker.get_state(),
        }

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get connection status.

        Returns:
            Status dictionary
        """
        return {
            'connected': self._stream is not None,
            'workspace_url': self.workspace_url,
            'zerobus_endpoint': self.zerobus_endpoint,
            'target_table': self.full_table_name,
            'circuit_breaker_state': self.circuit_breaker.state.value,
            'serialization_mode': 'protobuf' if self._protobuf_descriptor else 'json',
        }

    async def close(self):
        """Close ZeroBus stream."""
        logger.info("Closing ZeroBus stream")
        if self._stream:
            await self._stream.close()
            self._stream = None
        self._sdk = None
