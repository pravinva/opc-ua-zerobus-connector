"""OT Data Simulator - Unified CLI.

Run OPC-UA, MQTT, and Modbus simulators from a single command.

Usage:
    python -m ot_simulator --protocol opcua
    python -m ot_simulator --protocol mqtt
    python -m ot_simulator --protocol modbus
    python -m ot_simulator --protocol all
    python -m ot_simulator --config custom-config.yaml
    python -m ot_simulator --web-ui
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Any

from ot_simulator.config_loader import load_config, SimulatorConfig
from ot_simulator.opcua_simulator import OPCUASimulator
from ot_simulator.mqtt_simulator import MQTTSimulator
from ot_simulator.modbus_simulator import ModbusSimulator

logger = logging.getLogger("ot_simulator")


class SimulatorManager:
    """Manages multiple protocol simulators."""

    def __init__(self, config: SimulatorConfig, unified_manager: Any = None):
        self.config = config
        self.simulators: dict[str, Any] = {}
        self.tasks: list[asyncio.Task] = []
        self._shutdown = asyncio.Event()
        self.unified_manager = unified_manager

    async def start(self, protocols: list[str] | None = None):
        """Start specified protocol simulators.

        Args:
            protocols: List of protocols to start. If None, starts all enabled protocols.
        """
        if protocols is None:
            # Auto-detect enabled protocols from config
            protocols = []
            if self.config.opcua.enabled:
                protocols.append("opcua")
            if self.config.mqtt.enabled:
                protocols.append("mqtt")
            if self.config.modbus.enabled:
                protocols.append("modbus")

        logger.info(f"Starting simulators: {', '.join(protocols)}")

        # Create simulators
        if "opcua" in protocols:
            if not self.config.opcua.enabled:
                logger.warning("OPC-UA requested but disabled in config")
            else:
                opcua_sim = OPCUASimulator(self.config.opcua, simulator_manager=self.unified_manager)
                self.simulators["opcua"] = opcua_sim
                task = asyncio.create_task(opcua_sim.start(), name="opcua-simulator")
                self.tasks.append(task)
                logger.info(f"OPC-UA simulator started on {self.config.opcua.endpoint}")

        if "mqtt" in protocols:
            if not self.config.mqtt.enabled:
                logger.warning("MQTT requested but disabled in config")
            else:
                mqtt_sim = MQTTSimulator(self.config.mqtt)
                self.simulators["mqtt"] = mqtt_sim
                task = asyncio.create_task(mqtt_sim.start(), name="mqtt-simulator")
                self.tasks.append(task)
                broker = self.config.mqtt.broker
                port = broker.tls_port if broker.use_tls else broker.port
                logger.info(f"MQTT simulator started, publishing to {broker.host}:{port}")

        if "modbus" in protocols:
            if not self.config.modbus.enabled:
                logger.warning("Modbus requested but disabled in config")
            else:
                modbus_sim = ModbusSimulator(self.config.modbus)
                self.simulators["modbus"] = modbus_sim

                # Start TCP and/or RTU based on config
                if self.config.modbus.tcp.enabled:
                    task = asyncio.create_task(modbus_sim.start_tcp(), name="modbus-tcp-simulator")
                    self.tasks.append(task)
                    logger.info(
                        f"Modbus TCP simulator started on {self.config.modbus.tcp.host}:{self.config.modbus.tcp.port}"
                    )

                if self.config.modbus.rtu.enabled:
                    task = asyncio.create_task(modbus_sim.start_rtu(), name="modbus-rtu-simulator")
                    self.tasks.append(task)
                    logger.info(f"Modbus RTU simulator started on {self.config.modbus.rtu.port}")

        if not self.tasks:
            logger.error("No simulators started. Check config or protocol selection.")
            return

        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        logger.info(f"All simulators running. Press Ctrl+C to stop.")

        # Wait for shutdown signal or task completion
        try:
            await self._shutdown.wait()
        except asyncio.CancelledError:
            logger.info("Shutdown signal received")

        # Stop all simulators
        await self.stop()

    async def stop(self):
        """Stop all running simulators."""
        if self._shutdown.is_set():
            return  # Already stopping

        self._shutdown.set()
        logger.info("Stopping all simulators...")

        # Stop each simulator
        for name, sim in self.simulators.items():
            try:
                await sim.stop()
                logger.info(f"{name.upper()} simulator stopped")
            except Exception as e:
                logger.error(f"Error stopping {name} simulator: {e}")

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("All simulators stopped")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics from all simulators."""
        stats = {}
        for name, sim in self.simulators.items():
            try:
                stats[name] = sim.get_stats()
            except Exception as e:
                stats[name] = {"error": str(e)}
        return stats


