-- Unity Catalog table schema with W3C WoT semantic metadata support
-- This table extends the standard IoT events schema with semantic fields
-- that enable protocol-agnostic queries and analytics.

CREATE TABLE IF NOT EXISTS manufacturing.iot_data.events_bronze_wot (
  -- Existing fields (standard IoT event data)
  event_time TIMESTAMP COMMENT 'Event timestamp from device (microseconds precision)',
  ingest_time TIMESTAMP COMMENT 'Ingestion timestamp when record arrived',
  source_name STRING COMMENT 'Source identifier/name',
  endpoint STRING COMMENT 'Connection endpoint (e.g., opc.tcp://host:port)',
  protocol_type STRING COMMENT 'Protocol type: opcua, mqtt, or modbus',
  topic_or_path STRING COMMENT 'Protocol-specific identifier (OPC-UA path, MQTT topic, Modbus address)',
  value STRING COMMENT 'Value as string (always present)',
  value_type STRING COMMENT 'Data type (Int32, Float, Boolean, String, etc.)',
  value_num DOUBLE COMMENT 'Numeric value (if applicable, null otherwise)',
  metadata MAP<STRING, STRING> COMMENT 'Protocol-specific metadata as key-value pairs',
  status_code INT COMMENT 'Quality/status code (0 = Good)',
  status STRING COMMENT 'Status description (Good, Bad, Uncertain, etc.)',

  -- NEW: W3C WoT semantic metadata fields
  thing_id STRING COMMENT 'W3C WoT Thing identifier (e.g., urn:dev:ops:databricks-ot-simulator)',
  thing_title STRING COMMENT 'Human-readable Thing name from Thing Description',
  semantic_type STRING COMMENT 'Semantic type from ontology (e.g., saref:TemperatureSensor, saref:PowerSensor)',
  unit_uri STRING COMMENT 'QUDT unit URI (e.g., http://qudt.org/vocab/unit/DEG_C, http://qudt.org/vocab/unit/KiloW)'
)
USING DELTA
PARTITIONED BY (DATE(event_time), protocol_type)
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.columnMapping.mode' = 'name',
  'description' = 'IoT sensor events with W3C Web of Things semantic metadata'
)
COMMENT 'IoT sensor data from OPC-UA, MQTT, and Modbus sources with W3C WoT semantic annotations for protocol-agnostic analytics';
