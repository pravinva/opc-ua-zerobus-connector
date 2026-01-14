"""Configuration loader for OT Simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WebUIConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8989
    auto_open_browser: bool = False


@dataclass
class OPCUAConfig:
    enabled: bool = True
    endpoint: str = "opc.tcp://0.0.0.0:4840/ot-simulator/server/"
    server_name: str = "OT Data Simulator - OPC UA"
    namespace_uri: str = "http://databricks.com/iot-simulator"
    security_policy: str = "NoSecurity"
    update_rate_hz: float = 2.0
    industries: list[str] = field(default_factory=lambda: ["mining", "utilities", "manufacturing", "oil_gas"])


@dataclass
class MQTTBrokerConfig:
    host: str = "localhost"
    port: int = 1883
    use_tls: bool = False
    tls_port: int = 8883


@dataclass
class MQTTAuthConfig:
    username: str = ""
    password: str = ""


@dataclass
class MQTTConfig:
    enabled: bool = True
    broker: MQTTBrokerConfig = field(default_factory=MQTTBrokerConfig)
    auth: MQTTAuthConfig = field(default_factory=MQTTAuthConfig)
    client_id: str = "ot-simulator-publisher"
    clean_session: bool = True
    keepalive: int = 60
    qos: int = 1
    topic_prefix: str = "sensors"
    payload_format: str = "json"
    include_metadata: bool = True
    include_timestamp: bool = True
    publish_rate_hz: float = 2.0
    batch_publish: bool = False
    industries: list[str] = field(default_factory=lambda: ["mining", "utilities", "manufacturing", "oil_gas"])


@dataclass
class ModbusTCPConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 5020


@dataclass
class ModbusRTUConfig:
    enabled: bool = False
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    parity: str = "N"
    stopbits: int = 1
    bytesize: int = 8


@dataclass
class ModbusConfig:
    enabled: bool = True
    tcp: ModbusTCPConfig = field(default_factory=ModbusTCPConfig)
    rtu: ModbusRTUConfig = field(default_factory=ModbusRTUConfig)
    slave_id: int = 1
    register_mapping: dict[str, dict[str, Any]] = field(default_factory=dict)
    scale_factor: int = 10
    update_rate_hz: float = 2.0
    industries: list[str] = field(default_factory=lambda: ["mining", "utilities", "manufacturing", "oil_gas"])


@dataclass
class SensorConfig:
    global_config: dict[str, Any] = field(default_factory=dict)
    mining: dict[str, Any] = field(default_factory=lambda: {"enabled": True})
    utilities: dict[str, Any] = field(default_factory=lambda: {"enabled": True})
    manufacturing: dict[str, Any] = field(default_factory=lambda: {"enabled": True})
    oil_gas: dict[str, Any] = field(default_factory=lambda: {"enabled": True})


@dataclass
class FaultsConfig:
    enabled: bool = True
    auto_inject: bool = False
    auto_inject_interval_seconds: int = 300
    auto_inject_duration_seconds: int = 30
    fault_types: list[str] = field(default_factory=lambda: ["spike", "drift", "oscillation", "freeze", "noise"])
    targets: list[str] = field(default_factory=lambda: ["mining/*", "utilities/*", "manufacturing/*", "oil_gas/*"])


@dataclass
class PrometheusConfig:
    enabled: bool = True
    port: int = 9091
    path: str = "/metrics"


@dataclass
class MonitoringConfig:
    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulatorConfig:
    name: str = "Databricks OT Data Simulator"
    log_level: str = "INFO"
    log_file: str = "ot_simulator.log"
    web_ui: WebUIConfig = field(default_factory=WebUIConfig)
    opcua: OPCUAConfig = field(default_factory=OPCUAConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    modbus: ModbusConfig = field(default_factory=ModbusConfig)
    sensors: SensorConfig = field(default_factory=SensorConfig)
    faults: FaultsConfig = field(default_factory=FaultsConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    recording: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, Any] = field(default_factory=dict)
    active_preset: str | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SimulatorConfig":
        """Create config from dictionary."""
        # Handle nested configs
        web_ui = WebUIConfig(**data.get("web_ui", {}))

        opcua_data = data.get("opcua", {})
        # Filter out 'security' key until OPCUAConfig supports it
        opcua_data_filtered = {k: v for k, v in opcua_data.items() if k != 'security'}
        opcua = OPCUAConfig(**opcua_data_filtered)

        mqtt_data = data.get("mqtt", {})
        mqtt_broker = MQTTBrokerConfig(**mqtt_data.get("broker", {}))
        mqtt_auth = MQTTAuthConfig(**mqtt_data.get("auth", {}))
        mqtt = MQTTConfig(
            broker=mqtt_broker, auth=mqtt_auth, **{k: v for k, v in mqtt_data.items() if k not in ["broker", "auth"]}
        )

        modbus_data = data.get("modbus", {})
        modbus_tcp = ModbusTCPConfig(**modbus_data.get("tcp", {}))
        modbus_rtu = ModbusRTUConfig(**modbus_data.get("rtu", {}))
        modbus = ModbusConfig(
            tcp=modbus_tcp, rtu=modbus_rtu, **{k: v for k, v in modbus_data.items() if k not in ["tcp", "rtu"]}
        )

        # Handle sensors config - map "global" to "global_config"
        sensors_data = data.get("sensors", {})
        if "global" in sensors_data:
            sensors_data["global_config"] = sensors_data.pop("global")
        sensors = SensorConfig(**sensors_data)
        faults = FaultsConfig(**data.get("faults", {}))

        monitoring_data = data.get("monitoring", {})
        prometheus = PrometheusConfig(**monitoring_data.get("prometheus", {}))
        monitoring = MonitoringConfig(prometheus=prometheus, stats=monitoring_data.get("stats", {}))

        return SimulatorConfig(
            name=data.get("simulator", {}).get("name", "Databricks OT Data Simulator"),
            log_level=data.get("simulator", {}).get("log_level", "INFO"),
            log_file=data.get("simulator", {}).get("log_file", "ot_simulator.log"),
            web_ui=web_ui,
            opcua=opcua,
            mqtt=mqtt,
            modbus=modbus,
            sensors=sensors,
            faults=faults,
            monitoring=monitoring,
            recording=data.get("recording", {}),
            performance=data.get("performance", {}),
            active_preset=data.get("active_preset"),
        )


def load_config(config_path: str | Path) -> SimulatorConfig:
    """Load configuration from YAML file."""
    path = Path(config_path)

    if not path.exists():
        # Return default config
        return SimulatorConfig()

    with path.open("r") as f:
        data = yaml.safe_load(f) or {}

    # Apply preset if specified
    if "active_preset" in data:
        preset_name = data["active_preset"]
        presets = data.get("presets", {})
        if preset_name in presets:
            preset = presets[preset_name]
            # Deep merge preset into data
            _deep_merge(data, preset)

    return SimulatorConfig.from_dict(data)


def _deep_merge(base: dict, override: dict) -> None:
    """Deep merge override dict into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def save_config(config_path: str | Path, config: SimulatorConfig) -> None:
    """Save configuration to YAML file."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict (simplified - you may want to implement to_dict() methods)
    data = {
        "simulator": {
            "name": config.name,
            "log_level": config.log_level,
            "log_file": config.log_file,
        },
        "web_ui": {
            "enabled": config.web_ui.enabled,
            "host": config.web_ui.host,
            "port": config.web_ui.port,
            "auto_open_browser": config.web_ui.auto_open_browser,
        },
        # ... add other sections as needed
    }

    with path.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
