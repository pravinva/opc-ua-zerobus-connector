# ZeroBus Networking from Databricks Apps

## The Question

How does ZeroBus networking work when the connector runs inside a Databricks Apps container?

## Short Answer

**ZeroBus works perfectly from Databricks Apps** because:
1. ✅ Apps have **outbound HTTPS** access (port 443)
2. ✅ ZeroBus uses **HTTPS REST API** (not special ports)
3. ✅ OAuth2 authentication works from any internet-connected host
4. ✅ No firewall rules needed

## Detailed Explanation

### ZeroBus Architecture

```
┌──────────────────────────────────────────────────────────┐
│          Databricks Apps Container (Serverless)          │
│                                                           │
│  ┌────────────────────────────────────────────────┐     │
│  │           IoT Connector Process                │     │
│  │                                                 │     │
│  │  ┌──────────────────────────────────────────┐  │     │
│  │  │  Protocol Clients (collect data)        │  │     │
│  │  │  • OPC-UA: localhost:4840                │  │     │
│  │  │  • MQTT: cloud broker                    │  │     │
│  │  │  • Modbus: localhost:5020                │  │     │
│  │  └─────────────────┬────────────────────────┘  │     │
│  │                    │                            │     │
│  │  ┌─────────────────▼────────────────────────┐  │     │
│  │  │  ZeroBus SDK (Python)                    │  │     │
│  │  │  - Serializes data to Protobuf           │  │     │
│  │  │  - Batches messages                      │  │     │
│  │  │  - Handles retries                       │  │     │
│  │  └─────────────────┬────────────────────────┘  │     │
│  │                    │                            │     │
│  │  ┌─────────────────▼────────────────────────┐  │     │
│  │  │  HTTPS Client                            │  │     │
│  │  │  - OAuth2 M2M authentication             │  │     │
│  │  │  - TLS 1.2/1.3 encryption                │  │     │
│  │  └─────────────────┬────────────────────────┘  │     │
│  └────────────────────┼──────────────────────────┘     │
│                       │                                 │
└───────────────────────┼─────────────────────────────────┘
                        │
                        │ HTTPS (Port 443)
                        │ Outbound - No firewall needed
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Databricks Control Plane           │
        │    (e2-demo-field-eng.cloud...)       │
        │                                        │
        │  1. OAuth2 Token Exchange              │
        │     POST /oidc/v1/token                │
        │     → Returns access_token             │
        └───────────────────┬────────────────────┘
                            │
                            │ HTTPS (Port 443)
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │    ZeroBus Ingestion Service          │
        │    (xxxx.zerobus.us-west-2...)        │
        │                                        │
        │  2. Data Ingestion                     │
        │     POST /ingest                       │
        │     Headers:                           │
        │       Authorization: Bearer <token>    │
        │     Body: Protobuf bytes               │
        └───────────────────┬────────────────────┘
                            │
                            │ Internal Databricks Network
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │    Unity Catalog Delta Tables         │
        │    main.scada_data.iot_events_bronze  │
        │                                        │
        │  • Automatic schema validation         │
        │  • Transactional writes                │
        │  • Exactly-once semantics              │
        └────────────────────────────────────────┘
```

## Key Points

### 1. ZeroBus Uses Standard HTTPS

**Not a special protocol:**
- Port: **443** (standard HTTPS)
- Protocol: **HTTP/2 over TLS**
- No custom ports or protocols

**Connector code:**
```python
from databricks.sdk import WorkspaceClient
from databricks_zerobus_ingest_sdk import ZeroBusClient

# OAuth2 authentication
client = WorkspaceClient(
    host="https://e2-demo-field-eng.cloud.databricks.com",
    client_id=os.environ["DATABRICKS_CLIENT_ID"],
    client_secret=os.environ["DATABRICKS_CLIENT_SECRET"]
)

# ZeroBus client - just another HTTPS endpoint
zerobus = ZeroBusClient(
    endpoint="https://1444828305810485.zerobus.us-west-2.cloud.databricks.com",
    workspace_client=client
)

# Write data - standard HTTPS POST request
zerobus.write(table="main.scada.bronze", data=protobuf_bytes)
```

### 2. OAuth2 M2M Flow

**Two-step authentication:**

**Step 1: Get Access Token**
```http
POST https://e2-demo-field-eng.cloud.databricks.com/oidc/v1/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=52393ed8-xxxx-xxxx-xxxx-xxxxxxxxxxxx
&client_secret=<secret>
&scope=all-apis

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Step 2: Use Token for ZeroBus**
```http
POST https://1444828305810485.zerobus.us-west-2.cloud.databricks.com/ingest
Authorization: Bearer eyJhbGc...
Content-Type: application/octet-stream

<protobuf bytes>
```

### 3. Databricks Apps Networking

**What Databricks Apps allows:**

✅ **Outbound HTTPS** (port 443)
- To any internet destination
- No firewall configuration needed
- TLS encryption automatic

✅ **Inbound HTTP** (your app's port)
- Only to your web UI (port 8989)
- Databricks manages the ingress
- Automatic TLS termination

❌ **No direct inbound to internal ports**
- OPC-UA (4840), MQTT (1883), Modbus (5020) are localhost-only
- Only accessible within the container
- This is perfect for our use case!

### 4. Why This Architecture Works

**Simulator servers are localhost:**
```yaml
# In container:
OPC-UA Server:  opc.tcp://127.0.0.1:4840  # Localhost only
MQTT Publisher: → Cloud HiveMQ             # Internet accessible
Modbus Server:  modbus://127.0.0.1:5020   # Localhost only
```

**Connector clients connect locally:**
```yaml
# Connector config:
sources:
  - name: simulator_opcua
    endpoint: opc.tcp://localhost:4840    # Same container

  - name: simulator_mqtt
    endpoint: mqtt://cloud.hivemq.com:8883  # Internet

  - name: simulator_modbus
    endpoint: modbus://localhost:5020      # Same container
