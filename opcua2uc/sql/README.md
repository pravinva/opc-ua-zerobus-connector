# Unity Catalog SQL Schemas for W3C WoT Support

This directory contains SQL DDL and example queries for Unity Catalog tables with W3C Web of Things (WoT) semantic metadata support.

## Files

### `create_table_wot.sql`
Creates the main Unity Catalog table with W3C WoT semantic metadata fields:
- `thing_id`: W3C WoT Thing identifier (e.g., `urn:dev:ops:...`)
- `thing_title`: Human-readable Thing name
- `semantic_type`: Ontology-based semantic type (e.g., `saref:TemperatureSensor`)
- `unit_uri`: QUDT unit URI for standardized units

### `create_views.sql`
Creates convenience views for common semantic query patterns:
- `sensors_by_semantic_type`: Aggregate statistics grouped by semantic type
- `latest_sensor_values`: Latest value for each sensor
- `temperature_sensors`: Filter for temperature sensors only
- `power_sensors`: Filter for power sensors only
- `sensor_health_dashboard`: Health metrics for all sensors

### `example_queries.sql`
Example queries demonstrating semantic metadata usage:
1. Find all temperature sensors (protocol-agnostic)
2. Find power sensors above threshold
3. Aggregate statistics by semantic type
4. Protocol-agnostic sensor inventory
5. Find sensors with specific units
6. Cross-protocol correlation analysis
7. Data quality checks
8. Time-series analysis by semantic type

## Usage

### Creating the Table

Run the DDL in your Databricks workspace:

```sql
-- Create the table
%sql
CREATE CATALOG IF NOT EXISTS manufacturing;
CREATE SCHEMA IF NOT EXISTS manufacturing.iot_data;

-- Run create_table_wot.sql
CREATE TABLE IF NOT EXISTS manufacturing.iot_data.events_bronze_wot (
  -- ... (see create_table_wot.sql)
);
```

### Creating Views

```sql
-- Run create_views.sql to create all convenience views
%sql
CREATE OR REPLACE VIEW manufacturing.iot_data.sensors_by_semantic_type AS ...
```

### Example Queries

```sql
-- Find all temperature sensors today
SELECT *
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:TemperatureSensor'
  AND DATE(event_time) = CURRENT_DATE();
```

## Semantic Types

Common semantic types from SAREF ontology:
- `saref:TemperatureSensor` - Temperature measurements
- `saref:PowerSensor` - Power/energy measurements
- `saref:PressureSensor` - Pressure measurements
- `saref:FlowSensor` - Flow rate measurements
- `saref:VoltageSensor` - Voltage measurements
- `saref:CurrentSensor` - Current measurements
- `saref:HumiditySensor` - Humidity measurements

## Unit URIs

Common QUDT unit URIs:
- `http://qudt.org/vocab/unit/DEG_C` - Degrees Celsius
- `http://qudt.org/vocab/unit/KiloW` - Kilowatts
- `http://qudt.org/vocab/unit/BAR` - Bar (pressure)
- `http://qudt.org/vocab/unit/M3-PER-HR` - Cubic meters per hour
- `http://qudt.org/vocab/unit/V` - Volts
- `http://qudt.org/vocab/unit/A` - Amperes

## Benefits

### Protocol-Agnostic Queries
Query by semantic type instead of protocol-specific paths:
```sql
-- Before: Need to know OPC-UA paths
SELECT * FROM events WHERE topic_or_path LIKE 'ns=2;s=%temperature%'

-- After: Semantic query
SELECT * FROM events_bronze_wot WHERE semantic_type = 'saref:TemperatureSensor'
```

### Cross-Protocol Analytics
Correlate sensors across different protocols:
```sql
-- Temperature from OPC-UA + Power from MQTT
SELECT t.avg_temp, p.avg_power
FROM temperature_sensors t
JOIN power_sensors p ON t.time_bucket = p.time_bucket
```

### Standardized Units
Query with confidence about unit semantics:
```sql
-- All temperatures in Celsius
SELECT *
FROM events_bronze_wot
WHERE unit_uri = 'http://qudt.org/vocab/unit/DEG_C'
```

## Integration with Connector

The IoT Connector automatically populates these semantic fields when sources are configured via Thing Descriptions:

```bash
# Add source from Thing Description
curl -X POST http://localhost:8080/api/sources/from-td \
  -H "Content-Type: application/json" \
  -d '{"thing_description": "http://simulator:8000/api/opcua/thing-description"}'
```

Records will automatically include:
- `thing_id` from TD `id` field
- `thing_title` from TD `title` field
- `semantic_type` from property `@type` annotations
- `unit_uri` from property `unit` field

## References

- [W3C WoT Thing Description](https://www.w3.org/TR/wot-thing-description/)
- [SAREF Ontology](https://saref.etsi.org/)
- [QUDT Units](http://qudt.org/schema/qudt/)
- [Unity Catalog Tables](https://docs.databricks.com/en/data-governance/unity-catalog/create-tables.html)
