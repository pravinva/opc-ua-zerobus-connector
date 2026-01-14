-- Create convenience views for W3C WoT semantic queries
-- These views provide quick access to common semantic query patterns

-- ============================================================================
-- View: Sensors grouped by semantic type
-- ============================================================================
CREATE OR REPLACE VIEW manufacturing.iot_data.sensors_by_semantic_type AS
SELECT
  semantic_type,
  COUNT(DISTINCT thing_id) as sensor_count,
  COUNT(*) as total_events,
  COLLECT_SET(thing_title) as sensor_names,
  COLLECT_SET(protocol_type) as protocols_used,
  COLLECT_SET(unit_uri) as units_used,
  MIN(event_time) as first_event,
  MAX(event_time) as last_event
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type IS NOT NULL
GROUP BY semantic_type;

-- Query example:
-- SELECT * FROM manufacturing.iot_data.sensors_by_semantic_type
-- ORDER BY total_events DESC;

-- ============================================================================
-- View: Latest value for each sensor
-- ============================================================================
CREATE OR REPLACE VIEW manufacturing.iot_data.latest_sensor_values AS
WITH ranked_events AS (
  SELECT
    thing_id,
    thing_title,
    semantic_type,
    protocol_type,
    topic_or_path,
    value_num,
    unit_uri,
    event_time,
    status,
    ROW_NUMBER() OVER (PARTITION BY thing_id, topic_or_path ORDER BY event_time DESC) as rn
  FROM manufacturing.iot_data.events_bronze_wot
  WHERE thing_id IS NOT NULL
)
SELECT
  thing_id,
  thing_title,
  semantic_type,
  protocol_type,
  topic_or_path,
  value_num,
  unit_uri,
  event_time as last_update,
  status
FROM ranked_events
WHERE rn = 1;

-- Query example:
-- SELECT * FROM manufacturing.iot_data.latest_sensor_values
-- WHERE semantic_type = 'saref:TemperatureSensor'
-- ORDER BY value_num DESC;

-- ============================================================================
-- View: Temperature sensors only
-- ============================================================================
CREATE OR REPLACE VIEW manufacturing.iot_data.temperature_sensors AS
SELECT
  thing_id,
  thing_title,
  protocol_type,
  endpoint,
  topic_or_path,
  value_num as temperature,
  unit_uri,
  event_time,
  status
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:TemperatureSensor';

-- ============================================================================
-- View: Power sensors only
-- ============================================================================
CREATE OR REPLACE VIEW manufacturing.iot_data.power_sensors AS
SELECT
  thing_id,
  thing_title,
  protocol_type,
  endpoint,
  topic_or_path,
  value_num as power,
  unit_uri,
  event_time,
  status
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:PowerSensor';

-- ============================================================================
-- View: Sensor health dashboard
-- ============================================================================
CREATE OR REPLACE VIEW manufacturing.iot_data.sensor_health_dashboard AS
SELECT
  thing_id,
  thing_title,
  semantic_type,
  protocol_type,
  COUNT(*) as event_count_last_hour,
  COUNT(DISTINCT DATE_TRUNC('minute', event_time)) as active_minutes,
  AVG(value_num) as avg_value,
  STDDEV(value_num) as stddev_value,
  MIN(event_time) as first_event,
  MAX(event_time) as last_event,
  SUM(CASE WHEN status != 'Good' THEN 1 ELSE 0 END) as bad_status_count
FROM manufacturing.iot_data.events_bronze_wot
WHERE thing_id IS NOT NULL
  AND event_time >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
GROUP BY thing_id, thing_title, semantic_type, protocol_type;

-- Query example:
-- SELECT * FROM manufacturing.iot_data.sensor_health_dashboard
-- WHERE bad_status_count > 0 OR event_count_last_hour < 10
-- ORDER BY bad_status_count DESC, event_count_last_hour ASC;
