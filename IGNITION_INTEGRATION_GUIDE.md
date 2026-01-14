# Ignition Integration Guide - OPC UA Simulator Access

**Date**: January 15, 2026
**Purpose**: Connect Ignition (running on your laptop) to the OT Data Simulator OPC UA endpoint

---

## Overview

The OT Data Simulator exposes an OPC UA endpoint at `opc.tcp://0.0.0.0:4840/ot-simulator/server/` with 379 sensors across 16 industries. This guide explains how to make it accessible to Ignition running on your laptop.

---

## Quick Start - Local Network (Easiest) ✅

### Prerequisites
- Simulator running on your machine or local network
- Ignition installed on your laptop
- Both on same network (WiFi/Ethernet)

### Steps

1. **Find Your Simulator's IP Address**:
   ```bash
   # On Mac/Linux
   ifconfig | grep "inet "

   # On Windows
   ipconfig
   ```

   Look for IP like: `192.168.1.100` (your local network IP)

2. **Configure Ignition OPC UA Connection**:
   - Open Ignition Gateway (http://localhost:8088)
   - Go to: **Config → OPC UA → Connections**
   - Click **Create new OPC UA Connection**

   **Settings**:
   ```
   Name: OT Data Simulator
   Endpoint URL: opc.tcp://192.168.1.100:4840/ot-simulator/server/
   Security Policy: None (for testing)
   ```

3. **Test Connection**:
   - Click **Save**
   - Status should show **Connected**
   - Browse tags: You should see 379 sensors organized by industry

4. **Browse Available Tags** in Ignition Designer:
   ```
   OT Data Simulator/
   ├── mining/
   │   ├── crusher_1_temperature (°C)
   │   ├── crusher_1_vibration_x (g)
   │   ├── crusher_1_vibration_y (g)
   │   └── ...
   ├── utilities/
   │   ├── gas_turbine_1_temperature (°C)
   │   ├── gas_turbine_1_pressure (bar)
   │   └── ...
   └── ... (14 more industries)
   ```

---

## Production Deployment - Internet Access 🌐

### Option 1: AWS EC2 / Azure VM (Recommended)

**Architecture**:
```
Ignition (Laptop) → Internet → Cloud VM (Public IP) → OPC UA Simulator
                                                    → Web UI
```

#### Step 1: Deploy to Cloud VM

**AWS EC2 Example**:

1. **Launch EC2 Instance**:
   - Instance type: `t3.medium` (2 vCPU, 4 GB RAM)
   - OS: Ubuntu 22.04 LTS
   - Security Group: Open ports 4840 (OPC UA) and 8989 (Web UI)

2. **Security Group Rules**:
   ```
   Type        Protocol  Port   Source          Description
   Custom TCP  TCP       4840   0.0.0.0/0      OPC UA Server
   Custom TCP  TCP       8989   0.0.0.0/0      Web UI
   SSH         TCP       22     Your-IP/32     SSH Access
   ```

3. **Install Simulator on VM**:
   ```bash
   # SSH into VM
   ssh -i your-key.pem ubuntu@<ec2-public-ip>

   # Install dependencies
   sudo apt update
   sudo apt install -y python3-pip git

   # Clone repository
   git clone https://github.com/pravinva/opc-ua-zerobus-connector.git
   cd opc-ua-zerobus-connector
   git checkout feature/ot-sim-on-databricks-apps

   # Install Python dependencies
   pip3 install -r requirements.txt

   # Run simulator
   python3 -m ot_simulator --web-ui --config ot_simulator/config.yaml
   ```

4. **Keep Simulator Running (use systemd or screen)**:
   ```bash
   # Option A: Use screen (quick)
   screen -S simulator
   python3 -m ot_simulator --web-ui --config ot_simulator/config.yaml
   # Press Ctrl+A then D to detach

   # Option B: Use systemd (production)
   sudo nano /etc/systemd/system/ot-simulator.service
   ```

   **systemd service file**:
   ```ini
   [Unit]
   Description=OT Data Simulator
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/opc-ua-zerobus-connector
   ExecStart=/usr/bin/python3 -m ot_simulator --web-ui --config ot_simulator/config.yaml
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl enable ot-simulator
   sudo systemctl start ot-simulator
   sudo systemctl status ot-simulator
   ```

5. **Connect Ignition**:
   ```
   Endpoint URL: opc.tcp://<ec2-public-ip>:4840/ot-simulator/server/

   Example: opc.tcp://54.123.45.67:4840/ot-simulator/server/
   ```

#### Step 2: Enable Security (Production)

For production, enable OPC UA security:

1. **Update config.yaml** (uncomment security section):
   ```yaml
   opcua:
     endpoint: "opc.tcp://0.0.0.0:4840/ot-simulator/server/"
     security:
       enabled: true
       security_policy: "Basic256Sha256"
       security_mode: "SignAndEncrypt"
       server_cert_path: "ot_simulator/certs/server_cert.pem"
       server_key_path: "ot_simulator/certs/server_key.pem"
       trusted_certs_dir: "ot_simulator/certs/trusted"
       enable_user_auth: true
       users:
         admin: "change-this-password"
         ignition: "ignition-password"
   ```

2. **Generate Certificates** (if not already created):
   ```bash
   cd ot_simulator/certs

   # Generate server certificate (self-signed for testing)
   openssl req -x509 -newkey rsa:2048 -keyout server_key.pem \
     -out server_cert.pem -days 365 -nodes \
     -subj "/CN=ot-simulator/O=Databricks/C=US"

   # Create trusted certs directory
   mkdir -p trusted
   ```

3. **Configure Ignition with Security**:
   - Security Policy: **Basic256Sha256**
   - Message Mode: **SignAndEncrypt**
   - Username: `ignition`
   - Password: `ignition-password`
   - Trust server certificate when prompted

---

### Option 2: Databricks Apps + Separate OPC UA Server

**Problem**: Databricks Apps doesn't expose arbitrary TCP ports (only HTTP/HTTPS)

**Solution**: Split deployment
- **Databricks Apps**: Web UI only (port 8000)
- **Separate VM**: OPC UA server (port 4840)

**Architecture**:
```
Ignition → Cloud VM:4840 (OPC UA)
Users   → Databricks Apps:8000 (Web UI)
```

**Steps**:

1. **Deploy OPC UA to VM** (as shown in Option 1)

2. **Deploy Web UI to Databricks Apps**:
   ```bash
   # Modify config to disable OPC UA on Databricks Apps
   # Use app.yaml with only web UI
   databricks apps deploy ot-simulator
   ```

3. **Connect Both**:
   - Ignition points to: `opc.tcp://<vm-ip>:4840/ot-simulator/server/`
   - Web monitoring at: `https://<databricks-app>.databricks.com`

---

### Option 3: Ngrok Tunnel (Development Only)

**Use Case**: Quick testing without cloud VM

**Steps**:

1. **Install ngrok**:
   ```bash
   # Mac
   brew install ngrok

   # Or download from https://ngrok.com/download
   ```

2. **Create Account & Get Auth Token** (free tier):
   ```bash
   ngrok config add-authtoken <your-token>
   ```

3. **Start Simulator Locally**:
   ```bash
   python3 -m ot_simulator --web-ui --config ot_simulator/config.yaml
   ```

4. **Expose OPC UA Port**:
   ```bash
   ngrok tcp 4840
   ```

   Output:
   ```
   Forwarding: tcp://0.tcp.ngrok.io:12345 -> localhost:4840
   ```

5. **Connect Ignition**:
   ```
   Endpoint URL: opc.tcp://0.tcp.ngrok.io:12345/ot-simulator/server/
   ```

**Limitations**:
- ❌ Ngrok URL changes on restart (free tier)
- ❌ Not suitable for production
- ❌ Adds latency
- ✅ Good for quick demos

---

## Troubleshooting

### Issue 1: Ignition Can't Connect

**Symptoms**: Connection status shows "Faulted" or "Disconnected"

**Solutions**:

1. **Check Simulator is Running**:
   ```bash
   # Check if port 4840 is open
   lsof -i:4840  # Mac/Linux
   netstat -an | grep 4840  # Windows
   ```

2. **Test with OPC UA Client**:
   ```bash
   # Install UaExpert (free OPC UA client)
   # Try connecting to verify endpoint is accessible
   ```

3. **Check Firewall**:
   ```bash
   # Mac
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --list

   # Linux
   sudo ufw status
   sudo ufw allow 4840/tcp

   # Windows
   # Control Panel → Windows Defender Firewall → Allow an app
   ```

4. **Verify Endpoint URL Format**:
   ```
   ✅ Correct: opc.tcp://192.168.1.100:4840/ot-simulator/server/
   ❌ Wrong:   opc.tcp://192.168.1.100:4840/ot-simulator/server
   ❌ Wrong:   opc.tcp://192.168.1.100:4840
   ```

### Issue 2: Security Certificate Errors

**Symptoms**: "Untrusted certificate" or "Security validation failed"

**Solutions**:

1. **Trust Certificate in Ignition**:
   - When first connecting, Ignition will prompt to trust certificate
   - Click **Accept** and **Trust**

2. **Disable Security for Testing**:
   ```yaml
   opcua:
     security:
       enabled: false
   ```

   Then in Ignition:
   ```
   Security Policy: None
   ```

3. **Use Production Certificates** (CA-signed):
   - Replace self-signed cert with CA-signed certificate
   - Import CA cert into Ignition trusted store

### Issue 3: Can See Server But No Tags

**Symptoms**: Connection successful but tag browser is empty

**Solutions**:

1. **Check Namespace**:
   - Browse to namespace `http://databricks.com/iot-simulator`
   - Tags should appear under **Objects** → Industry folders

2. **Verify Simulator Data Generation**:
   - Check Web UI at http://localhost:8989
   - Ensure sensors are showing live data

3. **Check Ignition Tag Scan Class**:
   - Config → OPC UA → Settings
   - Ensure scan class is enabled (not paused)

---

## Performance Considerations

### Bandwidth

**Per Sensor**:
- Update rate: 2 Hz (500ms intervals)
- Data size: ~50 bytes per update
- Bandwidth: ~100 bytes/sec per sensor

**All 379 Sensors**:
- Total bandwidth: ~38 KB/sec
- Monthly data: ~100 GB/month
- **Recommendation**: Subscribe to only needed sensors in Ignition

### Latency

**Local Network**: < 10ms
**Internet (Cloud VM)**: 50-200ms depending on location
**Ngrok Tunnel**: 100-500ms (adds extra hop)

### Scaling

**Single Simulator Instance**:
- Max concurrent clients: 10-20 (depends on VM size)
- Max sensors: 379 (current)
- Update rate: 2 Hz (configurable in config.yaml)

**To Scale**:
- Use multiple simulator instances with different namespaces
- Deploy behind load balancer
- Use Databricks for connector at scale (ingests to Delta Lake)

---

## Testing Checklist

- [ ] Simulator running and accessible
- [ ] OPC UA port 4840 open in firewall
- [ ] Ignition connection configured
- [ ] Connection status shows "Connected" in Ignition
- [ ] Can browse tags in Ignition Designer
- [ ] Tag values updating in real-time
- [ ] Web UI accessible (optional)
- [ ] (Production) Security enabled and certificates trusted

---

## Quick Reference

### Connection Strings

**Local Machine**:
```
opc.tcp://localhost:4840/ot-simulator/server/
```

**Local Network**:
```
opc.tcp://192.168.1.x:4840/ot-simulator/server/
```

**Cloud VM**:
```
opc.tcp://<public-ip>:4840/ot-simulator/server/
opc.tcp://54.123.45.67:4840/ot-simulator/server/
```

**Ngrok (Dev Only)**:
```
opc.tcp://0.tcp.ngrok.io:12345/ot-simulator/server/
```

### Useful Commands

**Check if OPC UA server is running**:
```bash
lsof -i:4840  # Mac/Linux
netstat -an | findstr 4840  # Windows
```

**Test connectivity**:
```bash
telnet <ip> 4840
```

**View simulator logs**:
```bash
tail -f ot_simulator.log
```

---

## Next Steps

1. **For Local Testing**: Follow "Quick Start - Local Network" section
2. **For Production**: Deploy to AWS/Azure VM with security enabled
3. **For Databricks Apps**: Deploy Web UI separately, use VM for OPC UA
4. **For Quick Demo**: Use ngrok tunnel

## Support

- **Simulator Documentation**: See `README.md`
- **Security Guide**: See `SECURITY_IMPLEMENTATION_GUIDE.md`
- **Deployment Guide**: See `DEPLOYMENT_GUIDE_DATABRICKS_APPS.md`

---

**Last Updated**: 2026-01-15
**Simulator Version**: 1.0 (with advanced visualizations)
