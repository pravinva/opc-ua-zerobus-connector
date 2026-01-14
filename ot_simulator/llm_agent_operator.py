"""LLM-powered natural language agent operator for OT simulator.

Uses Databricks Foundation Models (Claude Sonnet 4.5) for true natural language understanding.

Model Endpoint: databricks-claude-sonnet-4-5

Usage:
    python -m ot_simulator.llm_agent_operator

Examples:
    "Start the OPC-UA simulator and show me what's happening"
    "Start the simulator for mining opcua"
    "I need to test a fault scenario - inject a fault into the mining crusher for 60 seconds"
    "Can you give me a summary of all the sensors we have?"
    "Something seems wrong with utilities - what's the status?"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

from ot_simulator.sensor_models import IndustryType, get_industry_sensors

logger = logging.getLogger("ot_simulator.llm_agent")


@dataclass
class Command:
    """Parsed command from LLM."""

    action: str
    target: str | None = None
    parameters: dict[str, Any] | None = None
    reasoning: str = ""


class LLMAgentOperator:
    """LLM-powered natural language agent using Databricks Foundation Models."""

    def __init__(
        self,
        api_base_url: str | None = None,
        databricks_profile: str | None = None,
        model_name: str | None = None,
        config_path: str | None = None,
    ):
        """Initialize LLM agent operator.

        Args:
            api_base_url: Base URL for simulator API (overrides config file)
            databricks_profile: Profile name from ~/.databrickscfg (overrides config file)
            model_name: Foundation model endpoint to use (overrides config file)
            config_path: Path to YAML config file (defaults to ot_simulator/llm_agent_config.yaml)
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent / "llm_agent_config.yaml"
        else:
            config_path = Path(config_path)

        config = {}
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {config_path}")
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")

        # Apply configuration with CLI overrides
        self.api_base_url = api_base_url or config.get("simulator", {}).get("api_base_url", "http://localhost:8989/api")
        databricks_profile = databricks_profile or config.get("databricks", {}).get("profile", "DEFAULT")
        self.model_name = model_name or config.get("databricks", {}).get(
            "model_endpoint", "databricks-claude-sonnet-4-5"
        )
        self.max_tokens = config.get("llm", {}).get("max_tokens", 500)
        self.temperature = config.get("llm", {}).get("temperature", 0.1)
        self.history_length = config.get("llm", {}).get("history_length", 5)

        self._session: aiohttp.ClientSession | None = None

        # Initialize Databricks client
        # Set profile environment variable for SDK
        os.environ["DATABRICKS_CONFIG_PROFILE"] = databricks_profile
        self.workspace_client = WorkspaceClient()

        logger.info(f"Initialized LLM agent with model: {self.model_name}")
        logger.info(f"Using Databricks profile: {databricks_profile}")
        logger.info(f"Simulator API: {self.api_base_url}")

    async def _ensure_session(self):
        """Ensure HTTP session exists."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_system_prompt(self) -> str:
        """Get system prompt for the LLM."""
        # Get available sensors
        sensor_summary = []
        total_sensors = 0
        for industry in IndustryType:
            sensors = get_industry_sensors(industry)
            count = len(sensors)
            total_sensors += count
            sensor_summary.append(f"{industry.value}: {count}")

        sensors_info = ", ".join(sensor_summary)

        return f"""You are an intelligent operator assistant for an industrial OT (Operational Technology) simulator with W3C Web of Things (WoT) capabilities.
Your job is to help users control and monitor a multi-protocol simulator that generates realistic sensor data with semantic metadata for industrial environments.

CURRENT SIMULATOR STATE:
- Total Sensors: {total_sensors} across {len(IndustryType)} industries
- Available Protocols: OPC-UA, MQTT, Modbus TCP
- W3C WoT: Thing Description available at /api/opcua/thing-description
- Semantic Types: 70+ types from SAREF, SOSA/SSN ontologies
- QUDT Units: Standardized unit URIs for 350+ sensors
- Currently Running: Check status to see which protocols are active

SENSORS BY INDUSTRY:
{sensors_info}