def setup_logging(level: str = "INFO", log_file: str | None = None):
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    # Suppress ALL warnings - only show INFO and ERROR
    logging.getLogger().setLevel(logging.INFO)

    # Suppress noisy asyncua library logs
    logging.getLogger("asyncua").setLevel(logging.ERROR)
    logging.getLogger("asyncua.server.address_space").setLevel(logging.ERROR)
    logging.getLogger("asyncua.server.internal_session").setLevel(logging.ERROR)
    logging.getLogger("asyncua.server.internal_server").setLevel(logging.ERROR)

    # Suppress PLC scan overrun warnings (harmless in cloud environment)
    logging.getLogger("ot_simulator.plc").setLevel(logging.ERROR)
    logging.getLogger("ot_simulator.plc_manager").setLevel(logging.INFO)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="OT Data Simulator - Multi-Protocol Industrial Sensor Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start all enabled protocols from config
  python -m ot_simulator --config config.yaml

  # Start only OPC-UA
  python -m ot_simulator --protocol opcua

  # Start MQTT and Modbus
  python -m ot_simulator --protocol mqtt --protocol modbus

  # Start all protocols (override config)
  python -m ot_simulator --protocol all

  # Start with web UI on custom port
  python -m ot_simulator --web-ui --web-port 9000

  # Custom log level
  python -m ot_simulator --log-level DEBUG --log-file simulator.log
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="ot_simulator/config.yaml",
        help="Path to configuration file (default: ot_simulator/config.yaml)",
    )

    parser.add_argument(
        "--protocol",
        type=str,
        action="append",
        choices=["opcua", "mqtt", "modbus", "all"],
        help="Protocol(s) to simulate. Can be specified multiple times. Use 'all' for all protocols.",
    )

    parser.add_argument(
        "--web-ui",
        action="store_true",
        help="Enable web UI for simulator control (coming soon)",
    )

    parser.add_argument(
        "--web-port",
        type=int,
        help="Web UI port (overrides config)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (overrides config)",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Log file path (overrides config)",
    )

    parser.add_argument(
        "--list-sensors",
        action="store_true",
        help="List all available sensors and exit",
    )

    return parser.parse_args()


