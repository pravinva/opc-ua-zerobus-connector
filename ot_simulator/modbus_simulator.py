"""Modbus TCP/RTU Server Simulator with realistic industrial data.

Runs a Modbus slave that responds to read requests with live sensor data.
Supports TCP and RTU (serial) protocols.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

try:
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
    from pymodbus.device import ModbusDeviceIdentification
    from pymodbus.server import StartAsyncTcpServer, StartAsyncSerialServer
    import pymodbus
    version = getattr(pymodbus, '__version__', 'unknown')
    PYMODBUS_AVAILABLE = True
except ImportError as e:
    ModbusSequentialDataBlock = None  # type: ignore
    ModbusSlaveContext = None  # type: ignore
    ModbusServerContext = None  # type: ignore
    ModbusDeviceIdentification = None  # type: ignore
    StartAsyncTcpServer = None  # type: ignore
    StartAsyncSerialServer = None  # type: ignore
    version = None  # type: ignore
    PYMODBUS_AVAILABLE = False
    _import_error = e

from ot_simulator.config_loader import ModbusConfig
from ot_simulator.sensor_models import IndustryType, SensorSimulator, get_industry_sensors

logger = logging.getLogger("ot_simulator.modbus")


class ModbusSimulator:
    """Modbus TCP/RTU server simulator with realistic sensor data."""

    def __init__(self, config: ModbusConfig):
        # Try to import again if initial import failed
        if not PYMODBUS_AVAILABLE:
            try:
                import importlib
                import sys
                # Force reload of pymodbus modules
                if 'pymodbus' in sys.modules:
                    del sys.modules['pymodbus']
                if 'pymodbus.datastore' in sys.modules:
                    del sys.modules['pymodbus.datastore']
                if 'pymodbus.device' in sys.modules:
                    del sys.modules['pymodbus.device']
                if 'pymodbus.server' in sys.modules:
                    del sys.modules['pymodbus.server']

                # Try importing again
                from pymodbus.datastore import ModbusSequentialDataBlock as MSB
                from pymodbus.datastore import ModbusSlaveContext as MSC
                from pymodbus.datastore import ModbusServerContext as MSRC
                from pymodbus.device import ModbusDeviceIdentification as MDI
                from pymodbus.server import StartAsyncTcpServer as SATS
                from pymodbus.server import StartAsyncSerialServer as SASS
                import pymodbus as pm
                pv = getattr(pm, '__version__', 'unknown')

                # Update module-level variables
                globals()['ModbusSequentialDataBlock'] = MSB
                globals()['ModbusSlaveContext'] = MSC
                globals()['ModbusServerContext'] = MSRC
                globals()['ModbusDeviceIdentification'] = MDI
                globals()['StartAsyncTcpServer'] = SATS
                globals()['StartAsyncSerialServer'] = SASS
                globals()['version'] = pv
                logger.info(f"Successfully imported pymodbus on retry (version {pv})")
            except ImportError as e:
                error_msg = f"pymodbus package required but failed to import: {e}"
                if '_import_error' in globals():
                    error_msg += f"\nOriginal error: {_import_error}"
                logger.error(error_msg)
                raise ImportError(error_msg)

        if ModbusSequentialDataBlock is None:
            raise ImportError("pymodbus package required. Install with: pip install pymodbus")

        self.config = config
        self.simulators: dict[int, tuple[str, SensorSimulator]] = {}  # address -> (path, simulator)
        self.context: ModbusServerContext | None = None
        self._running = False
        self._update_count = 0

    async def init(self):
        """Initialize Modbus server and register map."""
        # Create register mapping
        register_map: dict[int, tuple[str, SensorSimulator]] = {}
        current_address = 0

        # Map industries to register ranges
        industry_types = []
        for industry_name in self.config.industries:
            try:
                industry_types.append(IndustryType(industry_name))
            except ValueError:
                logger.warning(f"Unknown industry type: {industry_name}")

        for industry in industry_types:
            # Get base address for this industry from config
            industry_config = self.config.register_mapping.get(industry.value, {})
            base_address = industry_config.get("start_address", current_address)

            sensors = get_industry_sensors(industry)
            for i, simulator in enumerate(sensors):
                address = base_address + i
                path = f"{industry.value}/{simulator.config.name}"
                register_map[address] = (path, simulator)

            # Update current address for next industry
            current_address = base_address + len(sensors)

        self.simulators = register_map

        # Create Modbus datastore
        # We need enough registers to cover all addresses
        max_address = max(self.simulators.keys()) if self.simulators else 0
        register_count = max_address + 100  # Add buffer

        # Initialize all registers to 0
        holding_registers = ModbusSequentialDataBlock(0, [0] * register_count)
        input_registers = ModbusSequentialDataBlock(0, [0] * register_count)
        coils = ModbusSequentialDataBlock(0, [False] * register_count)
        discrete_inputs = ModbusSequentialDataBlock(0, [False] * register_count)

        # Create slave context
        store = ModbusSlaveContext(
            di=discrete_inputs,
            co=coils,
            hr=holding_registers,
            ir=input_registers,
        )

        # Create server context
        self.context = ModbusServerContext(slaves=store, single=True)

        logger.info(
            f"Initialized Modbus server with {len(self.simulators)} sensors mapped to registers 0-{max_address}"
        )

    async def start_tcp(self):
        """Start Modbus TCP server."""
        if self.context is None:
            await self.init()

        host = self.config.tcp.host
        port = self.config.tcp.port

        logger.info(f"Starting Modbus TCP server on {host}:{port}")

        # Create device identification
        identity = ModbusDeviceIdentification()
        identity.VendorName = "Databricks"
        identity.ProductCode = "OT-SIM"
        identity.VendorUrl = "https://databricks.com"
        identity.ProductName = "OT Data Simulator"
        identity.ModelName = "Modbus TCP Simulator"
        identity.MajorMinorRevision = "1.0.0"

        # Start update task
        update_task = asyncio.create_task(self._update_loop())

        try:
            # Start server
            await StartAsyncTcpServer(
                context=self.context,
                identity=identity,
                address=(host, port),
            )
        except asyncio.CancelledError:
            logger.info("Modbus TCP server stopping...")
            update_task.cancel()
            await update_task
        except Exception as e:
            logger.exception(f"Error in Modbus TCP server: {e}")
            update_task.cancel()
            await update_task
            raise

    async def start_rtu(self):
        """Start Modbus RTU server."""
        if self.context is None:
            await self.init()

        port = self.config.rtu.port
        baudrate = self.config.rtu.baudrate

        logger.info(f"Starting Modbus RTU server on {port} @ {baudrate} baud")

        # Create device identification
        identity = ModbusDeviceIdentification()
        identity.VendorName = "Databricks"
        identity.ProductCode = "OT-SIM"
        identity.ProductName = "OT Data Simulator"
        identity.ModelName = "Modbus RTU Simulator"
        identity.MajorMinorRevision = "1.0.0"

        # Start update task
        update_task = asyncio.create_task(self._update_loop())

        try:
            # Start server
            await StartAsyncSerialServer(
                context=self.context,
                identity=identity,
                port=port,
                baudrate=baudrate,
                bytesize=self.config.rtu.bytesize,
                parity=self.config.rtu.parity,
                stopbits=self.config.rtu.stopbits,
            )
        except asyncio.CancelledError:
            logger.info("Modbus RTU server stopping...")
            update_task.cancel()
            await update_task
        except Exception as e:
            logger.exception(f"Error in Modbus RTU server: {e}")
            update_task.cancel()
            await update_task
            raise

    async def _update_loop(self):
        """Continuously update register values from simulators."""
        self._running = True
        update_interval = 1.0 / self.config.update_rate_hz

        logger.info(f"Starting register update loop at {self.config.update_rate_hz} Hz")

        try:
            while self._running:
                start_time = time.time()

                # Update all sensors
                for address, (path, simulator) in self.simulators.items():
                    # Get updated value
                    value = simulator.update()

                    # Scale value for Modbus (16-bit integer)
                    # Store as: int(value * scale_factor)
                    scaled_value = int(value * self.config.scale_factor)

                    # Clamp to 16-bit signed integer range
                    scaled_value = max(-32768, min(32767, scaled_value))

                    # Update holding register
                    if self.context:
                        slave_id = self.config.slave_id
                        # Get the slave context
                        slave_context = self.context[slave_id]
                        # Update holding register
                        slave_context.setValues(3, address, [scaled_value])  # 3 = holding registers

                self._update_count += 1

                # Log stats periodically
                if self._update_count % 100 == 0:
                    logger.debug(f"Updated {len(self.simulators)} registers ({self._update_count} cycles)")

                # Sleep for remaining time
                elapsed = time.time() - start_time
                sleep_time = max(0, update_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info("Register update loop stopped")
            self._running = False
            raise

    async def stop(self):
        """Stop the Modbus server."""
        self._running = False

    def inject_fault(self, sensor_path: str, duration: float = 10.0):
        """Inject a fault into a specific sensor."""
        # Find simulator by path
        for address, (path, simulator) in self.simulators.items():
            if path == sensor_path:
                simulator.inject_fault(duration)
                logger.info(f"Fault injected into {sensor_path} (register {address}) for {duration} seconds")
                return

        logger.warning(f"Sensor {sensor_path} not found")

    def get_register_map(self) -> dict[int, dict[str, Any]]:
        """Get the register map with current values."""
        register_map = {}

        for address, (path, simulator) in self.simulators.items():
            industry, sensor_name = path.split("/", 1)
            scaled_value = int(simulator.get_value() * self.config.scale_factor)

            register_map[address] = {
                "industry": industry,
                "sensor": sensor_name,
                "path": path,
                "raw_value": round(simulator.get_value(), 3),
                "scaled_value": scaled_value,
                "unit": simulator.config.unit,
                "type": simulator.config.sensor_type.value,
                "scale_factor": self.config.scale_factor,
            }

        return register_map

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "update_count": self._update_count,
            "sensor_count": len(self.simulators),
            "register_count": len(self.simulators),
            "running": self._running,
            "slave_id": self.config.slave_id,
            "scale_factor": self.config.scale_factor,
            "tcp_enabled": self.config.tcp.enabled,
            "rtu_enabled": self.config.rtu.enabled,
        }


async def run_modbus_simulator(config: ModbusConfig):
    """Run Modbus simulator (convenience function)."""
    sim = ModbusSimulator(config)

    # Start enabled servers
    tasks = []

    if config.tcp.enabled:
        tasks.append(asyncio.create_task(sim.start_tcp()))

    if config.rtu.enabled:
        tasks.append(asyncio.create_task(sim.start_rtu()))

    if not tasks:
        logger.error("No Modbus servers enabled (TCP and RTU both disabled)")
        return

    # Run all servers
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Modbus simulator stopped")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    import sys
    from ot_simulator.config_loader import load_config

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Load config
    config_path = sys.argv[1] if len(sys.argv) > 1 else "ot_simulator/config.yaml"
    full_config = load_config(config_path)

    # Run Modbus simulator
    asyncio.run(run_modbus_simulator(full_config.modbus))