W3C WOT KNOWLEDGE BASE:
You have deep knowledge of:

1. SAREF (Smart Appliances Reference) Ontology:
   - saref:TemperatureSensor: Measures temperature (50+ in simulator)
   - saref:PressureSensor: Measures pressure (30+ in simulator)
   - saref:PowerSensor: Measures electrical power (40+ in simulator)
   - saref:ElectricitySensor: Measures current/voltage (25+ in simulator)
   - saref:HumiditySensor, saref:LevelSensor, saref:FlowSensor, etc.

2. SOSA/SSN (Semantic Sensor Network) Ontology:
   - sosa:Sensor: Generic sensor for observations
   - sosa:observes: Links sensor to observed property
   - Used for: Vibration, speed, force, torque sensors

3. QUDT (Quantities, Units, Dimensions, Types):
   - Standardized unit URIs (e.g., http://qudt.org/vocab/unit/DEG_C for °C)
   - Enables automatic unit conversion
   - Machine-readable for analytics

4. W3C WoT Thing Description Structure:
   - properties: 379 sensors with semantic metadata
   - forms: OPC-UA binding with nodeIds
   - @context: JSON-LD contexts for ontologies
   - security: Currently nosec (development mode)

SEMANTIC QUERY CAPABILITIES:
- Filter by semantic type (e.g., "all temperature sensors")
- Filter by industry (e.g., "pressure sensors in oil & gas")
- Filter by unit type (e.g., "sensors measuring in kilowatts")
- Compare across industries/protocols
- Explain ontology concepts in plain language

AVAILABLE COMMANDS:
You must respond with a JSON object containing ONE of these actions:

1. START SIMULATOR
{{
  "action": "start",
  "target": "opcua|mqtt|modbus|all",
  "reasoning": "Why you chose this action"
}}

2. STOP SIMULATOR
{{
  "action": "stop",
  "target": "opcua|mqtt|modbus|all",
  "reasoning": "Why you chose this action"
}}

3. INJECT FAULT
{{
  "action": "inject_fault",
  "target": "industry/sensor_name",
  "parameters": {{"duration": seconds}},
  "reasoning": "Why you chose this sensor and duration"
}}

4. GET STATUS
{{
  "action": "status",
  "reasoning": "What information the user wants to see"
}}

5. LIST SENSORS
{{
  "action": "list_sensors",
  "target": "industry_name|all",
  "reasoning": "Which sensors to show"
}}

6. CONVERSATIONAL RESPONSE (when user is not requesting an action)
{{
  "action": "chat",
  "reasoning": "Conversational response to user"
}}

7. WOT SEMANTIC QUERY (filter WoT browser by semantic criteria)
{{
  "action": "wot_query",
  "parameters": {{
    "semantic_type": "saref:TemperatureSensor|saref:PowerSensor|sosa:Sensor|etc",
    "industry": "mining|utilities|manufacturing|oil_gas|etc",
    "unit": "°C|kW|bar|PSI|etc",
    "search_text": "optional keyword search"
  }},
  "reasoning": "What semantic filters to apply and why"
}}

8. EXPLAIN WOT CONCEPT (educational response about WoT/ontologies)
{{
  "action": "explain_wot_concept",
  "target": "saref|sosa|qudt|thing_description|semantic_type|ontology",
  "parameters": {{"context": "specific question or concept"}},
  "reasoning": "What concept to explain"
}}

9. RECOMMEND SENSORS (suggest sensors for a use case)
{{
  "action": "recommend_sensors",
  "parameters": {{
    "use_case": "equipment_health|energy_monitoring|safety|predictive_maintenance|etc",
    "industry": "optional industry filter"
  }},
  "reasoning": "Why these sensors fit the use case"
}}

10. COMPARE SENSORS (comparative analysis)
{{
  "action": "compare_sensors",
  "parameters": {{
    "dimension": "by_industry|by_semantic_type|by_unit|by_range",
    "focus": "optional specific aspect to compare"
  }},
  "reasoning": "What insights to provide"
}}

SENSOR PATH FORMAT: "industry/sensor_name"
Examples:
- mining/crusher_1_motor_power
- utilities/grid_main_frequency
- manufacturing/robot_1_joint_1_torque
- oil_gas/pipeline_1_flow

USE CASE KNOWLEDGE (for sensor recommendations):

1. EQUIPMENT HEALTH MONITORING:
   - Vibration sensors (bearing wear, imbalance detection)
   - Temperature sensors (overheating detection)
   - Current sensors (motor load analysis)
   - Recommended: crusher_1_vibration_x/y, transformer_1_oil_temp, robot_1_joint_torques

2. ENERGY MONITORING:
   - Power sensors (consumption tracking)
   - Voltage/current sensors (power quality)
   - Efficiency metrics (inverter_1_efficiency)
   - Recommended: All saref:PowerSensor types, grid_main_frequency

3. SAFETY & COMPLIANCE:
   - Gas detection (toxic gas monitoring)
   - Pressure sensors (overpressure risk)
   - Temperature sensors (fire risk)
   - Recommended: h2s_detector_1_ppm, separator_1_pressure, flare_temperature

4. PREDICTIVE MAINTENANCE:
   - Vibration trending (mechanical degradation)
   - Temperature trending (thermal stress)
   - Current trending (electrical wear)
   - Recommended: All vibration + bearing_temp sensors

5. PROCESS OPTIMIZATION:
   - Flow sensors (throughput monitoring)
   - Level sensors (inventory tracking)
   - Speed sensors (cycle time optimization)
   - Recommended: pipeline_1_flow, tank levels, conveyor_1_speed

IMPORTANT RULES:
1. Always respond with valid JSON only, no extra text
2. When user asks about a specific protocol (MQTT, Modbus), you MUST call the status action to get current state
3. Provide complete, accurate answers - don't make assumptions about what's running
4. For conversational queries, provide helpful context about ALL available protocols (OPC-UA, MQTT, Modbus TCP)
5. Use exact sensor names from the available sensors
6. For fault injection, suggest reasonable durations (10-120 seconds)
7. Be proactive - suggest related actions when appropriate
8. For WoT queries, use semantic types (saref:, sosa:) not just sensor names
9. When explaining WoT concepts, be educational but concise
10. For recommendations, suggest 3-5 specific sensors with reasoning

AVAILABLE SENSORS BY INDUSTRY:

MINING (16 sensors):
- crusher_1_motor_power, crusher_1_vibration_x, crusher_1_vibration_y
- crusher_1_bearing_temp, conveyor_1_speed, conveyor_1_motor_current
- ore_flow_rate, slurry_density, pump_1_discharge_pressure
- pump_1_flow, mill_1_speed, mill_1_power
- stockpile_level, dust_concentration, ambient_temperature, wind_speed

UTILITIES (17 sensors):
- grid_main_frequency, grid_main_voltage, transformer_1_load
- transformer_1_oil_temp, transformer_1_winding_temp, substation_1_power_factor
- feeder_1_current, feeder_1_voltage, battery_bank_1_voltage
- battery_bank_1_current, battery_bank_1_soc, inverter_1_power
- inverter_1_efficiency, solar_array_1_voltage, solar_array_1_current
- wind_turbine_1_speed, wind_turbine_1_power

MANUFACTURING (18 sensors):
- robot_1_joint_1_torque through robot_1_joint_6_torque (6 sensors)
- robot_1_tcp_force_x, robot_1_tcp_force_y, robot_1_tcp_force_z
- assembly_line_speed, press_1_force, press_1_position
- welder_1_current, welder_1_voltage, paint_booth_temperature
- paint_booth_humidity

OIL_GAS (27 sensors):
- pipeline_1_flow, pipeline_1_pressure, pipeline_1_temperature
- compressor_1_discharge_pressure, compressor_1_suction_pressure
- compressor_1_motor_power, compressor_1_vibration
- separator_1_pressure, separator_1_level, separator_1_temperature
- tank_1_level through tank_3_level (3 sensors)
- pump_2_discharge_pressure through pump_4_discharge_pressure (3 sensors)
- pump_2_flow through pump_4_flow (3 sensors)
- flare_flow, flare_temperature, wellhead_1_pressure
- wellhead_1_temperature, wellhead_1_flow, gas_detector_1_ppm
- h2s_detector_1_ppm

Remember: Always respond with ONLY the JSON object, no additional text."""

    async def parse_with_llm(self, user_input: str, conversation_history: list[dict] | None = None) -> Command:
        """Parse user input using Databricks Foundation Model.

        Args:
            user_input: User's natural language input
            conversation_history: Optional conversation history for context

        Returns:
            Parsed Command object
        """
        try:
            # Build messages for chat API
            messages = []

            # Add system prompt as first message
            messages.append(ChatMessage(role=ChatMessageRole.SYSTEM, content=self._get_system_prompt()))

            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-self.history_length :]:  # Last N messages for context
                    messages.append(ChatMessage(role=ChatMessageRole(msg["role"]), content=msg["content"]))

            # Add current user message
            messages.append(ChatMessage(role=ChatMessageRole.USER, content=user_input))

            # Call Databricks Foundation Model API
            logger.info(f"Calling Databricks FM API with model: {self.model_name}")

            response = self.workspace_client.serving_endpoints.query(
                name=self.model_name, messages=messages, max_tokens=self.max_tokens, temperature=self.temperature
            )

            # Extract response
            if response.choices and len(response.choices) > 0:
                response_text = response.choices[0].message.content.strip()
                logger.info(f"LLM Response: {response_text[:200]}...")

                # Parse JSON response
                try:
                    # Extract JSON from response (might have markdown code blocks)
                    if "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        response_text = response_text[json_start:json_end].strip()
                    elif "```" in response_text:
                        json_start = response_text.find("```") + 3
                        json_end = response_text.find("```", json_start)
                        response_text = response_text[json_start:json_end].strip()

                    command_data = json.loads(response_text)

                    return Command(
                        action=command_data.get("action", "chat"),
                        target=command_data.get("target"),
                        parameters=command_data.get("parameters"),
                        reasoning=command_data.get("reasoning", ""),
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM JSON response: {e}")
                    logger.error(f"Response text: {response_text}")

                    # Fallback to chat
                    return Command(action="chat", reasoning=response_text)

            # Fallback
            return Command(action="chat", reasoning="I couldn't understand that request.")

        except Exception as e:
            logger.error(f"Error calling LLM: {e}", exc_info=True)
            return Command(action="chat", reasoning=f"I encountered an error: {str(e)}")

    async def synthesize_response(self, user_query: str, command: Command, backend_result: dict[str, Any]) -> str:
        """Synthesize backend result into user-friendly natural language response.

        Args:
            user_query: Original user question
            command: The command that was executed
            backend_result: Result from backend execution

        Returns:
            Natural language response
        """
        synthesis_prompt = f"""You are synthesizing a backend response into user-friendly natural language.

USER QUESTION: "{user_query}"

ACTION TAKEN: {command.action}
{f"TARGET: {command.target}" if command.target else ""}

BACKEND RESULT:
Success: {backend_result.get('success', True)}
{backend_result.get('message', '')}

YOUR TASK:
Convert the backend result into a concise, natural, user-friendly response in 1-3 sentences.
- Be conversational and helpful
- If asking about MQTT/Modbus status and it's stopped, say "MQTT is not currently running" or "Modbus is stopped"
- Highlight important information
- Use emojis appropriately (🟢 for running, 🔴 for stopped)
- Keep it brief but informative

Respond with ONLY the natural language message, no JSON, no extra text."""

        try:
            messages = [ChatMessage(role=ChatMessageRole.USER, content=synthesis_prompt)]

            response = self.workspace_client.serving_endpoints.query(
                name=self.model_name,
                messages=messages,
                max_tokens=200,
                temperature=0.3
            )

            if response.choices and len(response.choices) > 0:
                synthesized = response.choices[0].message.content.strip()
                logger.info(f"Synthesized response: {synthesized}")
                return synthesized

        except Exception as e:
            logger.error(f"Error synthesizing response: {e}")

        # Fallback to backend message
        return backend_result.get('message', 'Operation completed')

    async def execute_command(self, command: Command) -> dict[str, Any]:
        """Execute a parsed command.

        Args:
            command: Parsed command to execute

        Returns:
            Result dictionary with success status and message
        """
        await self._ensure_session()

        try:
            if command.action == "chat":
                return {"success": True, "message": command.reasoning}

            elif command.action == "start":
                return await self._start_simulator(command.target or "all")

            elif command.action == "stop":
                return await self._stop_simulator(command.target or "all")

            elif command.action == "inject_fault":
                duration = command.parameters.get("duration", 10) if command.parameters else 10
                return await self._inject_fault(command.target, duration)

            elif command.action == "status":
                return await self._get_status()

            elif command.action == "list_sensors":
                return self._list_sensors(command.target or "all")

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
            return {"success": False, "message": "No sensor specified"}

        # Determine protocol (default to opcua)
        protocol = "opcua"

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

                    # Show status for all known protocols, even if not registered
                    all_protocols = {"opcua", "mqtt", "modbus"}

                    lines = ["=== Simulator Status ===", ""]
                    for proto in sorted(all_protocols):
                        info = simulators.get(proto, {})
                        is_running = info.get("running", False)
                        status = "🟢 RUNNING" if is_running else "🔴 STOPPED"
                        lines.append(f"{proto.upper()}: {status}")

                        if is_running:
                            sensor_count = info.get("sensor_count", 0)
                            update_count = info.get("update_count") or info.get("message_count", 0)
                            lines.append(f"  Sensors: {sensor_count}")
                            if update_count:
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
                return {"success": False, "message": f"Unknown industry: {industry}"}

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

    async def process_input(self, text: str, conversation_history: list[dict] | None = None) -> tuple[str, Command]:
        """Process natural language input and return response.

        Args:
            text: User's natural language command
            conversation_history: Optional conversation history

        Returns:
            Tuple of (response message, parsed command)
        """
        # Parse with LLM
        command = await self.parse_with_llm(text, conversation_history)

        if command.reasoning:
            logger.info(f"LLM Reasoning: {command.reasoning}")

        # Execute command
        result = await self.execute_command(command)

        response_text = result["message"]

        # Add reasoning if helpful
        if command.reasoning and command.action != "chat":
            response_text = f"{response_text}\n\n💭 {command.reasoning}"

        return response_text, command


async def interactive_mode():
    """Run agent in interactive mode."""
    print("=== OT Simulator LLM Agent (Powered by Databricks Foundation Models) ===")
    print("Using Claude Sonnet 4.5 for natural language understanding")
    print("Type 'help' for examples, 'quit' to exit\n")

    # Try to initialize agent
    try:
        agent = LLMAgentOperator(
            databricks_profile="DEFAULT", model_name="databricks-meta-llama-3-1-70b-instruct"  # Available model
        )
    except Exception as e:
        print(f"❌ Failed to initialize LLM agent: {e}")
        print("Make sure ~/.databrickscfg has DEFAULT profile configured")
        return

    conversation_history = []

    try:
        while True:
            try:
                user_input = input("\n🎤 You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "bye"):
                print("👋 Goodbye!")
                break

            if user_input.lower() == "help":
                print(
                    """
💡 Try these natural language commands:

  • "Start the OPC-UA simulator"
  • "Can you show me what's running?"
  • "I need to test a fault - inject one into the mining crusher for 60 seconds"
  • "What sensors do we have in utilities?"
  • "Everything looks good, stop all simulators"
  • "Give me a status update"

The LLM will understand your intent and execute the appropriate commands!
                """
                )
                continue

            # Add to conversation history
            conversation_history.append({"role": "user", "content": user_input})

            # Process command
            print("\n🤖 Agent: ", end="", flush=True)
            response, command = await agent.process_input(user_input, conversation_history)
            print(response)

            # Add to conversation history
            conversation_history.append({"role": "assistant", "content": response})

            # Keep history manageable
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]

    finally:
        await agent.close()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    asyncio.run(interactive_mode())
