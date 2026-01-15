"""
Databricks IoT Connector - Main Entry Point

Production-ready DMZ connector for streaming IoT data to Unity Catalog via ZeroBus.

Supports:
- Multi-protocol data collection (OPC-UA, MQTT, Modbus)
- Backpressure management with disk spool
- Circuit breaker pattern for resilience
- OAuth2 M2M authentication
- Web GUI for configuration and monitoring
- Prometheus metrics
- Health check endpoint
"""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from connector.config_loader import ConfigLoader
from connector.bridge import UnifiedBridge
from connector.credential_manager import CredentialManager, CredentialInjector

# Version
__version__ = "1.0.0"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ConnectorApp:
    """Main connector application."""

    def __init__(self, config_file: Path, gui_enabled: bool = True):
        """
        Initialize connector application.

        Args:
            config_file: Path to YAML configuration file
            gui_enabled: Enable web GUI
        """
        self.config_file = config_file
        self.gui_enabled = gui_enabled

        # Components
        self.config_loader = ConfigLoader(config_file)
        self.config: Optional[dict] = None
        self.credential_manager: Optional[CredentialManager] = None
        self.bridge: Optional[UnifiedBridge] = None
        self.web_server = None
        self.metrics_server = None

        # Shutdown flag
        self._shutdown = False

    async def start(self):
        """Start connector application."""
        logger.info("=" * 80)
        logger.info(f"Databricks IoT Connector v{__version__}")
        logger.info("=" * 80)

        try:
            # Load configuration
            logger.info(f"Loading configuration from {self.config_file}")
            self.config = self.config_loader.load()

            if not self.config:
                logger.error("Failed to load configuration")
                return False

            # Initialize credential manager
            self.credential_manager = CredentialManager()

            # Inject credentials into config
            injector = CredentialInjector(self.credential_manager)
            self.config = injector.inject(self.config)

            # Log configuration summary
            self._log_config_summary()

            # Initialize bridge
            logger.info("Initializing UnifiedBridge...")
            self.bridge = UnifiedBridge(self.config)

            # TODO: Set protobuf descriptor once schemas are compiled
            # from connector.protos import iot_record_pb2
            # self.bridge.set_protobuf_descriptor(iot_record_pb2.IotRecord.DESCRIPTOR)

            # Start web GUI if enabled
            if self.gui_enabled:
                await self._start_web_gui()

            # Start metrics server if configured
            metrics_config = self.config.get('monitoring', {}).get('prometheus', {})
            if metrics_config.get('enabled', False):
                await self._start_metrics()

            # Start bridge
            logger.info("Starting data collection and ingestion...")
            await self.bridge.start()

            logger.info("=" * 80)
            logger.info("✓ Connector started successfully")
            logger.info("=" * 80)

            # Print status
            self._print_status()

            return True

        except Exception as e:
            logger.error(f"Failed to start connector: {e}", exc_info=True)
            return False

    async def _start_web_gui(self):
        """Start web GUI server."""
        try:
            from connector.web_gui import WebGUI

            gui_config = self.config.get('web_gui', {})
            host = gui_config.get('host', '0.0.0.0')
            port = gui_config.get('port', 8080)

            logger.info(f"Starting Web GUI on http://{host}:{port}")
            self.web_server = WebGUI(
                bridge=self.bridge,
                config=self.config,
                config_loader=self.config_loader,
                credential_manager=self.credential_manager
            )
            await self.web_server.start(host, port)

        except ImportError:
            logger.warning("Web GUI not available (aiohttp not installed)")
        except Exception as e:
            logger.error(f"Failed to start Web GUI: {e}")

    async def _start_metrics(self):
        """Start Prometheus metrics server."""
        try:
            from connector.metrics import MetricsServer

            metrics_config = self.config.get('monitoring', {}).get('prometheus', {})
            port = metrics_config.get('port', 9090)

            logger.info(f"Starting Prometheus metrics on http://0.0.0.0:{port}/metrics")
            self.metrics_server = MetricsServer(bridge=self.bridge)
            await self.metrics_server.start(port)

        except ImportError:
            logger.warning("Prometheus metrics not available (prometheus-client not installed)")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    def _log_config_summary(self):
        """Log configuration summary."""
        logger.info("Configuration summary:")
        logger.info(f"  Sources: {len(self.config.get('sources', []))}")

        for source in self.config.get('sources', []):
            logger.info(f"    - {source.get('name')}: {source.get('endpoint')}")

        zerobus = self.config.get('zerobus', {})
        target = zerobus.get('target', {})
        logger.info(f"  Target table: {target.get('catalog')}.{target.get('schema')}.{target.get('table')}")

        backpressure = self.config.get('backpressure', {})
        logger.info(f"  Backpressure: queue_size={backpressure.get('max_queue_size', 10000)}, "
                   f"spool={backpressure.get('spool_enabled', True)}")

    def _print_status(self):
        """Print current status."""
        status = self.bridge.get_status()

        logger.info("\nStatus:")
        logger.info(f"  Active sources: {status['active_sources']}")
        logger.info(f"  ZeroBus connected: {status['zerobus_connected']}")
        logger.info(f"  Circuit breaker: {status['circuit_breaker_state']}")

        bp_stats = status['backpressure_stats']
        logger.info(f"  Queue depth: {bp_stats['memory_queue_depth']}/{bp_stats['max_queue_size']}")

        if self.gui_enabled and self.web_server:
            gui_config = self.config.get('web_gui', {})
            host = gui_config.get('host', '0.0.0.0')
            port = gui_config.get('port', 8080)
            logger.info(f"\n  Web GUI: http://{host}:{port}")

    async def stop(self):
        """Stop connector application."""
        if self._shutdown:
            return

        self._shutdown = True
        logger.info("Shutting down connector...")

        try:
            # Stop bridge
            if self.bridge:
                await self.bridge.stop()

            # Stop web GUI
            if self.web_server:
                await self.web_server.stop()

            # Stop metrics
            if self.metrics_server:
                await self.metrics_server.stop()

            logger.info("✓ Connector stopped")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def run_forever(self):
        """Run connector until interrupted."""
        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start connector
        success = await self.start()
        if not success:
            return 1

        # Run until shutdown
        try:
            while not self._shutdown:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            return 1

        return 0


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Databricks IoT Connector - DMZ to Unity Catalog streaming',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default config
  python -m connector

  # Start with custom config
  python -m connector --config /path/to/config.yaml

  # Start without Web GUI
  python -m connector --no-gui

  # Validate configuration only
  python -m connector --validate

  # Test connection to ZeroBus
  python -m connector --test-connection

