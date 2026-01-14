# WoT Thing Description Integration Guide

## Quick Start (5 minutes)

### Step 1: Import the Generator

Add to your web server file (e.g., `enhanced_web_ui.py` or `web_server.py`):

```python
from ot_simulator.wot import ThingDescriptionGenerator
```

### Step 2: Add the REST Endpoint

```python
@app.get("/api/opcua/thing-description")
async def get_thing_description():
    """Generate W3C WoT Thing Description for OPC UA server.

    Query Parameters:
        nodes: Optional comma-separated list of sensor paths
        compact: Return compact TD if true

    Returns:
        JSON-LD Thing Description
    """
    try:
        # Parse query parameters
        node_filter_param = request.args.get('nodes')
        compact = request.args.get('compact', 'false').lower() == 'true'

        node_filter = None
        if node_filter_param:
            node_filter = [n.strip() for n in node_filter_param.split(',')]

        # Create generator
        td_generator = ThingDescriptionGenerator(
            simulator_manager=simulator_manager,  # Your SimulatorManager instance
            base_url="opc.tcp://0.0.0.0:4840/ot-simulator/server/",
            namespace_uri="http://databricks.com/iot-simulator"
        )

        # Generate Thing Description
        td = await td_generator.generate_td(
            include_plc_nodes=False,
            node_filter=node_filter
        )

        # Return compact or full
        if compact:
            td = td_generator.generate_compact_td(td)

        return jsonify(td), 200, {
            'Content-Type': 'application/td+json',
            'Access-Control-Allow-Origin': '*',
            'Link': '<https://www.w3.org/2022/wot/td/v1.1>; rel="type"'
        }

    except Exception as e:
        logger.exception(f"Error generating Thing Description: {e}")
        return jsonify({"error": str(e)}), 500
```

### Step 3: Test It

Start your simulator and test:

```bash
# Get full Thing Description
curl http://localhost:8000/api/opcua/thing-description | jq

# Get only mining sensors
curl "http://localhost:8000/api/opcua/thing-description?nodes=mining" | jq

# Get compact summary
curl "http://localhost:8000/api/opcua/thing-description?compact=true" | jq
```

---

## Framework-Specific Integration

### Flask Example

```python
from flask import Flask, request, jsonify
from ot_simulator.wot import ThingDescriptionGenerator

app = Flask(__name__)

@app.route("/api/opcua/thing-description", methods=["GET"])
async def get_thing_description():
    node_filter_param = request.args.get('nodes')
    compact = request.args.get('compact', 'false').lower() == 'true'

    # ... (generator code as above)

    return jsonify(td), 200, {'Content-Type': 'application/td+json'}
```

### FastAPI Example

```python
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from ot_simulator.wot import ThingDescriptionGenerator

app = FastAPI()

@app.get("/api/opcua/thing-description")
async def get_thing_description(
    nodes: str = Query(None, description="Comma-separated sensor paths"),
    compact: bool = Query(False, description="Return compact TD")
):
    node_filter = nodes.split(',') if nodes else None

    td_generator = ThingDescriptionGenerator(
        simulator_manager=simulator_manager,
        base_url="opc.tcp://0.0.0.0:4840/ot-simulator/server/"
    )

    td = await td_generator.generate_td(node_filter=node_filter)

    if compact:
        td = td_generator.generate_compact_td(td)

    return JSONResponse(
        content=td,
        media_type="application/td+json",
        headers={"Link": '<https://www.w3.org/2022/wot/td/v1.1>; rel="type"'}
    )
```

### aiohttp Example