async def run_web_ui(config: SimulatorConfig, manager: SimulatorManager, port: int | None = None, unified_manager = None):
    """Run enhanced web UI with WebSocket support."""
    import os
    from aiohttp import web
    from ot_simulator.enhanced_web_ui import EnhancedWebUI
    from ot_simulator.websocket_server import WebSocketServer
    from ot_simulator.llm_agent_operator import LLMAgentOperator
    from ot_simulator.simulator_manager import SimulatorManager as UnifiedSimulatorManager

    # Port priority: CLI arg > DATABRICKS_APP_PORT env var > config
    if port is None:
        port = int(os.getenv('DATABRICKS_APP_PORT', config.web_ui.port))

    # Use provided unified manager or create new one (for backward compatibility)
    if unified_manager is None:
        unified_manager = UnifiedSimulatorManager()
        unified_manager.init_plc_manager()

    # Register protocol simulators with unified manager
    for protocol, sim in manager.simulators.items():
        # For OPC-UA, update it with the unified manager reference for PLC support
        if protocol == "opcua" and hasattr(sim, 'simulator_manager'):
            sim.simulator_manager = unified_manager

        unified_manager.register_simulator(protocol, sim)

    # NOTE: DO NOT reinitialize OPC-UA here - it should start with PLCs from the beginning

    # Create enhanced web UI
    web_ui = EnhancedWebUI(config, unified_manager)
    app = web_ui.app

    # Initialize LLM agent for natural language (before starting server)
    try:
        llm_agent = LLMAgentOperator(
            api_base_url=f"http://localhost:{port}/api",
            databricks_profile="DEFAULT",
            model_name="databricks-claude-sonnet-4-5",
        )
        logger.info("LLM agent initialized for natural language interaction")
    except Exception as e:
        logger.warning(f"LLM agent initialization failed: {e}. Natural language features disabled.")
        llm_agent = None

    # Create WebSocket server and add route BEFORE starting the server
    ws_server = WebSocketServer(unified_manager, llm_agent)
    app.router.add_get("/ws", ws_server.handle_websocket)

    # NOW start the HTTP server (after all routes are registered)
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, config.web_ui.host, port)
    await site.start()

    logger.info(f"Enhanced Web UI started on http://{config.web_ui.host}:{port}")

    # Start WebSocket broadcast task (after server is running)
    await ws_server.start_broadcast()

    logger.info(f"Features: Real-time charts, WebSocket streaming, Natural language interface")

    # Keep server running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Web UI stopping...")
        await ws_server.stop_broadcast()
    finally:
        await runner.cleanup()


def list_sensors():
    """List all available sensors."""
    from ot_simulator.sensor_models import IndustryType, get_industry_sensors

    print("\n=== Available Sensors by Industry ===\n")

    for industry in IndustryType:
        sensors = get_industry_sensors(industry)
        print(f"\n{industry.value.upper()} ({len(sensors)} sensors):")
        print("-" * 80)

        for sim in sensors:
            cfg = sim.config
            print(
                f"  {cfg.name:40s} {cfg.min_value:8.1f} - {cfg.max_value:8.1f} {cfg.unit:10s} [{cfg.sensor_type.value}]"
            )

    print()


async def main():
    """Main entry point."""
    args = parse_args()

    # Handle list sensors command
    if args.list_sensors:
        list_sensors()
        return 0

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info("Using default configuration")
        config = SimulatorConfig()
    else:
        config = load_config(config_path)

    # Override config with CLI args
    if args.log_level:
        config.log_level = args.log_level
    if args.log_file:
        config.log_file = args.log_file
    if args.web_port:
        config.web_ui.port = args.web_port

    # Setup logging
    setup_logging(config.log_level, config.log_file if config.log_file else None)

    logger.info(f"OT Data Simulator starting...")
    logger.info(f"Config: {config_path}")

    # Determine which protocols to run
    protocols = None
    if args.protocol:
        if "all" in args.protocol:
            protocols = ["opcua", "mqtt", "modbus"]
        else:
            protocols = args.protocol

    # Start web UI if requested
    if args.web_ui:
        logger.info("Web UI mode enabled")
        if not config.web_ui.enabled:
            config.web_ui.enabled = True

        # Create unified simulator manager FIRST (before starting simulators)
        from ot_simulator.simulator_manager import SimulatorManager as UnifiedSimulatorManager
        unified_manager = UnifiedSimulatorManager()
        unified_manager.init_plc_manager()

        # Create protocol manager with unified manager (for OPC-UA PLC support)
        manager = SimulatorManager(config, unified_manager=unified_manager)

        # Start simulators in background but DON'T await full initialization
        # This creates the simulator objects synchronously then starts them async
        simulator_task = asyncio.create_task(manager.start(protocols))

        # Give simulators a moment to be created (not fully started, just instantiated)
        # This ensures manager.simulators dict is populated before we try to register them
        await asyncio.sleep(0.1)

        # Run enhanced web UI immediately (blocks until stopped)
        # NOTE: Web UI must start ASAP for Databricks Apps health checks
        # Simulators will continue initializing in background while web UI is serving
        await run_web_ui(config, manager, args.web_port, unified_manager)
    else:
        # Run simulators directly
        manager = SimulatorManager(config)
        await manager.start(protocols)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
