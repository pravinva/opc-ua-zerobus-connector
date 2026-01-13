"""WebSocket server for real-time sensor data streaming.

Provides bidirectional real-time communication for:
- Live sensor data streaming
- Natural language command processing
- Simulator status updates
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from aiohttp import web
import aiohttp

logger = logging.getLogger("ot_simulator.websocket")


class WebSocketServer:
    """WebSocket server for real-time data streaming."""

    def __init__(self, simulator_manager, llm_agent=None):
        """Initialize WebSocket server.

        Args:
            simulator_manager: Reference to simulator manager (holds all protocol simulators)
            llm_agent: Optional LLM agent for natural language processing
        """
        self.manager = simulator_manager
        self.llm_agent = llm_agent
        self.connections: set[web.WebSocketResponse] = set()
        self.subscriptions: dict[web.WebSocketResponse, set[str]] = {}
        self.broadcast_task = None
        self.update_interval = 0.5  # 500ms default

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.connections.add(ws)
        logger.info(f"WebSocket connection established. Total connections: {len(self.connections)}")

        # Send initial status
        await self.send_status_update(ws)

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "message": "Invalid JSON"})
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
                        await ws.send_json({"type": "error", "message": str(e)})
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.connections.discard(ws)
            if ws in self.subscriptions:
                del self.subscriptions[ws]
            logger.info(f"WebSocket connection closed. Total connections: {len(self.connections)}")

        return ws

    async def handle_message(self, ws: web.WebSocketResponse, data: dict[str, Any]):
        """Handle incoming WebSocket message.

        Args:
            ws: WebSocket connection
            data: Parsed JSON message
        """
        msg_type = data.get("type")

        if msg_type == "subscribe":
            # Subscribe to sensor data
            sensors = data.get("sensors", [])
            if ws not in self.subscriptions:
                self.subscriptions[ws] = set()
            self.subscriptions[ws].update(sensors)
            logger.info(f"Client subscribed to {len(sensors)} sensors")
            await ws.send_json({"type": "subscribed", "sensors": list(self.subscriptions[ws])})

        elif msg_type == "unsubscribe":
            # Unsubscribe from sensor data
            sensors = data.get("sensors", [])
            if ws in self.subscriptions:
                self.subscriptions[ws].difference_update(sensors)
            await ws.send_json({"type": "unsubscribed", "sensors": sensors})

        elif msg_type == "nlp_command":
            # Natural language command
            text = data.get("text", "")
            logger.info(f"Received NLP command: '{text}'")

            if not text:
                logger.warning("Empty NLP command text")
                await ws.send_json({"type": "error", "message": "Empty command text"})
                return

            if self.llm_agent:
                try:
                    logger.info(f"Processing NLP command with LLM: '{text}'")
                    # Process with LLM
                    conversation_history = data.get("history", [])
                    command = await self.llm_agent.parse_with_llm(text, conversation_history)
                    logger.info(f"LLM parsed command: action={command.action}, target={command.target}")

                    # Execute command
                    logger.info(f"Executing command: {command.action}")
                    result = await self.execute_command(command)
                    logger.info(f"Command execution result: success={result.get('success', True)}, message={result.get('message', '')[:100]}")

                    # Phase 2: Have LLM synthesize the backend response into natural language
                    # Skip synthesis for actions that return detailed formatted data
                    if command.action in ["chat", "list_sensors", "status"]:
                        # Use raw backend message or reasoning directly
                        if command.action == "chat":
                            final_message = command.reasoning
                        else:
                            final_message = result.get("message", "")
                    else:
                        # Synthesize for simple actions (start, stop, inject_fault)
                        try:
                            synthesized_response = await self.llm_agent.synthesize_response(
                                user_query=text,
                                command=command,
                                backend_result=result
                            )
                            final_message = synthesized_response
                        except Exception as synth_error:
                            logger.warning(f"LLM synthesis failed, using backend message: {synth_error}")
                            final_message = result.get("message", "")

                    # Send response
                    response_data = {
                        "type": "nlp_response",
                        "action": command.action,
                        "target": command.target,
                        "parameters": command.parameters,
                        "reasoning": command.reasoning,
                        "success": result.get("success", True),
                        "message": final_message,
                    }
                    logger.info(f"Sending NLP response: action={command.action}, success={response_data['success']}")

                    try:
                        await ws.send_json(response_data)
                        logger.info("✓ NLP response sent successfully via WebSocket")
                    except Exception as send_error:
                        logger.error(f"✗ Failed to send WebSocket response: {send_error}", exc_info=True)

                except Exception as e:
                    logger.error(f"Error processing NLP command: {e}", exc_info=True)
                    try:
                        await ws.send_json(
                            {
                                "type": "nlp_response",
                                "action": "chat",
                                "reasoning": f"Error processing command: {str(e)}",
                                "success": False,
                            }
                        )
                        logger.info("✓ Error response sent via WebSocket")
                    except Exception as send_error:
                        logger.error(f"✗ Failed to send error response: {send_error}", exc_info=True)
            else:
                logger.warning("LLM agent not available")
                await ws.send_json({"type": "error", "message": "Natural language processing not available"})

        elif msg_type == "get_status":
            # Get current simulator status
            await self.send_status_update(ws)

        elif msg_type == "set_update_rate":
            # Change update rate
            interval = data.get("interval", 0.5)
            self.update_interval = max(0.1, min(5.0, interval))  # Clamp between 100ms and 5s
            await ws.send_json({"type": "update_rate_changed", "interval": self.update_interval})

        else:
            await ws.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    async def execute_command(self, command) -> dict[str, Any]:
        """Execute a parsed command from LLM.

        Args:
            command: Command object from LLM agent

        Returns:
            Result dictionary with success status and message
        """
        try:
            if command.action == "start":
                # Start simulator
                protocol = command.target
                logger.info(f"Start command: protocol={protocol}, available={list(self.manager.simulators.keys())}")
                if protocol in self.manager.simulators:
                    logger.info(f"Starting {protocol} simulator...")
                    await self.manager.start_simulator(protocol)
                    logger.info(f"✓ {protocol} simulator started successfully")
                    return {"success": True, "message": f"{protocol.upper()} started"}
                else:
                    logger.warning(f"Unknown protocol: {protocol}")
                    return {"success": False, "message": f"Unknown protocol: {protocol}"}

            elif command.action == "stop":
                # Stop simulator
                protocol = command.target
                logger.info(f"Stop command: protocol={protocol}")
                if protocol in self.manager.simulators:
                    logger.info(f"Stopping {protocol} simulator...")
                    await self.manager.stop_simulator(protocol)
                    logger.info(f"✓ {protocol} simulator stopped successfully")
                    return {"success": True, "message": f"{protocol.upper()} stopped"}
                else:
                    logger.warning(f"Unknown protocol: {protocol}")
                    return {"success": False, "message": f"Unknown protocol: {protocol}"}

            elif command.action == "inject_fault":
                # Inject fault
                sensor_path = command.target
                duration = command.parameters.get("duration", 60) if command.parameters else 60
                await self.manager.inject_fault(sensor_path, duration)
                return {"success": True, "message": f"Fault injected for {duration}s"}

            elif command.action == "status":
                # Generate formatted status report
                lines = ["=== Simulator Status ===", ""]

                for proto, simulator in self.manager.simulators.items():
                    # Check if simulator is running
                    if hasattr(simulator, "_running"):
                        is_running = simulator._running
                    elif hasattr(simulator, "get_stats"):
                        stats = simulator.get_stats()
                        is_running = stats.get("running", False)
                    else:
                        is_running = False

                    status_icon = "🟢 RUNNING" if is_running else "🔴 STOPPED"
                    lines.append(f"{proto.upper()}: {status_icon}")

                    if is_running:
                        # Get sensor count
                        if hasattr(simulator, "simulators"):
                            sensor_count = len(simulator.simulators)
                        elif hasattr(simulator, "get_stats"):
                            stats = simulator.get_stats()
                            sensor_count = stats.get("sensor_count", 0)
                        else:
                            sensor_count = 0

                        lines.append(f"  Sensors: {sensor_count}")

                    lines.append("")

                return {"success": True, "message": "\n".join(lines)}

            elif command.action == "list_sensors":
                # Generate formatted sensor list
                from ot_simulator.sensor_models import IndustryType, get_industry_sensors

                industry = command.target or "all"

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

            elif command.action == "chat":
                # Conversational response
                return {"success": True, "message": command.reasoning}

            else:
                return {"success": False, "message": f"Unknown action: {command.action}"}

        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    async def send_status_update(self, ws: web.WebSocketResponse):
        """Send current simulator status to WebSocket client."""
        status = {"type": "status_update", "timestamp": time.time(), "simulators": {}}

        for protocol, simulator in self.manager.simulators.items():
            # Use get_stats() if available, otherwise use _running flag
            if hasattr(simulator, "get_stats"):
                stats = simulator.get_stats()
                status["simulators"][protocol] = {
                    "running": stats.get("running", False),
                    "sensor_count": stats.get("sensor_count", 0),
                    "update_count": stats.get("update_count") or stats.get("message_count", 0),
                    "errors": stats.get("errors", 0),
                }
            else:
                # Fallback for simulators without get_stats()
                status["simulators"][protocol] = {
                    "running": getattr(simulator, "_running", False),
                    "sensor_count": len(simulator.simulators) if hasattr(simulator, "simulators") else 0,
                    "update_count": 0,
                    "errors": 0,
                }

        await ws.send_json(status)

    async def broadcast_sensor_data(self):
        """Periodically broadcast sensor data to subscribed clients."""
        logger.info("Starting sensor data broadcast task")

        while True:
            try:
                await asyncio.sleep(self.update_interval)

                if not self.connections:
                    continue

                # Collect all subscribed sensor paths
                all_sensors = set()
                for sensors in self.subscriptions.values():
                    all_sensors.update(sensors)

                if not all_sensors:
                    continue

                # Get current sensor values
                sensor_data = {}
                for sensor_path in all_sensors:
                    value = self.manager.get_sensor_value(sensor_path)
                    if value is not None:
                        sensor_data[sensor_path] = value

                if not sensor_data:
                    continue

                # Send to each subscribed client
                timestamp = time.time()
                disconnected = []

                for ws in list(self.connections):
                    if ws in self.subscriptions and self.subscriptions[ws]:
                        # Filter to only subscribed sensors for this client
                        client_data = {
                            sensor: value for sensor, value in sensor_data.items() if sensor in self.subscriptions[ws]
                        }

                        if client_data:
                            try:
                                await ws.send_json(
                                    {"type": "sensor_data", "timestamp": timestamp, "sensors": client_data}
                                )
                            except Exception as e:
                                logger.error(f"Error sending to client: {e}")
                                disconnected.append(ws)

                # Clean up disconnected clients
                for ws in disconnected:
                    self.connections.discard(ws)
                    if ws in self.subscriptions:
                        del self.subscriptions[ws]

            except asyncio.CancelledError:
                logger.info("Sensor data broadcast task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause on error

    async def start_broadcast(self):
        """Start the broadcast task."""
        if self.broadcast_task is None:
            self.broadcast_task = asyncio.create_task(self.broadcast_sensor_data())

    async def stop_broadcast(self):
        """Stop the broadcast task."""
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
            self.broadcast_task = None

    async def broadcast_status_update(self):
        """Broadcast status update to all connected clients."""
        if not self.connections:
            return

        status = {"type": "status_update", "timestamp": time.time(), "simulators": {}}

        for protocol, simulator in self.manager.simulators.items():
            # Use get_stats() if available, otherwise use _running flag
            if hasattr(simulator, "get_stats"):
                stats = simulator.get_stats()
                status["simulators"][protocol] = {
                    "running": stats.get("running", False),
                    "sensor_count": stats.get("sensor_count", 0),
                    "update_count": stats.get("update_count") or stats.get("message_count", 0),
                    "errors": stats.get("errors", 0),
                }
            else:
                # Fallback for simulators without get_stats()
                status["simulators"][protocol] = {
                    "running": getattr(simulator, "_running", False),
                    "sensor_count": len(simulator.simulators) if hasattr(simulator, "simulators") else 0,
                    "update_count": 0,
                    "errors": 0,
                }

        for ws in list(self.connections):
            try:
                await ws.send_json(status)
            except Exception as e:
                logger.error(f"Error broadcasting status: {e}")