Version: {version}
        """.format(version=__version__)
    )

    parser.add_argument(
        '--config', '-c',
        type=Path,
        default=Path('config.yaml'),
        help='Path to YAML configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Disable Web GUI'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate configuration and exit'
    )

    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Test connection to ZeroBus and exit'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'Databricks IoT Connector v{__version__}'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )

    return parser.parse_args()


async def validate_config(config_file: Path) -> bool:
    """Validate configuration file."""
    logger.info(f"Validating configuration: {config_file}")

    try:
        loader = ConfigLoader(config_file)
        config = loader.load()

        if not config:
            logger.error("Failed to load configuration")
            return False

        # Validate required fields
        required_fields = ['sources', 'zerobus']
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required field: {field}")
                return False

        # Validate sources
        if not config['sources']:
            logger.error("No sources configured")
            return False

        for source in config['sources']:
            if 'name' not in source or 'endpoint' not in source:
                logger.error(f"Invalid source configuration: {source}")
                return False

        # Validate ZeroBus config
        zerobus = config['zerobus']
        required_zerobus = ['workspace_host', 'zerobus_endpoint', 'auth', 'target']
        for field in required_zerobus:
            if field not in zerobus:
                logger.error(f"Missing required ZeroBus field: {field}")
                return False

        logger.info("✓ Configuration is valid")
        logger.info(f"  Sources: {len(config['sources'])}")
        logger.info(f"  Target: {zerobus['target'].get('catalog')}.{zerobus['target'].get('schema')}.{zerobus['target'].get('table')}")

        return True

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}", exc_info=True)
        return False


async def test_connection(config_file: Path) -> bool:
    """Test connection to ZeroBus."""
    logger.info("Testing ZeroBus connection...")

    try:
        loader = ConfigLoader(config_file)
        config = loader.load()

        if not config:
            logger.error("Failed to load configuration")
            return False

        from connector.zerobus_client import ZeroBusClient

        client = ZeroBusClient(config)
        await client.connect()

        status = client.get_connection_status()
        logger.info("✓ ZeroBus connection successful")
        logger.info(f"  Workspace: {status['workspace_url']}")
        logger.info(f"  Endpoint: {status['zerobus_endpoint']}")
        logger.info(f"  Target table: {status['target_table']}")
        logger.info(f"  Serialization: {status['serialization_mode']}")

        await client.close()
        return True

    except Exception as e:
        logger.error(f"ZeroBus connection failed: {e}", exc_info=True)
        return False


async def main():
    """Main entry point."""
    args = parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if config file exists
    if not args.config.exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1

    # Validate configuration
    if args.validate:
        success = await validate_config(args.config)
        return 0 if success else 1

    # Test connection
    if args.test_connection:
        success = await test_connection(args.config)
        return 0 if success else 1

    # Run connector
    app = ConnectorApp(
        config_file=args.config,
        gui_enabled=not args.no_gui
    )

    return await app.run_forever()


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
