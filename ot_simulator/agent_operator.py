"""Natural language agent operator for OT simulator.

Provides an intelligent agent that can understand and execute commands in natural language,
making simulator operation more intuitive and powerful.

Usage:
    python -m ot_simulator.agent_operator

Examples:
    "Start the OPC-UA simulator"
    "Inject a fault into mining crusher motor power for 60 seconds"
    "What's the current status of all simulators?"
    "Show me all sensors in the utilities industry"
    "Set MQTT publish rate to 5 Hz"
    "Stop all simulators"
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

from ot_simulator.config_loader import load_config, SimulatorConfig
from ot_simulator.sensor_models import IndustryType, get_industry_sensors

logger = logging.getLogger("ot_simulator.agent")


@dataclass
class Command:
    """Parsed command from natural language."""

    action: str  # start, stop, inject_fault, get_status, list_sensors, configure
    target: str | None = None  # protocol, sensor_path, etc.
    parameters: dict[str, Any] | None = None
    confidence: float = 1.0


class AgentOperator:
    """Natural language agent for simulator operation."""

    def __init__(self, api_base_url: str = "http://localhost:8989/api"):
        """Initialize agent operator.

        Args:
            api_base_url: Base URL for simulator API
        """
        self.api_base_url = api_base_url
        self.config: SimulatorConfig | None = None
        self._session: aiohttp.ClientSession | None = None

        # Command patterns for intent recognition
        self.patterns = {
            "start_simulator": [
                r"start\s+(?:the\s+)?(\w+)\s+simulator",
                r"run\s+(?:the\s+)?(\w+)\s+protocol",
                r"launch\s+(\w+)",
            ],
            "stop_simulator": [
                r"stop\s+(?:the\s+)?(\w+)\s+simulator",
                r"halt\s+(\w+)",
                r"shutdown\s+(\w+)",
            ],
            "inject_fault": [
                r"inject\s+(?:a\s+)?fault\s+(?:into|in)\s+(.+?)\s+for\s+(\d+)\s+seconds?",
                r"fault\s+(.+?)\s+(\d+)s",
                r"break\s+(.+?)\s+for\s+(\d+)",
            ],
            "get_status": [
                r"(?:what[\'']?s|show|get)\s+(?:the\s+)?status",
                r"how\s+(?:are|is)\s+(?:the\s+)?simulators?",
                r"list\s+(?:running\s+)?simulators?",
            ],
            "list_sensors": [
                r"(?:list|show|get)\s+(?:all\s+)?sensors?\s+(?:in|for)\s+(\w+)",
                r"what\s+sensors?\s+(?:are\s+)?(?:in|for)\s+(\w+)",
                r"show\s+me\s+(\w+)\s+sensors?",
            ],
            "configure": [
                r"set\s+(\w+)\s+(?:publish|update)\s+rate\s+to\s+([\d.]+)\s*Hz",
                r"change\s+(\w+)\s+rate\s+to\s+([\d.]+)",
                r"configure\s+(\w+)\s+(\w+)\s+to\s+(.+)",
            ],
        }

    async def _ensure_session(self):
        """Ensure HTTP session exists."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    def parse_command(self, text: str) -> Command | None:
        """Parse natural language command into structured Command.

        Args:
            text: Natural language input

        Returns:
            Parsed Command or None if no match
        """
        text = text.lower().strip()

        # Try each pattern category
        for action, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()

                    if action == "start_simulator":
                        return Command(action="start", target=groups[0] if groups else None, confidence=0.9)

                    elif action == "stop_simulator":
                        return Command(action="stop", target=groups[0] if groups else None, confidence=0.9)

                    elif action == "inject_fault":
                        sensor_path = groups[0].strip() if groups else None
                        duration = int(groups[1]) if len(groups) > 1 else 10

                        # Try to resolve sensor path
                        if sensor_path and "/" not in sensor_path:
                            # Try to find sensor by name
                            sensor_path = self._resolve_sensor_name(sensor_path)

                        return Command(
                            action="inject_fault",
                            target=sensor_path,
                            parameters={"duration": duration},
                            confidence=0.85,
                        )

                    elif action == "get_status":
                        return Command(action="status", confidence=0.95)

                    elif action == "list_sensors":
                        industry = groups[0] if groups else "all"
                        return Command(action="list_sensors", target=industry, confidence=0.9)

                    elif action == "configure":
                        protocol = groups[0] if groups else None
                        value = groups[1] if len(groups) > 1 else None
                        return Command(
                            action="configure",
                            target=protocol,
                            parameters={"rate_hz": float(value) if value else None},
                            confidence=0.8,
                        )

        # Fallback: try to extract key verbs and nouns
        return self._fallback_parse(text)

    def _resolve_sensor_name(self, name: str) -> str | None:
        """Try to resolve a partial sensor name to full path.

        Args:
            name: Partial sensor name (e.g., "crusher power")

        Returns:
            Full sensor path (e.g., "mining/crusher_1_motor_power") or None
        """
        name_lower = name.lower().replace(" ", "_")

        for industry in IndustryType:
            sensors = get_industry_sensors(industry)
            for sim in sensors:
                sensor_name = sim.config.name.lower()
                if name_lower in sensor_name or sensor_name in name_lower:
                    return f"{industry.value}/{sim.config.name}"

        return None

    def _fallback_parse(self, text: str) -> Command | None:
        """Fallback parser using keyword matching.

        Args:
            text: Natural language input

        Returns:
            Parsed Command or None
        """
        # Check for common action keywords
        if any(word in text for word in ["start", "run", "launch", "begin"]):
            # Try to extract protocol
            for protocol in ["opcua", "mqtt", "modbus"]:
                if protocol in text:
                    return Command(action="start", target=protocol, confidence=0.7)

        if any(word in text for word in ["stop", "halt", "shutdown", "kill"]):
            for protocol in ["opcua", "mqtt", "modbus"]:
                if protocol in text:
                    return Command(action="stop", target=protocol, confidence=0.7)

        if "status" in text or "running" in text:
            return Command(action="status", confidence=0.8)

        if "fault" in text or "break" in text or "inject" in text:
            return Command(action="inject_fault", confidence=0.6)

        if "sensor" in text and any(word in text for word in ["list", "show", "get"]):
            return Command(action="list_sensors", confidence=0.7)

        return None

    async def execute_command(self, command: Command) -> dict[str, Any]:
        """Execute a parsed command.

        Args:
            command: Parsed command to execute

        Returns:
            Result dictionary with success status and message
        """
        await self._ensure_session()

        try:
            if command.action == "start":
                return await self._start_simulator(command.target or "all")

            elif command.action == "stop":
                return await self._stop_simulator(command.target or "all")

            elif command.action == "inject_fault":
                return await self._inject_fault(
                    command.target, command.parameters.get("duration", 10) if command.parameters else 10
                )

            elif command.action == "status":
                return await self._get_status()

            elif command.action == "list_sensors":
                return self._list_sensors(command.target or "all")

            elif command.action == "configure":
                return await self._configure(command.target, command.parameters)

            else:
                return {"success": False, "message": f"Unknown action: {command.action}"}

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {"success": False, "message": f"Error executing command: {e}"}

    async def _start_simulator(self, protocol: str) -> dict[str, Any]:
        """Start simulator for given protocol."""
        if protocol == "all":
            protocols = ["opcua", "mqtt", "modbus"]
        else:
            protocols = [protocol.lower()]

        results = []
        for proto in protocols:
            try:
                async with self._session.post(f"{self.api_base_url}/simulators/{proto}/start") as resp:
                    if resp.status == 200:
                        results.append(f"✓ {proto.upper()} started")
                    else:
                        error = await resp.text()
                        results.append(f"✗ {proto.upper()} failed: {error}")
            except Exception as e:
                results.append(f"✗ {proto.upper()} error: {e}")

        return {"success": True, "message": "\n".join(results)}

    async def _stop_simulator(self, protocol: str) -> dict[str, Any]:
        """Stop simulator for given protocol."""
        if protocol == "all":
            protocols = ["opcua", "mqtt", "modbus"]
        else:
            protocols = [protocol.lower()]

        results = []
        for proto in protocols:
            try:
                async with self._session.post(f"{self.api_base_url}/simulators/{proto}/stop") as resp:
                    if resp.status == 200:
                        results.append(f"✓ {proto.upper()} stopped")
                    else:
                        error = await resp.text()
                        results.append(f"✗ {proto.upper()} failed: {error}")
            except Exception as e:
                results.append(f"✗ {proto.upper()} error: {e}")

        return {"success": True, "message": "\n".join(results)}

    async def _inject_fault(self, sensor_path: str | None, duration: float) -> dict[str, Any]:
        """Inject fault into sensor."""
        if not sensor_path:
            return {
                "success": False,
                "message": "No sensor specified. Try: 'inject fault into mining/crusher_1_motor_power for 30 seconds'",
            }

        # Determine protocol from sensor path
        protocol = "opcua"  # Default
        if "mqtt" in sensor_path.lower():
            protocol = "mqtt"
        elif "modbus" in sensor_path.lower():
            protocol = "modbus"

        payload = {"protocol": protocol, "sensor_path": sensor_path, "duration": duration}

        try:
            async with self._session.post(f"{self.api_base_url}/fault/inject", json=payload) as resp:
                if resp.status == 200:
                    return {"success": True, "message": f"✓ Fault injected into {sensor_path} for {duration} seconds"}
                else:
                    error = await resp.text()
                    return {"success": False, "message": f"Failed to inject fault: {error}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    async def _get_status(self) -> dict[str, Any]:
        """Get status of all simulators."""
        try:
            async with self._session.get(f"{self.api_base_url}/simulators") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    simulators = data.get("simulators", {})

                    lines = ["=== Simulator Status ===", ""]
                    for proto, info in simulators.items():
                        status = "🟢 RUNNING" if info.get("running") else "🔴 STOPPED"
                        lines.append(f"{proto.upper()}: {status}")

                        if info.get("running"):
                            sensor_count = info.get("sensor_count", 0)
                            update_count = info.get("update_count") or info.get("message_count", 0)
                            lines.append(f"  Sensors: {sensor_count}")
                            lines.append(f"  Updates: {update_count}")

                        lines.append("")

                    return {"success": True, "message": "\n".join(lines), "data": simulators}
                else:
                    error = await resp.text()
                    return {"success": False, "message": f"Failed to get status: {error}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    def _list_sensors(self, industry: str) -> dict[str, Any]:
        """List sensors for given industry."""
        if industry == "all":
            industries = list(IndustryType)
        else:
            try:
                industries = [IndustryType(industry.lower())]
            except ValueError:
                return {
                    "success": False,
                    "message": f"Unknown industry: {industry}. Options: mining, utilities, manufacturing, oil_gas",
                }

        lines = []
        total_count = 0

        for ind in industries:
            sensors = get_industry_sensors(ind)
            lines.append(f"\n=== {ind.value.upper()} ({len(sensors)} sensors) ===")

            for sim in sensors:
                cfg = sim.config
                lines.append(f"  {cfg.name}")
                lines.append(f"    Range: {cfg.min_value} - {cfg.max_value} {cfg.unit}")
                lines.append(f"    Type: {cfg.sensor_type.value}")

            total_count += len(sensors)

        lines.insert(0, f"Total: {total_count} sensors\n")

        return {"success": True, "message": "\n".join(lines)}

    async def _configure(self, target: str | None, parameters: dict[str, Any] | None) -> dict[str, Any]:
        """Configure simulator parameters."""
        return {
            "success": False,
            "message": "Configuration via API not yet implemented. Please edit config.yaml manually.",
        }

    async def process_input(self, text: str) -> str:
        """Process natural language input and return response.

        Args:
            text: Natural language command

        Returns:
            Response message
        """
        # Parse command
        command = self.parse_command(text)

        if not command:
            return (
                "❌ Sorry, I couldn't understand that command. Try:\n"
                "  - 'start the opcua simulator'\n"
                "  - 'show me all sensors'\n"
                "  - 'inject fault into mining/crusher_1_motor_power for 30 seconds'\n"
                "  - 'what's the status?'"
            )

        # Low confidence warning
        if command.confidence < 0.7:
            logger.warning(f"Low confidence parse: {command.confidence:.2f} for '{text}'")

        # Execute command
        result = await self.execute_command(command)

        if result["success"]:
            return result["message"]
        else:
            return f"❌ {result['message']}"


async def interactive_mode():
    """Run agent in interactive mode."""
    print("=== OT Simulator Agent Operator ===")
    print("Natural language interface for simulator control")
    print("Type 'help' for examples, 'quit' to exit\n")

    agent = AgentOperator()

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "bye"):
                print("Goodbye!")
                break

            if user_input.lower() == "help":
                print(
                    """
Examples:
  • start the opcua simulator
  • stop mqtt simulator
  • inject fault into mining/crusher_1_motor_power for 60 seconds
  • what's the status?
  • show me all sensors in utilities
  • list mining sensors
  • start all simulators
  • stop all simulators
                """
                )
                continue

            # Process command
            response = await agent.process_input(user_input)
            print(f"\nAgent: {response}\n")

    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(interactive_mode())
