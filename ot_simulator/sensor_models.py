"""Realistic sensor models for industrial OT environments.

Based on industry standards and typical operating ranges from:
- Mining operations
- Utilities (power, water, gas)
- Manufacturing facilities
- Oil & Gas operations
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class IndustryType(str, Enum):
    """Industrial sector types."""

    MINING = "mining"
    UTILITIES = "utilities"
    MANUFACTURING = "manufacturing"
    OIL_GAS = "oil_gas"
    AEROSPACE = "aerospace"
    SPACE = "space"
    WATER_WASTEWATER = "water_wastewater"
    ELECTRIC_POWER = "electric_power"
    AUTOMOTIVE = "automotive"
    CHEMICAL = "chemical"
    FOOD_BEVERAGE = "food_beverage"
    PHARMACEUTICAL = "pharmaceutical"
    DATA_CENTER = "data_center"
    SMART_BUILDING = "smart_building"
    AGRICULTURE = "agriculture"
    RENEWABLE_ENERGY = "renewable_energy"


class SensorType(str, Enum):
    """Types of industrial sensors."""

    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    FLOW = "flow"
    VIBRATION = "vibration"
    LEVEL = "level"
    SPEED = "speed"
    POWER = "power"
    CURRENT = "current"
    VOLTAGE = "voltage"
    HUMIDITY = "humidity"
    PH = "ph"
    CONDUCTIVITY = "conductivity"
    POSITION = "position"
    STATUS = "status"


@dataclass
class SensorConfig:
    """Configuration for a sensor."""

    name: str
    sensor_type: SensorType
    unit: str
    min_value: float
    max_value: float
    nominal_value: float
    noise_std: float = 0.01  # Standard deviation for noise
    drift_rate: float = 0.0001  # Slow drift per update
    anomaly_probability: float = 0.001  # 0.1% chance of anomaly
    anomaly_magnitude: float = 2.0  # Multiplier for anomalies
    update_frequency_hz: float = 1.0  # Updates per second

    # Cyclic patterns (for motors, pumps, etc.)
    cyclic: bool = False
    cycle_period_seconds: float = 60.0
    cycle_amplitude: float = 0.1  # As fraction of nominal


class SensorSimulator:
    """Simulates a single sensor with realistic behavior."""

    def __init__(self, config: SensorConfig):
        self.config = config
        self.current_value = config.nominal_value
        self.drift_accumulator = 0.0
        self.cycle_offset = random.uniform(0, 2 * math.pi)
        self.last_update = time.time()
        self.fault_active = False
        self.fault_end_time = 0.0

    def update(self) -> float:
        """Update sensor value with realistic variations."""
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Base value
        value = self.config.nominal_value

        # Add cyclic variation (for rotating equipment)
        if self.config.cyclic:
            cycle_phase = (2 * math.pi * now / self.config.cycle_period_seconds) + self.cycle_offset
            cycle_variation = math.sin(cycle_phase) * self.config.cycle_amplitude * self.config.nominal_value
            value += cycle_variation

        # Add slow drift
        self.drift_accumulator += self.config.drift_rate * dt * random.choice([-1, 1])
        self.drift_accumulator = max(-0.05, min(0.05, self.drift_accumulator))  # Limit drift
        value += value * self.drift_accumulator

        # Add random noise
        noise = random.gauss(0, self.config.noise_std * abs(self.config.nominal_value))
        value += noise

        # Check for anomalies
        if not self.fault_active:
            if random.random() < self.config.anomaly_probability:
                # Trigger anomaly
                self.fault_active = True
                self.fault_end_time = now + random.uniform(5, 30)  # 5-30 second anomaly

        # Apply active fault
        if self.fault_active:
            if now < self.fault_end_time:
                # Anomaly types: spike, drift, oscillation
                anomaly_type = random.choice(["spike", "drift", "oscillation"])
                if anomaly_type == "spike":
                    value *= self.config.anomaly_magnitude
                elif anomaly_type == "drift":
                    value += (self.config.max_value - self.config.min_value) * 0.3
                elif anomaly_type == "oscillation":
                    value += math.sin(now * 10) * (self.config.max_value - self.config.min_value) * 0.2
            else:
                self.fault_active = False

        # Clamp to physical limits
        value = max(self.config.min_value, min(self.config.max_value, value))

        self.current_value = value
        return value

    def get_value(self) -> float:
        """Get current sensor value."""
        return self.current_value

    def inject_fault(self, duration_seconds: float = 10.0):
        """Manually inject a fault condition."""
        self.fault_active = True
        self.fault_end_time = time.time() + duration_seconds


# Industry-specific sensor configurations
INDUSTRY_SENSORS: dict[IndustryType, list[SensorConfig]] = {
    IndustryType.MINING: [
        # Conveyor Belt System
        SensorConfig(
            "conveyor_belt_1_speed", SensorType.SPEED, "m/s", 0.5, 3.0, 1.8, 0.02, cyclic=True, cycle_period_seconds=120
        ),
        SensorConfig("conveyor_belt_1_motor_temp", SensorType.TEMPERATURE, "°C", 40, 95, 65, 2.0, 0.001),
        SensorConfig(
            "conveyor_belt_1_motor_current",
            SensorType.CURRENT,
            "A",
            50,
            200,
            120,
            3.0,
            cyclic=True,
            cycle_period_seconds=60,
        ),
        SensorConfig(
            "conveyor_belt_1_vibration", SensorType.VIBRATION, "mm/s", 0.5, 15.0, 2.5, 0.3, anomaly_probability=0.002
        ),
        # Crusher
        SensorConfig(
            "crusher_1_motor_power", SensorType.POWER, "kW", 200, 800, 450, 15.0, cyclic=True, cycle_period_seconds=30
        ),
        SensorConfig("crusher_1_bearing_temp", SensorType.TEMPERATURE, "°C", 35, 105, 70, 3.0, 0.002),
        SensorConfig("crusher_1_oil_pressure", SensorType.PRESSURE, "bar", 2.0, 8.0, 5.0, 0.15, cyclic=True),
        SensorConfig(
            "crusher_1_vibration_x", SensorType.VIBRATION, "mm/s", 1.0, 25.0, 5.0, 0.5, anomaly_probability=0.003
        ),
        SensorConfig(
            "crusher_1_vibration_y", SensorType.VIBRATION, "mm/s", 1.0, 25.0, 4.8, 0.5, anomaly_probability=0.003
        ),
        # Ventilation System
        SensorConfig(
            "vent_fan_1_speed", SensorType.SPEED, "RPM", 500, 1800, 1200, 20, cyclic=True, cycle_period_seconds=300
        ),
        SensorConfig("vent_fan_1_power", SensorType.POWER, "kW", 30, 150, 75, 3.0),
        SensorConfig("vent_fan_1_vibration", SensorType.VIBRATION, "mm/s", 0.5, 12.0, 2.0, 0.2),
        SensorConfig("vent_fan_1_motor_temp", SensorType.TEMPERATURE, "°C", 35, 85, 55, 2.5),
        # Dewatering Pump
        SensorConfig("pump_1_flow", SensorType.FLOW, "LPM", 500, 3000, 1800, 50, cyclic=True, cycle_period_seconds=180),
        SensorConfig("pump_1_discharge_pressure", SensorType.PRESSURE, "bar", 3.0, 12.0, 7.5, 0.25),
        SensorConfig("pump_1_motor_current", SensorType.CURRENT, "A", 80, 250, 150, 5.0, cyclic=True),
        SensorConfig("pump_1_bearing_temp", SensorType.TEMPERATURE, "°C", 40, 95, 60, 3.0, 0.001),
    ],
    IndustryType.UTILITIES: [
        # Power Generation - Turbine
        SensorConfig(
            "turbine_1_speed", SensorType.SPEED, "RPM", 2900, 3100, 3000, 5.0, cyclic=True, cycle_period_seconds=600
        ),
        SensorConfig(
            "turbine_1_power_output", SensorType.POWER, "MW", 45, 55, 50, 0.5, cyclic=True, cycle_period_seconds=900
        ),
        SensorConfig("turbine_1_bearing_temp_1", SensorType.TEMPERATURE, "°C", 50, 105, 75, 2.5, 0.001),
        SensorConfig("turbine_1_bearing_temp_2", SensorType.TEMPERATURE, "°C", 50, 105, 73, 2.5, 0.001),
        SensorConfig(
            "turbine_1_vibration", SensorType.VIBRATION, "mm/s", 0.5, 18.0, 3.5, 0.4, anomaly_probability=0.002
        ),
        SensorConfig("turbine_1_oil_pressure", SensorType.PRESSURE, "bar", 3.5, 8.5, 6.0, 0.2),
        # Water Treatment - Pump Station
        SensorConfig(
            "water_pump_1_flow", SensorType.FLOW, "GPM", 2000, 8000, 5000, 150, cyclic=True, cycle_period_seconds=300
        ),
        SensorConfig("water_pump_1_discharge_pressure", SensorType.PRESSURE, "PSI", 60, 150, 95, 3.0),
        SensorConfig("water_pump_1_motor_power", SensorType.POWER, "kW", 100, 400, 250, 10),
        SensorConfig("water_pump_1_motor_temp", SensorType.TEMPERATURE, "°C", 45, 90, 60, 2.0),
        # Water Quality
        SensorConfig("water_ph", SensorType.PH, "pH", 6.5, 8.5, 7.2, 0.05),
        SensorConfig("water_conductivity", SensorType.CONDUCTIVITY, "μS/cm", 200, 800, 450, 15),
        SensorConfig("water_turbidity", SensorType.LEVEL, "NTU", 0.1, 5.0, 0.8, 0.1),
        # Gas Distribution - Compressor
        SensorConfig("gas_compressor_1_pressure_in", SensorType.PRESSURE, "PSI", 40, 80, 60, 2.0),
        SensorConfig("gas_compressor_1_pressure_out", SensorType.PRESSURE, "PSI", 200, 500, 350, 10),
        SensorConfig("gas_compressor_1_flow", SensorType.FLOW, "SCFM", 5000, 15000, 10000, 300),
        SensorConfig("gas_compressor_1_motor_power", SensorType.POWER, "kW", 300, 900, 600, 20),
        SensorConfig("gas_compressor_1_discharge_temp", SensorType.TEMPERATURE, "°C", 80, 150, 110, 3.0),
    ],
    IndustryType.MANUFACTURING: [
        # CNC Machine
        SensorConfig(
            "cnc_1_spindle_speed", SensorType.SPEED, "RPM", 0, 8000, 3500, 50, cyclic=True, cycle_period_seconds=45
        ),
        SensorConfig("cnc_1_spindle_temp", SensorType.TEMPERATURE, "°C", 25, 75, 45, 2.0),
        SensorConfig("cnc_1_spindle_power", SensorType.POWER, "kW", 5, 35, 20, 1.5, cyclic=True),
        SensorConfig("cnc_1_coolant_flow", SensorType.FLOW, "LPM", 10, 40, 25, 1.0),
        SensorConfig("cnc_1_coolant_temp", SensorType.TEMPERATURE, "°C", 18, 28, 22, 0.5),
        SensorConfig("cnc_1_vibration", SensorType.VIBRATION, "mm/s", 0.5, 10.0, 2.0, 0.25),
        # Assembly Line Conveyor
        SensorConfig(
            "assy_line_1_speed", SensorType.SPEED, "m/min", 2.0, 12.0, 8.0, 0.2, cyclic=True, cycle_period_seconds=90
        ),
        SensorConfig("assy_line_1_motor_current", SensorType.CURRENT, "A", 5, 25, 12, 0.5),
        SensorConfig(
            "assy_line_1_position", SensorType.POSITION, "m", 0, 100, 50, 0.1, cyclic=True, cycle_period_seconds=600
        ),
        # Hydraulic Press
        SensorConfig(
            "press_1_pressure", SensorType.PRESSURE, "bar", 10, 300, 200, 5.0, cyclic=True, cycle_period_seconds=20
        ),
        SensorConfig("press_1_hydraulic_oil_temp", SensorType.TEMPERATURE, "°C", 35, 65, 48, 1.5),
        SensorConfig("press_1_cycle_count", SensorType.POSITION, "count", 0, 1000000, 123456, 0),  # Counter
        # Air Compressor
        SensorConfig(
            "compressor_1_pressure",
            SensorType.PRESSURE,
            "PSI",
            90,
            125,
            105,
            2.0,
            cyclic=True,
            cycle_period_seconds=240,
        ),
        SensorConfig("compressor_1_motor_temp", SensorType.TEMPERATURE, "°C", 45, 95, 65, 2.5),
        SensorConfig("compressor_1_flow", SensorType.FLOW, "CFM", 100, 500, 300, 15),
        # HVAC System
        SensorConfig("hvac_zone_1_temp", SensorType.TEMPERATURE, "°C", 18, 26, 21, 0.3),
        SensorConfig("hvac_zone_1_humidity", SensorType.HUMIDITY, "%RH", 30, 60, 45, 2.0),
        SensorConfig("hvac_ahu_1_supply_temp", SensorType.TEMPERATURE, "°C", 12, 18, 15, 0.5),
        SensorConfig("hvac_ahu_1_return_temp", SensorType.TEMPERATURE, "°C", 19, 25, 22, 0.5),
    ],
    IndustryType.OIL_GAS: [
        # Pipeline
        SensorConfig(
            "pipeline_1_flow",
            SensorType.FLOW,
            "BBL/day",
            5000,
            25000,
            15000,
            500,
            cyclic=True,
            cycle_period_seconds=3600,
        ),
        SensorConfig("pipeline_1_pressure", SensorType.PRESSURE, "PSI", 800, 1500, 1200, 20),
        SensorConfig("pipeline_1_temperature", SensorType.TEMPERATURE, "°C", 10, 45, 28, 1.0),
        SensorConfig("pipeline_1_density", SensorType.LEVEL, "kg/m³", 780, 950, 850, 5),
        # Pump Station
        SensorConfig("pump_station_1_suction_pressure", SensorType.PRESSURE, "PSI", 50, 200, 120, 5),
        SensorConfig("pump_station_1_discharge_pressure", SensorType.PRESSURE, "PSI", 1000, 1600, 1300, 25),
        SensorConfig("pump_station_1_flow", SensorType.FLOW, "BBL/day", 8000, 30000, 18000, 600),
        SensorConfig("pump_station_1_motor_power", SensorType.POWER, "kW", 500, 1500, 1000, 30),
        SensorConfig("pump_station_1_bearing_temp", SensorType.TEMPERATURE, "°C", 45, 95, 65, 2.5),
        SensorConfig("pump_station_1_seal_pressure", SensorType.PRESSURE, "PSI", 15, 45, 30, 1.5),
        SensorConfig(
            "pump_station_1_vibration", SensorType.VIBRATION, "mm/s", 1.0, 20.0, 4.5, 0.5, anomaly_probability=0.002
        ),
        # Separator
        SensorConfig("separator_1_pressure", SensorType.PRESSURE, "PSI", 100, 400, 250, 8),
        SensorConfig("separator_1_temperature", SensorType.TEMPERATURE, "°C", 30, 80, 55, 2.0),
        SensorConfig(
            "separator_1_level", SensorType.LEVEL, "%", 20, 80, 50, 2.0, cyclic=True, cycle_period_seconds=600
        ),
        SensorConfig("separator_1_gas_flow", SensorType.FLOW, "MMSCFD", 1.0, 15.0, 8.0, 0.3),
        SensorConfig("separator_1_oil_flow", SensorType.FLOW, "BBL/day", 2000, 12000, 7000, 250),
        SensorConfig("separator_1_water_flow", SensorType.FLOW, "BBL/day", 500, 4000, 2000, 100),
        # Storage Tank
        SensorConfig("tank_1_level", SensorType.LEVEL, "%", 10, 95, 65, 1.0, cyclic=True, cycle_period_seconds=7200),
        SensorConfig("tank_1_temperature", SensorType.TEMPERATURE, "°C", 15, 40, 25, 1.0),
        SensorConfig("tank_1_pressure", SensorType.PRESSURE, "PSI", 0, 5, 1.5, 0.1),
        SensorConfig("tank_1_volume", SensorType.LEVEL, "BBL", 0, 50000, 32500, 500),
        # Wellhead
        SensorConfig("well_1_pressure", SensorType.PRESSURE, "PSI", 500, 3000, 1800, 50),
        SensorConfig("well_1_temperature", SensorType.TEMPERATURE, "°C", 40, 90, 65, 2.0),
        SensorConfig("well_1_flow", SensorType.FLOW, "BBL/day", 100, 5000, 2500, 100),
        SensorConfig("well_1_gas_oil_ratio", SensorType.LEVEL, "SCF/BBL", 200, 2000, 800, 50),
        SensorConfig("well_1_water_cut", SensorType.LEVEL, "%", 5, 70, 25, 2.0, 0.002),
    ],
    IndustryType.AEROSPACE: [
        # Aircraft Flight Control Systems
        SensorConfig("aileron_position_left", SensorType.POSITION, "deg", -25, 25, 0, 0.5, cyclic=True),
        SensorConfig("aileron_position_right", SensorType.POSITION, "deg", -25, 25, 0, 0.5, cyclic=True),
        SensorConfig("elevator_position", SensorType.POSITION, "deg", -30, 20, 0, 0.5, cyclic=True),
        SensorConfig("rudder_position", SensorType.POSITION, "deg", -35, 35, 0, 0.6, cyclic=True),
        SensorConfig("flap_position", SensorType.POSITION, "deg", 0, 40, 0, 1.0),
        # Engine Systems (Turbofan)
        SensorConfig("engine_1_n1_rpm", SensorType.SPEED, "RPM", 0, 12000, 8500, 50, cyclic=True),
        SensorConfig("engine_1_n2_rpm", SensorType.SPEED, "RPM", 0, 16000, 11500, 70, cyclic=True),
        SensorConfig("engine_1_egt", SensorType.TEMPERATURE, "°C", 200, 900, 650, 10),
        SensorConfig("engine_1_fuel_flow", SensorType.FLOW, "kg/h", 100, 12000, 6000, 100, cyclic=True),
        SensorConfig("engine_1_oil_pressure", SensorType.PRESSURE, "PSI", 25, 90, 60, 2.0),
        SensorConfig("engine_1_oil_temp", SensorType.TEMPERATURE, "°C", 70, 120, 95, 2.5),
        SensorConfig("engine_1_vibration", SensorType.VIBRATION, "mm/s", 0.5, 15.0, 3.5, 0.4),
        # Hydraulic Systems
        SensorConfig("hydraulic_system_a_pressure", SensorType.PRESSURE, "PSI", 2800, 3200, 3000, 20),
        SensorConfig("hydraulic_system_b_pressure", SensorType.PRESSURE, "PSI", 2800, 3200, 3000, 20),
        SensorConfig("hydraulic_fluid_temp", SensorType.TEMPERATURE, "°C", 40, 90, 65, 2.0),
        SensorConfig("hydraulic_reservoir_level", SensorType.LEVEL, "%", 40, 100, 85, 1.0),
        # Landing Gear
        SensorConfig("landing_gear_nose_position", SensorType.POSITION, "%", 0, 100, 0, 2.0),
        SensorConfig("landing_gear_left_position", SensorType.POSITION, "%", 0, 100, 0, 2.0),
        SensorConfig("landing_gear_right_position", SensorType.POSITION, "%", 0, 100, 0, 2.0),
        # Environmental Control
        SensorConfig("cabin_pressure", SensorType.PRESSURE, "ft", 8000, 12000, 8000, 50),
        SensorConfig("cabin_temperature", SensorType.TEMPERATURE, "°C", 18, 28, 22, 0.5),
        SensorConfig("cabin_humidity", SensorType.HUMIDITY, "%RH", 10, 60, 35, 2.0),
        # Fuel System
        SensorConfig("fuel_tank_1_quantity", SensorType.LEVEL, "kg", 0, 50000, 35000, 100, cyclic=True),
        SensorConfig("fuel_tank_2_quantity", SensorType.LEVEL, "kg", 0, 50000, 35000, 100, cyclic=True),
        SensorConfig("fuel_temperature", SensorType.TEMPERATURE, "°C", -40, 50, 15, 2.0),
    ],
    IndustryType.SPACE: [
        # Satellite Attitude Control
        SensorConfig("reaction_wheel_1_speed", SensorType.SPEED, "RPM", -6000, 6000, 0, 50, cyclic=True),
        SensorConfig("reaction_wheel_2_speed", SensorType.SPEED, "RPM", -6000, 6000, 0, 50, cyclic=True),
        SensorConfig("reaction_wheel_3_speed", SensorType.SPEED, "RPM", -6000, 6000, 0, 50, cyclic=True),
        SensorConfig("gyroscope_x", SensorType.POSITION, "deg/s", -10, 10, 0, 0.1),
        SensorConfig("gyroscope_y", SensorType.POSITION, "deg/s", -10, 10, 0, 0.1),
        SensorConfig("gyroscope_z", SensorType.POSITION, "deg/s", -10, 10, 0, 0.1),
        # Power Systems
        SensorConfig("solar_array_1_voltage", SensorType.VOLTAGE, "V", 28, 35, 32, 0.5, cyclic=True),
        SensorConfig("solar_array_1_current", SensorType.CURRENT, "A", 0, 30, 20, 1.0, cyclic=True),
        SensorConfig("battery_voltage", SensorType.VOLTAGE, "V", 28, 34, 32, 0.3),
        SensorConfig("battery_current", SensorType.CURRENT, "A", -20, 20, 5, 1.0, cyclic=True),
        SensorConfig("battery_temperature", SensorType.TEMPERATURE, "°C", -10, 30, 15, 1.0),
        SensorConfig("battery_state_of_charge", SensorType.LEVEL, "%", 20, 100, 85, 0.5, cyclic=True),
        # Thermal Control
        SensorConfig("radiator_temp_1", SensorType.TEMPERATURE, "°C", -150, 150, 20, 5.0, cyclic=True),
        SensorConfig("radiator_temp_2", SensorType.TEMPERATURE, "°C", -150, 150, 20, 5.0, cyclic=True),
        SensorConfig("electronics_bay_temp", SensorType.TEMPERATURE, "°C", 5, 35, 20, 1.0),
        SensorConfig("propellant_tank_temp", SensorType.TEMPERATURE, "°C", -20, 40, 15, 2.0),
        # Propulsion System
        SensorConfig("propellant_tank_pressure", SensorType.PRESSURE, "PSI", 200, 350, 280, 5),
        SensorConfig("propellant_mass", SensorType.LEVEL, "kg", 0, 500, 350, 1.0, cyclic=True),
        SensorConfig("thruster_temp", SensorType.TEMPERATURE, "°C", 20, 400, 100, 10),
        # Communications
        SensorConfig("transmitter_power", SensorType.POWER, "W", 0, 100, 50, 2.0),
    ],
    IndustryType.WATER_WASTEWATER: [
        # Raw Water Intake
        SensorConfig("intake_pump_1_flow", SensorType.FLOW, "MGD", 5, 50, 25, 1.0, cyclic=True),
        SensorConfig("intake_pump_1_pressure", SensorType.PRESSURE, "PSI", 30, 80, 55, 2.0),
        SensorConfig("intake_pump_1_motor_current", SensorType.CURRENT, "A", 50, 200, 120, 5.0),
        SensorConfig("raw_water_turbidity", SensorType.LEVEL, "NTU", 1.0, 100.0, 15.0, 2.0),
        # Coagulation/Flocculation
        SensorConfig("coagulant_dosing_rate", SensorType.FLOW, "GPM", 0, 50, 20, 1.0),
        SensorConfig("mixer_1_speed", SensorType.SPEED, "RPM", 10, 100, 50, 2.0),
        SensorConfig("flocculation_basin_level", SensorType.LEVEL, "ft", 5, 15, 10, 0.5),
        # Sedimentation
        SensorConfig("clarifier_1_overflow_rate", SensorType.FLOW, "GPM", 100, 1000, 500, 20),
        SensorConfig("clarifier_1_sludge_blanket", SensorType.LEVEL, "ft", 0, 8, 3, 0.3),
        SensorConfig("settled_water_turbidity", SensorType.LEVEL, "NTU", 0.1, 10.0, 2.0, 0.2),
        # Filtration
        SensorConfig("filter_1_inlet_pressure", SensorType.PRESSURE, "PSI", 20, 60, 40, 2.0),
        SensorConfig("filter_1_outlet_pressure", SensorType.PRESSURE, "PSI", 15, 55, 35, 2.0),
        SensorConfig("filter_1_flow", SensorType.FLOW, "GPM", 100, 2000, 1000, 50),
        SensorConfig("filtered_water_turbidity", SensorType.LEVEL, "NTU", 0.01, 0.5, 0.1, 0.02),
        # Disinfection
        SensorConfig("chlorine_residual", SensorType.LEVEL, "mg/L", 0.5, 4.0, 2.0, 0.1),
        SensorConfig("contact_tank_level", SensorType.LEVEL, "ft", 8, 20, 15, 0.5),
        # Distribution
        SensorConfig("clearwell_level", SensorType.LEVEL, "ft", 10, 30, 22, 1.0),
        SensorConfig("distribution_pump_1_flow", SensorType.FLOW, "MGD", 10, 60, 35, 2.0, cyclic=True),
        SensorConfig("distribution_pump_1_pressure", SensorType.PRESSURE, "PSI", 60, 120, 90, 3.0),
        SensorConfig("distribution_pump_1_power", SensorType.POWER, "kW", 50, 300, 180, 10),
        # Finished Water Quality
        SensorConfig("finished_water_ph", SensorType.PH, "pH", 6.5, 9.0, 7.5, 0.1),
        SensorConfig("finished_water_conductivity", SensorType.CONDUCTIVITY, "μS/cm", 100, 800, 400, 20),
    ],
    IndustryType.ELECTRIC_POWER: [
        # Gas Turbine Generator
        SensorConfig("gt_1_speed", SensorType.SPEED, "RPM", 2950, 3050, 3000, 5.0, cyclic=True),
        SensorConfig("gt_1_power_output", SensorType.POWER, "MW", 100, 300, 200, 5.0, cyclic=True),
        SensorConfig("gt_1_exhaust_temp", SensorType.TEMPERATURE, "°C", 400, 600, 500, 10),
        SensorConfig("gt_1_fuel_flow", SensorType.FLOW, "kg/s", 5, 20, 12, 0.5, cyclic=True),
        SensorConfig("gt_1_compressor_pressure", SensorType.PRESSURE, "bar", 15, 25, 20, 0.5),
        SensorConfig("gt_1_vibration", SensorType.VIBRATION, "mm/s", 0.5, 20.0, 4.0, 0.5),
        # Steam Turbine
        SensorConfig("st_1_speed", SensorType.SPEED, "RPM", 2950, 3050, 3000, 5.0, cyclic=True),
        SensorConfig("st_1_power_output", SensorType.POWER, "MW", 150, 450, 300, 8.0, cyclic=True),
        SensorConfig("st_1_steam_pressure", SensorType.PRESSURE, "bar", 100, 180, 140, 3.0),
        SensorConfig("st_1_steam_temp", SensorType.TEMPERATURE, "°C", 500, 560, 530, 5.0),
        SensorConfig("st_1_condenser_vacuum", SensorType.PRESSURE, "kPa", 5, 15, 10, 0.5),
        # Generator
        SensorConfig("gen_1_voltage", SensorType.VOLTAGE, "kV", 12, 15, 13.8, 0.2),
        SensorConfig("gen_1_current", SensorType.CURRENT, "kA", 5, 20, 12, 0.5, cyclic=True),
        SensorConfig("gen_1_power_factor", SensorType.LEVEL, "PF", 0.8, 1.0, 0.95, 0.01),
        SensorConfig("gen_1_frequency", SensorType.SPEED, "Hz", 59.9, 60.1, 60.0, 0.02),
        SensorConfig("gen_1_stator_temp", SensorType.TEMPERATURE, "°C", 60, 120, 85, 3.0),
        SensorConfig("gen_1_bearing_temp", SensorType.TEMPERATURE, "°C", 50, 95, 70, 2.5),
        # Transformer
        SensorConfig("transformer_1_oil_temp", SensorType.TEMPERATURE, "°C", 50, 90, 70, 2.0),
        SensorConfig("transformer_1_winding_temp", SensorType.TEMPERATURE, "°C", 60, 110, 80, 3.0),
        SensorConfig("transformer_1_load", SensorType.POWER, "MVA", 50, 500, 300, 10),
        # Cooling System
        SensorConfig("cooling_tower_1_water_temp", SensorType.TEMPERATURE, "°C", 15, 35, 25, 1.0),
        SensorConfig("cooling_tower_1_fan_speed", SensorType.SPEED, "RPM", 0, 600, 400, 10, cyclic=True),
        SensorConfig("circulating_pump_1_flow", SensorType.FLOW, "m³/h", 5000, 20000, 12000, 300, cyclic=True),
        SensorConfig("circulating_pump_1_discharge_pressure", SensorType.PRESSURE, "bar", 3, 8, 5.5, 0.2),
    ],
    IndustryType.AUTOMOTIVE: [
        # Body Welding Robots
        SensorConfig("robot_1_joint_1_position", SensorType.POSITION, "deg", -180, 180, 0, 1.0, cyclic=True),
        SensorConfig("robot_1_joint_2_position", SensorType.POSITION, "deg", -90, 90, 0, 1.0, cyclic=True),
        SensorConfig("robot_1_joint_3_position", SensorType.POSITION, "deg", -180, 180, 0, 1.0, cyclic=True),
        SensorConfig("robot_1_weld_current", SensorType.CURRENT, "A", 100, 400, 250, 10, cyclic=True),
        SensorConfig("robot_1_weld_voltage", SensorType.VOLTAGE, "V", 15, 35, 25, 1.0),
        SensorConfig("robot_1_motor_temp", SensorType.TEMPERATURE, "°C", 35, 75, 50, 2.0),
        # Paint Booth
        SensorConfig("paint_booth_temp", SensorType.TEMPERATURE, "°C", 18, 28, 22, 0.5),
        SensorConfig("paint_booth_humidity", SensorType.HUMIDITY, "%RH", 40, 70, 55, 2.0),
        SensorConfig("paint_booth_airflow", SensorType.FLOW, "m³/h", 5000, 15000, 10000, 200),
        SensorConfig("paint_booth_pressure", SensorType.PRESSURE, "Pa", -50, 50, 10, 2.0),
        SensorConfig("paint_atomizer_pressure", SensorType.PRESSURE, "bar", 2, 4, 3, 0.1),
        # Oven/Curing
        SensorConfig("oven_zone_1_temp", SensorType.TEMPERATURE, "°C", 120, 180, 150, 3.0),
        SensorConfig("oven_zone_2_temp", SensorType.TEMPERATURE, "°C", 140, 200, 170, 3.0),
        SensorConfig("oven_zone_3_temp", SensorType.TEMPERATURE, "°C", 100, 160, 130, 3.0),
        SensorConfig("oven_conveyor_speed", SensorType.SPEED, "m/min", 1, 8, 4, 0.2),
        # Final Assembly
        SensorConfig("assembly_line_speed", SensorType.SPEED, "vehicles/h", 20, 80, 50, 2, cyclic=True),
        SensorConfig("torque_wrench_1_torque", SensorType.LEVEL, "Nm", 50, 300, 180, 5.0, cyclic=True),
        SensorConfig("torque_wrench_1_angle", SensorType.POSITION, "deg", 0, 360, 90, 5.0),
        # Quality Testing
        SensorConfig("leak_test_pressure", SensorType.PRESSURE, "mbar", 0, 100, 50, 2.0),
        SensorConfig("alignment_x_offset", SensorType.POSITION, "mm", -5, 5, 0, 0.1),
        SensorConfig("alignment_y_offset", SensorType.POSITION, "mm", -5, 5, 0, 0.1),
        # Material Handling
        SensorConfig("agv_1_battery_level", SensorType.LEVEL, "%", 20, 100, 75, 1.0, cyclic=True),
        SensorConfig("agv_1_speed", SensorType.SPEED, "m/s", 0, 2.0, 1.0, 0.1),
        SensorConfig("overhead_crane_position", SensorType.POSITION, "m", 0, 100, 50, 0.5, cyclic=True),
        SensorConfig("overhead_crane_load", SensorType.LEVEL, "kg", 0, 5000, 2000, 50),
        # Stamping Press
        SensorConfig("press_2_force", SensorType.PRESSURE, "ton", 100, 1000, 600, 20, cyclic=True),
        SensorConfig("press_2_position", SensorType.POSITION, "mm", 0, 500, 250, 5.0, cyclic=True),
        SensorConfig("press_2_oil_pressure", SensorType.PRESSURE, "bar", 150, 250, 200, 5.0),
    ],
    IndustryType.CHEMICAL: [
        # Reactor System
        SensorConfig("reactor_1_temperature", SensorType.TEMPERATURE, "°C", 60, 180, 120, 5.0),
        SensorConfig("reactor_1_pressure", SensorType.PRESSURE, "bar", 1, 25, 10, 0.5),
        SensorConfig("reactor_1_level", SensorType.LEVEL, "%", 20, 90, 60, 2.0),
        SensorConfig("reactor_1_agitator_speed", SensorType.SPEED, "RPM", 50, 300, 180, 10, cyclic=True),
        SensorConfig("reactor_1_ph", SensorType.PH, "pH", 2.0, 12.0, 7.0, 0.2),
        SensorConfig("reactor_1_conductivity", SensorType.CONDUCTIVITY, "mS/cm", 1, 100, 50, 2.0),
        SensorConfig("reactor_1_jacket_temp", SensorType.TEMPERATURE, "°C", 40, 160, 100, 4.0),
        # Distillation Column
        SensorConfig("column_1_bottom_temp", SensorType.TEMPERATURE, "°C", 100, 200, 150, 5.0),
        SensorConfig("column_1_top_temp", SensorType.TEMPERATURE, "°C", 60, 120, 90, 3.0),
        SensorConfig("column_1_pressure", SensorType.PRESSURE, "bar", 0.5, 5.0, 2.0, 0.1),
        SensorConfig("column_1_reflux_ratio", SensorType.LEVEL, "ratio", 1.0, 10.0, 5.0, 0.2),
        SensorConfig("column_1_feed_flow", SensorType.FLOW, "L/min", 50, 500, 250, 10, cyclic=True),
        # Storage Tanks
        SensorConfig("tank_2_level", SensorType.LEVEL, "%", 10, 95, 65, 1.5, cyclic=True),
        SensorConfig("tank_2_temperature", SensorType.TEMPERATURE, "°C", 15, 45, 25, 1.0),
        SensorConfig("tank_2_pressure", SensorType.PRESSURE, "mbar", -50, 200, 50, 5.0),
        # Pumps
        SensorConfig("chemical_pump_1_flow", SensorType.FLOW, "L/min", 10, 200, 100, 5.0, cyclic=True),
        SensorConfig("chemical_pump_1_discharge_pressure", SensorType.PRESSURE, "bar", 2, 15, 8, 0.3),
        SensorConfig("chemical_pump_1_motor_current", SensorType.CURRENT, "A", 10, 50, 25, 2.0),
        SensorConfig("chemical_pump_1_seal_temp", SensorType.TEMPERATURE, "°C", 30, 70, 45, 2.0),
        # Heat Exchangers
        SensorConfig("hx_1_hot_inlet_temp", SensorType.TEMPERATURE, "°C", 80, 180, 130, 5.0),
        SensorConfig("hx_1_hot_outlet_temp", SensorType.TEMPERATURE, "°C", 40, 100, 70, 3.0),
        SensorConfig("hx_1_cold_inlet_temp", SensorType.TEMPERATURE, "°C", 15, 40, 25, 2.0),
        SensorConfig("hx_1_cold_outlet_temp", SensorType.TEMPERATURE, "°C", 50, 120, 80, 3.0),
        # Safety Systems
        SensorConfig("emergency_vent_pressure", SensorType.PRESSURE, "bar", 0, 30, 1.5, 0.5),
        SensorConfig("gas_detector_1_concentration", SensorType.LEVEL, "ppm", 0, 1000, 10, 5.0),
        SensorConfig("scrubber_efficiency", SensorType.LEVEL, "%", 90, 99.9, 97, 0.5),
    ],
    IndustryType.FOOD_BEVERAGE: [
        # Mixing/Blending
        SensorConfig("mixer_tank_1_temperature", SensorType.TEMPERATURE, "°C", 4, 25, 15, 1.0),
        SensorConfig("mixer_tank_1_level", SensorType.LEVEL, "%", 20, 90, 60, 2.0),
        SensorConfig("mixer_tank_1_agitator_speed", SensorType.SPEED, "RPM", 20, 200, 100, 5.0, cyclic=True),
        SensorConfig("mixer_tank_1_viscosity", SensorType.LEVEL, "cP", 1, 1000, 100, 10),
        # Pasteurization
        SensorConfig("pasteurizer_inlet_temp", SensorType.TEMPERATURE, "°C", 4, 20, 10, 1.0),
        SensorConfig("pasteurizer_hold_temp", SensorType.TEMPERATURE, "°C", 72, 78, 75, 0.5),
        SensorConfig("pasteurizer_outlet_temp", SensorType.TEMPERATURE, "°C", 4, 10, 6, 0.5),
        SensorConfig("pasteurizer_flow_rate", SensorType.FLOW, "L/min", 100, 1000, 500, 20, cyclic=True),
        SensorConfig("pasteurizer_hold_time", SensorType.LEVEL, "s", 15, 30, 20, 1.0),
        # Fermentation
        SensorConfig("fermenter_1_temp", SensorType.TEMPERATURE, "°C", 8, 28, 18, 1.0),
        SensorConfig("fermenter_1_pressure", SensorType.PRESSURE, "bar", 0, 3, 1.5, 0.1),
        SensorConfig("fermenter_1_ph", SensorType.PH, "pH", 3.5, 7.0, 5.0, 0.1),
        SensorConfig("fermenter_1_dissolved_oxygen", SensorType.LEVEL, "ppm", 0, 20, 8, 0.5),
        # Filling Line
        SensorConfig("filler_1_speed", SensorType.SPEED, "bottles/min", 50, 500, 300, 10, cyclic=True),
        SensorConfig("filler_1_fill_volume", SensorType.LEVEL, "mL", 495, 505, 500, 0.5),
        SensorConfig("filler_1_product_temp", SensorType.TEMPERATURE, "°C", 2, 8, 5, 0.5),
        # Packaging
        SensorConfig("labeler_speed", SensorType.SPEED, "units/min", 100, 600, 350, 15, cyclic=True),
        SensorConfig("capper_torque", SensorType.LEVEL, "Nm", 1, 5, 3, 0.2),
        SensorConfig("conveyor_speed", SensorType.SPEED, "m/min", 5, 30, 18, 1.0, cyclic=True),
        # Cold Storage
        SensorConfig("cold_room_1_temp", SensorType.TEMPERATURE, "°C", 2, 6, 4, 0.3),
        SensorConfig("cold_room_1_humidity", SensorType.HUMIDITY, "%RH", 70, 90, 80, 2.0),
        SensorConfig("freezer_1_temp", SensorType.TEMPERATURE, "°C", -25, -18, -22, 1.0),
        # CIP (Clean-In-Place)
        SensorConfig("cip_solution_temp", SensorType.TEMPERATURE, "°C", 65, 85, 75, 2.0),
        SensorConfig("cip_solution_conductivity", SensorType.CONDUCTIVITY, "mS/cm", 5, 50, 25, 2.0),
        SensorConfig("cip_flow_rate", SensorType.FLOW, "L/min", 50, 300, 180, 10),
    ],
    IndustryType.PHARMACEUTICAL: [
        # Clean Room Environment
        SensorConfig("cleanroom_1_temp", SensorType.TEMPERATURE, "°C", 18, 24, 21, 0.2),
        SensorConfig("cleanroom_1_humidity", SensorType.HUMIDITY, "%RH", 35, 55, 45, 1.0),
        SensorConfig("cleanroom_1_pressure", SensorType.PRESSURE, "Pa", 5, 20, 12, 0.5),
        SensorConfig("cleanroom_1_particle_count_0_5um", SensorType.LEVEL, "particles/m³", 0, 3520, 1000, 100),
        SensorConfig("cleanroom_1_particle_count_5um", SensorType.LEVEL, "particles/m³", 0, 29, 10, 2),
        SensorConfig("cleanroom_1_air_changes", SensorType.LEVEL, "ACH", 15, 25, 20, 1.0),
        # Bioreactor
        SensorConfig("bioreactor_1_temp", SensorType.TEMPERATURE, "°C", 35, 39, 37, 0.1),
        SensorConfig("bioreactor_1_ph", SensorType.PH, "pH", 6.8, 7.4, 7.2, 0.05),
        SensorConfig("bioreactor_1_dissolved_oxygen", SensorType.LEVEL, "%", 20, 60, 40, 2.0),
        SensorConfig("bioreactor_1_agitation", SensorType.SPEED, "RPM", 50, 300, 180, 10),
        SensorConfig("bioreactor_1_pressure", SensorType.PRESSURE, "bar", 0.5, 2.0, 1.2, 0.05),
        SensorConfig("bioreactor_1_cell_density", SensorType.LEVEL, "g/L", 0, 50, 25, 2.0),
        # Freeze Dryer (Lyophilizer)
        SensorConfig("freeze_dryer_shelf_temp", SensorType.TEMPERATURE, "°C", -50, 40, -10, 2.0, cyclic=True),
        SensorConfig("freeze_dryer_chamber_pressure", SensorType.PRESSURE, "mTorr", 10, 500, 100, 5.0),
        SensorConfig("freeze_dryer_condenser_temp", SensorType.TEMPERATURE, "°C", -80, -40, -60, 3.0),
        # Tablet Press
        SensorConfig("tablet_press_compression_force", SensorType.LEVEL, "kN", 5, 40, 20, 1.0, cyclic=True),
        SensorConfig("tablet_press_speed", SensorType.SPEED, "tablets/min", 500, 10000, 5000, 100, cyclic=True),
        SensorConfig("tablet_press_turret_temp", SensorType.TEMPERATURE, "°C", 25, 45, 32, 2.0),
        SensorConfig("tablet_weight", SensorType.LEVEL, "mg", 95, 105, 100, 0.5),
        SensorConfig("tablet_thickness", SensorType.POSITION, "mm", 3.8, 4.2, 4.0, 0.05),
        # Coating Pan
        SensorConfig("coating_pan_inlet_air_temp", SensorType.TEMPERATURE, "°C", 40, 80, 60, 2.0),
        SensorConfig("coating_pan_exhaust_temp", SensorType.TEMPERATURE, "°C", 30, 50, 40, 2.0),
        SensorConfig("coating_pan_spray_rate", SensorType.FLOW, "g/min", 10, 100, 50, 5.0),
        SensorConfig("coating_pan_rotation_speed", SensorType.SPEED, "RPM", 2, 20, 10, 1.0),
        # Filling Line
        SensorConfig("vial_filler_speed", SensorType.SPEED, "vials/min", 50, 600, 300, 20, cyclic=True),
        SensorConfig("vial_fill_volume", SensorType.LEVEL, "mL", 4.9, 5.1, 5.0, 0.02),
        SensorConfig("vial_fill_weight", SensorType.LEVEL, "g", 4.95, 5.05, 5.0, 0.01),
        # Autoclave/Sterilizer
        SensorConfig("autoclave_chamber_temp", SensorType.TEMPERATURE, "°C", 20, 140, 121, 5.0, cyclic=True),
        SensorConfig("autoclave_chamber_pressure", SensorType.PRESSURE, "bar", 0, 3, 2.1, 0.1),
        SensorConfig("autoclave_cycle_time", SensorType.LEVEL, "min", 0, 60, 20, 1.0),
    ],
    IndustryType.DATA_CENTER: [
        # Server Racks
        SensorConfig("rack_1_inlet_temp", SensorType.TEMPERATURE, "°C", 18, 27, 22, 0.5),
        SensorConfig("rack_1_outlet_temp", SensorType.TEMPERATURE, "°C", 25, 40, 32, 1.0),
        SensorConfig("rack_1_power_consumption", SensorType.POWER, "kW", 5, 30, 18, 1.0, cyclic=True),
        SensorConfig("rack_1_humidity", SensorType.HUMIDITY, "%RH", 40, 60, 50, 2.0),
        # Cooling System (CRAC)
        SensorConfig("crac_1_supply_air_temp", SensorType.TEMPERATURE, "°C", 15, 20, 18, 0.3),
        SensorConfig("crac_1_return_air_temp", SensorType.TEMPERATURE, "°C", 25, 35, 30, 0.5),
        SensorConfig("crac_1_fan_speed", SensorType.SPEED, "RPM", 500, 1800, 1200, 50, cyclic=True),
        SensorConfig("crac_1_chilled_water_flow", SensorType.FLOW, "L/min", 100, 500, 300, 20),
        SensorConfig("crac_1_chilled_water_supply_temp", SensorType.TEMPERATURE, "°C", 7, 12, 10, 0.5),
        SensorConfig("crac_1_chilled_water_return_temp", SensorType.TEMPERATURE, "°C", 12, 18, 15, 0.5),
        # UPS System
        SensorConfig("ups_1_input_voltage", SensorType.VOLTAGE, "V", 200, 240, 220, 5.0),
        SensorConfig("ups_1_output_voltage", SensorType.VOLTAGE, "V", 200, 240, 220, 2.0),
        SensorConfig("ups_1_battery_voltage", SensorType.VOLTAGE, "V", 450, 550, 500, 5.0),
        SensorConfig("ups_1_load", SensorType.LEVEL, "%", 20, 90, 60, 2.0, cyclic=True),
        SensorConfig("ups_1_battery_temp", SensorType.TEMPERATURE, "°C", 20, 30, 25, 1.0),
        SensorConfig("ups_1_battery_capacity", SensorType.LEVEL, "%", 80, 100, 95, 1.0),
        # Power Distribution
        SensorConfig("pdu_1_total_power", SensorType.POWER, "kW", 100, 800, 450, 20, cyclic=True),
        SensorConfig("pdu_1_voltage_phase_a", SensorType.VOLTAGE, "V", 200, 240, 220, 3.0),
        SensorConfig("pdu_1_current_phase_a", SensorType.CURRENT, "A", 50, 400, 200, 10),
        # Fire Suppression
        SensorConfig("fire_suppression_system_pressure", SensorType.PRESSURE, "bar", 40, 60, 50, 1.0),
        # Environmental Monitoring
        SensorConfig("ambient_humidity", SensorType.HUMIDITY, "%RH", 35, 55, 45, 2.0),
        SensorConfig("water_leak_detector_status", SensorType.STATUS, "binary", 0, 1, 0, 0),
    ],
    IndustryType.SMART_BUILDING: [
        # HVAC System
        SensorConfig("building_hvac_zone_1_temp", SensorType.TEMPERATURE, "°C", 18, 26, 21, 0.4),
        SensorConfig("building_hvac_zone_1_humidity", SensorType.HUMIDITY, "%RH", 30, 60, 45, 2.0),
        SensorConfig("building_hvac_zone_1_co2", SensorType.LEVEL, "ppm", 400, 1000, 600, 20),
        SensorConfig("building_hvac_ahu_supply_temp", SensorType.TEMPERATURE, "°C", 12, 18, 15, 0.5),
        SensorConfig("building_hvac_ahu_return_temp", SensorType.TEMPERATURE, "°C", 19, 25, 22, 0.5),
        SensorConfig("building_hvac_ahu_fan_speed", SensorType.SPEED, "RPM", 300, 1200, 800, 30, cyclic=True),
        SensorConfig("building_hvac_damper_position", SensorType.POSITION, "%", 0, 100, 50, 5.0),
        # Chiller Plant
        SensorConfig("chiller_1_leaving_water_temp", SensorType.TEMPERATURE, "°C", 6, 12, 8, 0.3),
        SensorConfig("chiller_1_entering_water_temp", SensorType.TEMPERATURE, "°C", 10, 16, 13, 0.3),
        SensorConfig("chiller_1_power", SensorType.POWER, "kW", 100, 800, 450, 20, cyclic=True),
        SensorConfig("chiller_1_efficiency", SensorType.LEVEL, "kW/ton", 0.4, 1.0, 0.6, 0.05),
        # Lighting System
        SensorConfig("floor_1_lighting_power", SensorType.POWER, "kW", 0, 50, 25, 2.0, cyclic=True),
        SensorConfig("floor_1_occupancy", SensorType.LEVEL, "people", 0, 200, 100, 5),
        SensorConfig("floor_1_light_level", SensorType.LEVEL, "lux", 200, 800, 500, 20),
        # Energy Management
        SensorConfig("building_total_power", SensorType.POWER, "kW", 200, 2000, 1000, 50, cyclic=True),
        SensorConfig("solar_panel_output", SensorType.POWER, "kW", 0, 100, 50, 5.0, cyclic=True),
        SensorConfig("battery_storage_soc", SensorType.LEVEL, "%", 20, 100, 75, 2.0, cyclic=True),
        # Water Management
        SensorConfig("domestic_water_flow", SensorType.FLOW, "L/min", 0, 500, 200, 10, cyclic=True),
        SensorConfig("domestic_water_pressure", SensorType.PRESSURE, "PSI", 40, 80, 60, 2.0),
        SensorConfig("hot_water_temp", SensorType.TEMPERATURE, "°C", 50, 70, 60, 2.0),
        # Elevator System
        SensorConfig("elevator_1_position", SensorType.POSITION, "floor", 1, 20, 10, 1.0, cyclic=True),
        SensorConfig("elevator_1_load", SensorType.LEVEL, "kg", 0, 1000, 400, 20),
        SensorConfig("elevator_1_motor_current", SensorType.CURRENT, "A", 10, 80, 40, 5.0),
        # Security/Access
        SensorConfig("main_entrance_occupancy_count", SensorType.LEVEL, "people", 0, 50, 10, 2),
        SensorConfig("parking_occupancy", SensorType.LEVEL, "vehicles", 0, 500, 300, 5),
    ],
    IndustryType.AGRICULTURE: [
        # Greenhouse Climate
        SensorConfig("greenhouse_1_temp", SensorType.TEMPERATURE, "°C", 15, 35, 24, 1.0),
        SensorConfig("greenhouse_1_humidity", SensorType.HUMIDITY, "%RH", 40, 90, 70, 3.0),
        SensorConfig("greenhouse_1_co2", SensorType.LEVEL, "ppm", 400, 1200, 800, 30),
        SensorConfig("greenhouse_1_light_intensity", SensorType.LEVEL, "W/m²", 0, 1000, 500, 50, cyclic=True),
        SensorConfig("greenhouse_1_soil_moisture_1", SensorType.LEVEL, "%", 20, 80, 50, 3.0),
        SensorConfig("greenhouse_1_soil_temp_1", SensorType.TEMPERATURE, "°C", 15, 30, 22, 1.0),
        # Irrigation System
        SensorConfig("irrigation_pump_flow", SensorType.FLOW, "L/min", 50, 500, 250, 15, cyclic=True),
        SensorConfig("irrigation_pump_pressure", SensorType.PRESSURE, "bar", 2, 6, 4, 0.2),
        SensorConfig("irrigation_valve_1_position", SensorType.POSITION, "%", 0, 100, 50, 5.0),
        SensorConfig("water_tank_level", SensorType.LEVEL, "%", 10, 100, 70, 2.0),
        # Fertigation
        SensorConfig("nutrient_solution_ph", SensorType.PH, "pH", 5.5, 7.0, 6.2, 0.1),
        SensorConfig("nutrient_solution_ec", SensorType.CONDUCTIVITY, "mS/cm", 1.5, 3.5, 2.5, 0.1),
        SensorConfig("nutrient_solution_temp", SensorType.TEMPERATURE, "°C", 15, 25, 20, 1.0),
        SensorConfig("fertilizer_tank_a_level", SensorType.LEVEL, "%", 10, 100, 60, 2.0),
        # Livestock Barn
        SensorConfig("barn_temp", SensorType.TEMPERATURE, "°C", 10, 30, 18, 1.0),
        SensorConfig("barn_humidity", SensorType.HUMIDITY, "%RH", 40, 80, 60, 3.0),
        SensorConfig("barn_ammonia_level", SensorType.LEVEL, "ppm", 0, 25, 5, 1.0),
        SensorConfig("barn_ventilation_fan_speed", SensorType.SPEED, "RPM", 0, 1000, 500, 30, cyclic=True),
        # Grain Storage
        SensorConfig("silo_1_grain_temp", SensorType.TEMPERATURE, "°C", 5, 25, 15, 1.0),
        SensorConfig("silo_1_grain_moisture", SensorType.HUMIDITY, "%", 10, 20, 14, 0.5),
    ],
    IndustryType.RENEWABLE_ENERGY: [
        # Wind Turbine 1
        SensorConfig("wind_turbine_1_wind_speed", SensorType.SPEED, "m/s", 0, 25, 8.5, 1.5, cyclic=True, cycle_period_seconds=180),
        SensorConfig("wind_turbine_1_rotor_speed", SensorType.SPEED, "RPM", 0, 20, 12, 1.0, cyclic=True, cycle_period_seconds=120),
        SensorConfig("wind_turbine_1_power_output", SensorType.POWER, "MW", 0, 3.6, 2.2, 0.3, cyclic=True, cycle_period_seconds=200),
        SensorConfig("wind_turbine_1_nacelle_temp", SensorType.TEMPERATURE, "°C", 20, 75, 45, 3.0),
        SensorConfig("wind_turbine_1_gearbox_temp", SensorType.TEMPERATURE, "°C", 30, 80, 55, 3.5),
        SensorConfig("wind_turbine_1_gearbox_oil_pressure", SensorType.PRESSURE, "bar", 1.5, 4.5, 3.0, 0.2),
        SensorConfig("wind_turbine_1_bearing_vibration", SensorType.VIBRATION, "mm/s", 0.5, 12.0, 2.5, 0.3, anomaly_probability=0.002),
        SensorConfig("wind_turbine_1_pitch_angle", SensorType.POSITION, "°", 0, 90, 15, 2.0),
        SensorConfig("wind_turbine_1_yaw_position", SensorType.POSITION, "°", 0, 360, 180, 15.0, cyclic=True),
        SensorConfig("wind_turbine_1_generator_temp", SensorType.TEMPERATURE, "°C", 35, 90, 60, 4.0),
        # Solar Array 1
        SensorConfig("solar_array_1_dc_power", SensorType.POWER, "kW", 0, 500, 300, 25, cyclic=True, cycle_period_seconds=3600),
        SensorConfig("solar_array_1_dc_voltage", SensorType.VOLTAGE, "V", 500, 800, 650, 10),
        SensorConfig("solar_array_1_dc_current", SensorType.CURRENT, "A", 0, 700, 450, 30, cyclic=True, cycle_period_seconds=3600),
        SensorConfig("solar_array_1_panel_temp", SensorType.TEMPERATURE, "°C", 15, 65, 35, 4.0, cyclic=True, cycle_period_seconds=3600),
        SensorConfig("solar_array_1_irradiance", SensorType.LEVEL, "W/m²", 0, 1200, 650, 80, cyclic=True, cycle_period_seconds=3600),
        SensorConfig("solar_array_1_efficiency", SensorType.LEVEL, "%", 15, 22, 19, 0.5),
        # Solar Inverter 1
        SensorConfig("solar_inverter_1_ac_power", SensorType.POWER, "kW", 0, 500, 285, 24, cyclic=True, cycle_period_seconds=3600),
        SensorConfig("solar_inverter_1_ac_voltage", SensorType.VOLTAGE, "V", 380, 420, 400, 5),
        SensorConfig("solar_inverter_1_ac_current", SensorType.CURRENT, "A", 0, 700, 420, 28, cyclic=True),
        SensorConfig("solar_inverter_1_frequency", SensorType.LEVEL, "Hz", 49.9, 50.1, 50.0, 0.05),
        SensorConfig("solar_inverter_1_temp", SensorType.TEMPERATURE, "°C", 25, 75, 50, 3.5),
        SensorConfig("solar_inverter_1_efficiency", SensorType.LEVEL, "%", 94, 98, 96.5, 0.3),
        # Battery Energy Storage System (BESS)
        SensorConfig("bess_1_soc", SensorType.LEVEL, "%", 10, 100, 70, 2.0, cyclic=True, cycle_period_seconds=1800),
        SensorConfig("bess_1_voltage", SensorType.VOLTAGE, "V", 700, 850, 780, 8),
        SensorConfig("bess_1_current", SensorType.CURRENT, "A", -500, 500, 50, 40, cyclic=True, cycle_period_seconds=900),
        SensorConfig("bess_1_power", SensorType.POWER, "kW", -400, 400, 40, 35, cyclic=True, cycle_period_seconds=900),
        SensorConfig("bess_1_temp_avg", SensorType.TEMPERATURE, "°C", 15, 45, 28, 2.0),
        SensorConfig("bess_1_temp_max", SensorType.TEMPERATURE, "°C", 20, 50, 32, 2.5),
        SensorConfig("bess_1_cycles_count", SensorType.LEVEL, "cycles", 0, 5000, 1200, 5),
        # Tracking System (Solar)
        SensorConfig("solar_tracker_1_azimuth", SensorType.POSITION, "°", 0, 360, 180, 10.0, cyclic=True, cycle_period_seconds=43200),
        SensorConfig("solar_tracker_1_elevation", SensorType.POSITION, "°", 0, 90, 45, 5.0, cyclic=True, cycle_period_seconds=43200),
        SensorConfig("solar_tracker_1_motor_current", SensorType.CURRENT, "A", 0, 15, 5, 1.0),
    ],
}


def get_industry_sensors(industry: IndustryType) -> list[SensorSimulator]:
    """Get configured simulators for an industry."""
    configs = INDUSTRY_SENSORS.get(industry, [])
    return [SensorSimulator(config) for config in configs]


def get_all_sensors() -> dict[IndustryType, list[SensorSimulator]]:
    """Get all configured simulators for all industries."""
    return {industry: get_industry_sensors(industry) for industry in IndustryType}