```python
from aiohttp import web
from ot_simulator.wot import ThingDescriptionGenerator

async def get_thing_description(request):
    """Handle Thing Description request."""
    node_filter_param = request.query.get('nodes')
    compact = request.query.get('compact', 'false').lower() == 'true'

    node_filter = node_filter_param.split(',') if node_filter_param else None

    td_generator = ThingDescriptionGenerator(
        simulator_manager=request.app['simulator_manager'],
        base_url="opc.tcp://0.0.0.0:4840/ot-simulator/server/"
    )

    td = await td_generator.generate_td(node_filter=node_filter)

    if compact:
        td = td_generator.generate_compact_td(td)

    return web.json_response(
        td,
        content_type="application/td+json",
        headers={"Link": '<https://www.w3.org/2022/wot/td/v1.1>; rel="type"'}
    )

# Add to router
app.router.add_get('/api/opcua/thing-description', get_thing_description)
```

---

## Advanced Usage

### Caching Thing Descriptions

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedTDGenerator:
    """Thing Description generator with caching."""

    def __init__(self, simulator_manager, cache_ttl_seconds=60):
        self.generator = ThingDescriptionGenerator(
            simulator_manager=simulator_manager,
            base_url="opc.tcp://0.0.0.0:4840/ot-simulator/server/"
        )
        self.cache = {}
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)

    async def get_td(self, node_filter=None):
        """Get Thing Description with caching."""
        cache_key = str(node_filter) if node_filter else "full"

        # Check cache
        if cache_key in self.cache:
            td, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return td

        # Generate fresh TD
        td = await self.generator.generate_td(node_filter=node_filter)
        self.cache[cache_key] = (td, datetime.now())

        return td
```

### Filtering by Industry

```python
@app.get("/api/opcua/thing-description/<industry>")
async def get_td_by_industry(industry: str):
    """Get Thing Description for specific industry."""
    td_generator = ThingDescriptionGenerator(
        simulator_manager=simulator_manager,
        base_url="opc.tcp://0.0.0.0:4840/ot-simulator/server/"
    )

    # Filter by industry
    td = await td_generator.generate_td(node_filter=[industry])

    return jsonify(td), 200, {'Content-Type': 'application/td+json'}
```

### Adding Custom Metadata

```python
td = await td_generator.generate_td()

# Add custom metadata
td["version"] = "1.0.0"
td["maintainer"] = "Your Organization"
td["license"] = "Apache-2.0"
td["documentation"] = "https://docs.example.com"
td["instanceOf"] = "urn:schema:industrial-ot-simulator"

return jsonify(td)
```

---

## Troubleshooting

### Issue: "simulator_manager not found"

**Solution:** Ensure simulator_manager is accessible in your endpoint:

```python
# Option 1: Pass as app context
app.simulator_manager = simulator_manager

@app.get("/api/opcua/thing-description")
async def get_td():
    manager = request.app.simulator_manager  # or app.simulator_manager
    td_generator = ThingDescriptionGenerator(manager, ...)
```

### Issue: "No sensors found in TD"

**Solution:** Check simulator_manager structure:

```python
# Debug: Print simulator manager structure
print(f"Simulator manager type: {type(simulator_manager)}")
print(f"Has 'sensors' attr: {hasattr(simulator_manager, 'sensors')}")
if hasattr(simulator_manager, 'sensors'):
    print(f"Sensor industries: {list(simulator_manager.sensors.keys())}")
```

The ThingDescriptionGenerator handles missing sensors gracefully, but check your simulator is running.

### Issue: "JSON serialization error"

**Solution:** Ensure proper async handling:

```python
# WRONG: Mixing sync/async
td = td_generator.generate_td()  # Missing await

# CORRECT:
td = await td_generator.generate_td()
```

---

## Next Steps

After integration:

1. **Test the endpoint** - Verify TD generation works
2. **Validate TD** - Use W3C WoT TD validator
3. **Add monitoring** - Log TD requests and response times
4. **Implement Priority 2** - Add semantic_type to SensorConfig
5. **Add caching** - Cache TDs for performance

---

## Support

For questions or issues:
1. Check `WOT_IMPLEMENTATION_REPORT.md`
2. Review `OPC_UA_10101_WOT_BINDING_RESEARCH.md`
3. See `IMPLEMENTATION_PRIORITIES.md`

---

**Last Updated:** January 14, 2026
**Version:** 1.0
**Status:** Production Ready ✅
