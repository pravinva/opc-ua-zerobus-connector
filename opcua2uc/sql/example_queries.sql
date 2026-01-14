-- Example queries demonstrating W3C WoT semantic metadata usage
-- These queries show how semantic types enable protocol-agnostic analytics

-- ============================================================================
-- 1. Find all temperature sensors (regardless of protocol)
-- ============================================================================
SELECT
  thing_title,
  endpoint,
  protocol_type,
  topic_or_path,
  value_num,
  unit_uri,
  event_time
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:TemperatureSensor'
  AND DATE(event_time) = CURRENT_DATE()
ORDER BY event_time DESC
LIMIT 100;

-- ============================================================================
-- 2. Find all power sensors above threshold
-- ============================================================================
SELECT
  thing_title,
  topic_or_path,
  value_num as power_kw,
  event_time
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type = 'saref:PowerSensor'
  AND value_num > 100  -- Power above 100 kW
  AND DATE(event_time) = CURRENT_DATE()
ORDER BY value_num DESC;

-- ============================================================================
-- 3. Aggregate statistics by semantic type
-- ============================================================================
SELECT
  semantic_type,
  COUNT(DISTINCT thing_id) as sensor_count,
  COUNT(*) as event_count,
  AVG(value_num) as avg_value,
  MIN(value_num) as min_value,
  MAX(value_num) as max_value,
  COLLECT_SET(unit_uri) as units
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type IS NOT NULL
  AND DATE(event_time) = CURRENT_DATE()
GROUP BY semantic_type
ORDER BY event_count DESC;

-- ============================================================================
-- 4. Protocol-agnostic sensor inventory
-- ============================================================================
SELECT
  thing_id,
  thing_title,
  semantic_type,
  protocol_type,
  endpoint,
  COUNT(*) as recent_events,
  MAX(event_time) as last_seen
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type IS NOT NULL
  AND event_time >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
GROUP BY thing_id, thing_title, semantic_type, protocol_type, endpoint
ORDER BY semantic_type, thing_title;

-- ============================================================================
-- 5. Find sensors with specific units (e.g., all temperatures in Celsius)
-- ============================================================================
SELECT
  thing_title,
  topic_or_path,
  value_num,
  unit_uri,
  event_time
FROM manufacturing.iot_data.events_bronze_wot
WHERE unit_uri = 'http://qudt.org/vocab/unit/DEG_C'
  AND DATE(event_time) = CURRENT_DATE()
ORDER BY event_time DESC
LIMIT 100;

-- ============================================================================
-- 6. Cross-protocol correlation (temperature vs power)
-- ============================================================================
WITH temperature_data AS (
  SELECT
    DATE_TRUNC('minute', event_time) as time_bucket,
    AVG(value_num) as avg_temp
  FROM manufacturing.iot_data.events_bronze_wot
  WHERE semantic_type = 'saref:TemperatureSensor'
    AND DATE(event_time) = CURRENT_DATE()
  GROUP BY time_bucket
),
power_data AS (
  SELECT
    DATE_TRUNC('minute', event_time) as time_bucket,
    AVG(value_num) as avg_power
  FROM manufacturing.iot_data.events_bronze_wot
  WHERE semantic_type = 'saref:PowerSensor'
    AND DATE(event_time) = CURRENT_DATE()
  GROUP BY time_bucket
)
SELECT
  t.time_bucket,
  t.avg_temp,
  p.avg_power
FROM temperature_data t
INNER JOIN power_data p ON t.time_bucket = p.time_bucket
ORDER BY t.time_bucket;

-- ============================================================================
-- 7. Detect missing semantic metadata (data quality check)
-- ============================================================================
SELECT
  source_name,
  protocol_type,
  COUNT(*) as events_without_semantic_metadata
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type IS NULL
  AND DATE(event_time) = CURRENT_DATE()
GROUP BY source_name, protocol_type
ORDER BY events_without_semantic_metadata DESC;

-- ============================================================================
-- 8. Time-series analysis by semantic type (hourly aggregation)
-- ============================================================================
SELECT
  semantic_type,
  DATE_TRUNC('hour', event_time) as hour,
  COUNT(*) as event_count,
  AVG(value_num) as avg_value,
  STDDEV(value_num) as stddev_value,
  MIN(value_num) as min_value,
  MAX(value_num) as max_value
FROM manufacturing.iot_data.events_bronze_wot
WHERE semantic_type IS NOT NULL
  AND DATE(event_time) = CURRENT_DATE()
GROUP BY semantic_type, hour
ORDER BY semantic_type, hour;
