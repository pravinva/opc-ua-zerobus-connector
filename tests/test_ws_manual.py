#!/usr/bin/env python3
"""Manual WebSocket test to debug NL AI integration."""

import asyncio
import json
import aiohttp


async def test_websocket():
    """Test WebSocket connection and natural language commands."""
    ws_url = "ws://localhost:8989/ws"

    print(f"Connecting to {ws_url}...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                print("✅ Connected!")

                # Send a natural language command
                command = {
                    "type": "nlp_command",
                    "text": "What is SAREF?"
                }

                print(f"\nSending command: {json.dumps(command, indent=2)}")
                await ws.send_json(command)

                print("\nWaiting for response (10s timeout)...")

                # Listen for responses
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        print(f"\nReceived message:")
                        print(json.dumps(data, indent=2))

                        # Check if this is the response to our command
                        if data.get("type") == "nlp_response":
                            print("\n✅ Got NLP response!")
                            return True

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"❌ WebSocket error: {ws.exception()}")
                        return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_websocket())
