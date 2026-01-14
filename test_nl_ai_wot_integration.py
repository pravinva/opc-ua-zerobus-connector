#!/usr/bin/env python3
"""
End-to-End Test: Natural Language AI + WoT Browser Integration

Tests all Phase 1 and Phase 2 features:
- Semantic query filtering
- Educational explanations
- Smart sensor recommendations
- Comparative analytics
"""

import asyncio
import json
import sys
from typing import Any, Dict

import aiohttp


class NLAIWoTTester:
    """Test harness for NL AI + WoT integration."""

    def __init__(self, base_url: str = "http://localhost:8989"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://") + "/ws"
        self.results = []

    async def test_wot_browser_accessible(self) -> bool:
        """Test 1: Verify WoT browser is accessible."""
        print("\n" + "=" * 80)
        print("TEST 1: WoT Browser Accessibility")
        print("=" * 80)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/wot/browser") as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        if "W3C WoT Thing Description Browser" in html:
                            print("✅ PASS: WoT browser accessible and contains expected title")
                            return True
                        else:
                            print("❌ FAIL: WoT browser missing expected content")
                            return False
                    else:
                        print(f"❌ FAIL: Got status {resp.status}")
                        return False
        except Exception as e:
            print(f"❌ FAIL: Exception - {e}")
            return False

    async def test_thing_description_complete(self) -> bool:
        """Test 2: Verify Thing Description has all 379 properties."""
        print("\n" + "=" * 80)
        print("TEST 2: Thing Description Completeness")
        print("=" * 80)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/opcua/thing-description") as resp:
                    if resp.status == 200:
                        td = await resp.json()
                        prop_count = len(td.get("properties", {}))

                        if prop_count == 379:
                            print(f"✅ PASS: Thing Description has {prop_count} properties")

                            # Sample a few properties to verify structure
                            props = td.get("properties", {})
                            sample_prop = next(iter(props.values()))

                            has_semantic_type = "@type" in sample_prop
                            has_unit = "unit" in sample_prop
                            has_forms = "forms" in sample_prop

                            print(f"   - Has semantic types: {'✅' if has_semantic_type else '❌'}")
                            print(f"   - Has units: {'✅' if has_unit else '❌'}")
                            print(f"   - Has forms: {'✅' if has_forms else '❌'}")

                            return has_semantic_type and has_unit and has_forms
                        else:
                            print(f"❌ FAIL: Expected 379 properties, got {prop_count}")
                            return False
                    else:
                        print(f"❌ FAIL: Got status {resp.status}")
                        return False
        except Exception as e:
            print(f"❌ FAIL: Exception - {e}")
            return False

    async def test_nl_command(self, command: str, expected_action: str) -> bool:
        """Test a natural language command via WebSocket."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.ws_url) as ws:
                    # Send command
                    await ws.send_json({
                        "type": "nlp_command",
                        "text": command
                    })

                    # Wait for response (timeout after 30 seconds for LLM processing)
                    try:
                        # Skip sensor_data messages until we get nlp_response
                        for _ in range(100):  # Max 100 messages
                            msg = await asyncio.wait_for(ws.receive(), timeout=30.0)

                            if msg.type == aiohttp.WSMsgType.TEXT:
                                response = json.loads(msg.data)

                                # Skip sensor_data messages
                                if response.get("type") == "sensor_data":
                                    continue

                                # Found our response
                                if response.get("type") == "nlp_response":
                                    message = response.get("message", "")
                                    success = response.get("success", False)

                                    print(f"   Message: {message[:100]}...")
                                    return success and len(message) > 0

                        print(f"   ⚠️  Did not receive nlp_response after 100 messages")
                        return False

                    except asyncio.TimeoutError:
                        print(f"   ⚠️  Timeout waiting for response")
                        return False

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False

    async def test_semantic_query(self) -> bool:
        """Test 3: Semantic Query - Filter by semantic type."""
        print("\n" + "=" * 80)
        print("TEST 3: Semantic Query (wot_query action)")
        print("=" * 80)

        commands = [
            "Show me all temperature sensors",
            "Filter by saref:PowerSensor",
            "Show sensors in the oil_gas industry",
        ]

        results = []
        for cmd in commands:
            print(f"\nCommand: '{cmd}'")
            result = await self.test_nl_command(cmd, "wot_query")
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Result: {status}")
            results.append(result)

        return all(results)

    async def test_educational_explanations(self) -> bool:
        """Test 4: Educational Explanations - Explain WoT concepts."""
        print("\n" + "=" * 80)
        print("TEST 4: Educational Explanations (explain_wot_concept action)")
        print("=" * 80)

        commands = [
            "What is SAREF?",
            "Explain semantic types",
            "What does SOSA mean?",
        ]

        results = []
        for cmd in commands:
            print(f"\nCommand: '{cmd}'")
            result = await self.test_nl_command(cmd, "explain_wot_concept")
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Result: {status}")
            results.append(result)

        return all(results)

    async def test_sensor_recommendations(self) -> bool:
        """Test 5: Smart Recommendations - Recommend sensors for use cases."""
        print("\n" + "=" * 80)
        print("TEST 5: Smart Recommendations (recommend_sensors action)")
        print("=" * 80)

        commands = [
            "I need sensors for equipment health monitoring",
            "What sensors should I use for energy monitoring?",
            "Recommend sensors for predictive maintenance",
        ]

        results = []
        for cmd in commands:
            print(f"\nCommand: '{cmd}'")
            result = await self.test_nl_command(cmd, "recommend_sensors")
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Result: {status}")
            results.append(result)

        return all(results)

    async def test_comparative_analytics(self) -> bool:
        """Test 6: Comparative Analytics - Compare sensors across dimensions."""
        print("\n" + "=" * 80)
        print("TEST 6: Comparative Analytics (compare_sensors action)")
        print("=" * 80)

        commands = [
            "Compare sensors by industry",
            "Compare sensors by semantic type",
            "Show me sensor comparison by unit",
        ]

        results = []
        for cmd in commands:
            print(f"\nCommand: '{cmd}'")
            result = await self.test_nl_command(cmd, "compare_sensors")
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Result: {status}")
            results.append(result)

        return all(results)

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results."""
        print("\n" + "=" * 80)
        print("🧪 NL AI + WoT BROWSER INTEGRATION TEST SUITE")
        print("=" * 80)
        print(f"Target: {self.base_url}")
        print(f"WebSocket: {self.ws_url}")

        tests = [
            ("WoT Browser Accessible", self.test_wot_browser_accessible),
            ("Thing Description Complete", self.test_thing_description_complete),
            ("Semantic Query", self.test_semantic_query),
            ("Educational Explanations", self.test_educational_explanations),
            ("Sensor Recommendations", self.test_sensor_recommendations),
            ("Comparative Analytics", self.test_comparative_analytics),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"\n❌ TEST FAILED WITH EXCEPTION: {test_name}")
                print(f"   {e}")
                results[test_name] = False

        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in results.values() if r)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 ALL TESTS PASSED! NL AI + WoT integration is working correctly.")
            return {"success": True, "passed": passed, "total": total}
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
            return {"success": False, "passed": passed, "total": total}


async def main():
    """Main entry point."""
    tester = NLAIWoTTester()

    try:
        results = await tester.run_all_tests()
        sys.exit(0 if results["success"] else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