```

**ZeroBus writes go outbound:**
```yaml
# ZeroBus config:
zerobus:
  workspace_host: https://e2-demo-field-eng.cloud.databricks.com  # Internet
  zerobus_endpoint: https://xxxx.zerobus.us-west-2.cloud...       # Internet
```

## Network Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Databricks Apps Container                       │
│              (No inbound access needed)                      │
│                                                              │
│  Simulator ──→ Connector (local sockets: 4840, 5020)        │
│      │              │                                        │
│      │              ├──→ ZeroBus SDK                        │
│      │              │         │                             │
│      └──────────────┼─────────┘                             │
│                     │                                        │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      │ Outbound HTTPS (Port 443)
                      │ ✅ Always allowed
                      │
         ┌────────────▼─────────────┐
         │   Internet               │
         │                          │
         │  • Databricks Workspace  │
         │  • ZeroBus Endpoint      │
         │  • HiveMQ Cloud MQTT     │
         └──────────────────────────┘
```

## Security Considerations

### Authentication
- **OAuth2 M2M**: Industry standard, token-based
- **Service Principal**: Scoped permissions to specific catalog/schema
- **Token Refresh**: Automatic, handles expiration

### Encryption
- **TLS 1.2/1.3**: All traffic encrypted in transit
- **Certificate Validation**: Databricks certificates validated
- **No Credentials in Code**: Environment variables or secrets

### Authorization
```sql
-- Grant write permission to service principal
GRANT INSERT ON TABLE main.scada_data.iot_events_bronze
TO SERVICE_PRINCIPAL '<client-id>';

-- ZeroBus validates permissions on every write
```

## Configuration Example

**Complete working config for Databricks Apps:**

```yaml
# connector_config.yaml
sources:
  # Localhost connections (within container)
  - name: simulator_opcua
    endpoint: opc.tcp://localhost:4840
    protocol: opcua
    enabled: true

  - name: simulator_modbus
    endpoint: modbus://localhost:5020
    protocol: modbus
    enabled: true

  # Cloud MQTT broker (internet)
  - name: simulator_mqtt
    endpoint: mqtt://abc123.s1.eu.hivemq.cloud:8883
    protocol: mqtt
    use_tls: true
    username: ${MQTT_USERNAME}
    password: ${MQTT_PASSWORD}
    enabled: true

# ZeroBus connection (internet - outbound HTTPS only)
zerobus:
  # OAuth2 endpoint
  workspace_host: https://e2-demo-field-eng.cloud.databricks.com

  # ZeroBus ingestion endpoint
  zerobus_endpoint: https://1444828305810485.zerobus.us-west-2.cloud.databricks.com

  # Service Principal credentials (from secrets)
  auth:
    client_id: ${DATABRICKS_CLIENT_ID}
    client_secret: ${DATABRICKS_CLIENT_SECRET}

  # Unity Catalog destination
  target:
    catalog: main
    schema: scada_data
    table: iot_events_bronze

# Backpressure (local disk in container)
backpressure:
  max_queue_size: 10000
  spool_enabled: true
  spool_path: /tmp/spool  # Container filesystem
```

## Common Questions

### Q: Do I need to configure firewall rules?
**A:** No! Databricks Apps containers have outbound HTTPS access by default. No firewall configuration needed.

### Q: Will ZeroBus work from Databricks Apps?
**A:** Yes, perfectly! ZeroBus is designed for this. It uses standard HTTPS (port 443) which is always allowed outbound.

### Q: What about the protocol servers (OPC-UA, MQTT, Modbus)?
**A:** They run on localhost within the container. The connector connects locally. No external access needed or wanted.

### Q: Do I need a VPN?
**A:** No! Everything works over public internet with:
- OAuth2 authentication
- TLS encryption
- Databricks manages the security

### Q: What if my workspace is on a private network?
**A:** You'll need:
- VPN or Private Link configured for Databricks Apps
- Or deploy the connector in your DMZ instead

### Q: Can I test ZeroBus writes before deploying?
**A:** Yes! Run the e2e test we created:
```bash
cd databricks_iot_connector
python test_zerobus_e2e.py --write --protocol all
```

## Performance Considerations

### Latency
- **OAuth token fetch**: ~200ms (cached for 1 hour)
- **ZeroBus write**: ~50-100ms per batch
- **Total overhead**: Minimal, batching amortizes cost

### Throughput
- **ZeroBus limit**: 1000 messages/second per stream
- **Batch size**: Configure for your needs (default: 100 messages)
- **Concurrent writes**: Multiple streams supported

### Cost
- **Data transfer**: Standard Databricks egress rates
- **Compute**: Apps serverless (~$0.10-0.20/hour)
- **Storage**: Unity Catalog standard rates

## Summary

**ZeroBus networking "just works" from Databricks Apps because:**

1. ✅ Uses standard HTTPS (port 443) - always allowed outbound
2. ✅ OAuth2 authentication - no special credentials needed
3. ✅ Databricks SDK handles all the complexity
4. ✅ No firewall rules or network configuration required
5. ✅ Works from any internet-connected environment

**The connector running in Databricks Apps:**
- Reads from local simulator servers (localhost)
- Reads from cloud MQTT broker (internet)
- Writes to ZeroBus (internet, HTTPS)
- Serves web UI (Databricks Apps handles ingress)

**No networking configuration needed on your part!**
