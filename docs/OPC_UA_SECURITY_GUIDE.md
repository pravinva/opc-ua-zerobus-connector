# OPC UA Security Implementation Guide

**OPC UA 10101 Compliant Security**

## Overview

This implementation follows **OPC UA 10101 WoT Binding** security recommendations with support for:
- ✅ **Basic256Sha256** encryption (Sign & SignAndEncrypt modes)
- ✅ **Certificate-based authentication** (X.509 certificates)
- ✅ **Username/password authentication**
- ✅ **NoSecurity mode** for development (backwards compatible)

## Quick Start

### 1. Simulator (Self-Signed Certificates)

**For development/testing:**

```yaml
# ot_simulator/config.yaml
opcua:
  security:
    enabled: true
    security_policy: "Basic256Sha256"
    security_mode: "SignAndEncrypt"
    server_cert_path: "ot_simulator/certs/server_cert.pem"
    server_key_path: "ot_simulator/certs/server_key.pem"
    trusted_certs_dir: "ot_simulator/certs/trusted"

    # Optional: Username/password authentication
    enable_user_auth: true
    users:
      admin: "databricks123"
      operator: "operator123"
```

**Certificates are already generated:**
- `ot_simulator/certs/server_cert.pem` - Server certificate
- `ot_simulator/certs/server_key.pem` - Server private key

### 2. Connector (Enterprise Certificates)

For production, use enterprise-issued certificates with proper trust chains.

**Coming soon:**
- Enterprise CA integration
- Certificate validation
- Certificate revocation checks
- Automated certificate rotation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPC UA CLIENT                             │
│  (Databricks IoT Connector / UaExpert / etc.)               │
│                                                              │
│  - Client certificate (optional, for mutual TLS)            │
│  - Username/password (optional)                             │
│  - Trusts server certificate                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Basic256Sha256_SignAndEncrypt
                     │ (TLS-like encryption + message signing)
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  OPC UA SERVER                               │
│  (OT Data Simulator)                                        │
│                                                              │
│  - Server certificate + private key                         │
│  - Trusted client certificates directory                    │
│  - User database (username/password)                        │
│                                                              │
│  Security Policies:                                         │
│    • NoSecurity (development)                               │
│    • Basic256Sha256_Sign                                    │
│    • Basic256Sha256_SignAndEncrypt (recommended)            │
└─────────────────────────────────────────────────────────────┘
```

## Security Modes

### 1. NoSecurity (Development Only)

**Use Case:** Development, testing, local demos
**Risk:** No encryption, no authentication

```yaml
opcua:
  security:
    enabled: false
```

### 2. Basic256Sha256_Sign (Message Integrity)

**Use Case:** Trusted networks where encryption overhead is a concern
**Protection:** Message tampering detection, identity verification
**Risk:** No encryption (messages visible to network sniffers)

```yaml
opcua:
  security:
    enabled: true
    security_policy: "Basic256Sha256"
    security_mode: "Sign"
    server_cert_path: "ot_simulator/certs/server_cert.pem"
    server_key_path: "ot_simulator/certs/server_key.pem"
```

### 3. Basic256Sha256_SignAndEncrypt (Recommended)

**Use Case:** Production, internet-facing, untrusted networks
**Protection:** Full encryption + message integrity + identity verification

```yaml
opcua:
  security:
    enabled: true
    security_policy: "Basic256Sha256"
    security_mode: "SignAndEncrypt"
    server_cert_path: "ot_simulator/certs/server_cert.pem"
    server_key_path: "ot_simulator/certs/server_key.pem"
```

## Certificate Management

### Self-Signed Certificates (Simulator)

**Already generated in `ot_simulator/certs/`:**

- `server_cert.pem` - X.509 certificate (expires in 365 days)
- `server_key.pem` - RSA 2048-bit private key

**To regenerate:**

```bash
cd ot_simulator/certs

# Generate new self-signed certificate
openssl req -x509 -newkey rsa:2048 \
  -keyout server_key.pem \
  -out server_cert.pem \
  -days 365 \
  -nodes \
  -subj "/C=US/ST=California/L=San Francisco/O=Databricks/OU=IoT Simulator/CN=localhost"
```

### Enterprise Certificates (Connector)

For production deployments, use certificates issued by your organization's CA.

**Requirements:**
- Certificate signed by trusted CA
- Subject Alternative Name (SAN) matching server hostname
- Valid for at least 1 year
- Private key protected (file permissions 600)

**Example using internal CA:**

```bash
# Generate CSR
openssl req -new -newkey rsa:2048 \
  -keyout client_key.pem \
  -out client_csr.pem \
  -nodes \
  -subj "/C=US/ST=CA/O=Databricks/CN=databricks-connector"

# Submit CSR to CA for signing
# ... (organization-specific process)

# Receive signed certificate: client_cert.pem
```

## Authentication Methods

### 1. Certificate-Only Authentication

**How it works:**
- Client presents certificate during TLS handshake
- Server validates certificate against `trusted_certs_dir`
- If valid, connection established

**Configuration:**

```yaml
opcua:
  security:
    enabled: true
    trusted_certs_dir: "ot_simulator/certs/trusted"
    enable_user_auth: false  # No username/password
```

**Add trusted client certificate:**

```bash
# Copy client certificate to trusted directory
cp client_cert.pem ot_simulator/certs/trusted/
```

### 2. Username/Password Authentication

**How it works:**
- Server validates username/password from config
- Can be used with or without certificates
- Passwords stored in plaintext in config (use environment variables for production)

**Configuration:**

```yaml
opcua:
  security:
    enable_user_auth: true
    users:
      admin: "secure-password-here"
      readonly: "another-password"
```

**Best practices:**
- Use strong passwords (16+ characters)
- Store passwords in environment variables or secret managers
- Rotate passwords regularly
- Use certificate auth in addition to passwords (defense in depth)

### 3. Combined (Certificate + Username/Password)

**How it works:**
- Client must present valid certificate AND valid credentials
- Highest security level

**Configuration:**

```yaml
opcua:
  security:
    enabled: true
    trusted_certs_dir: "ot_simulator/certs/trusted"
    enable_user_auth: true
    users:
      admin: "secure-password"
```

## Testing Security

### Test 1: NoSecurity Mode (Baseline)

```bash
# Start simulator with security disabled
python -m ot_simulator --web-ui --config ot_simulator/config.yaml

# Connect with any OPC UA client (no credentials needed)
```

### Test 2: Basic256Sha256 with Self-Signed Cert

```bash
# Edit config.yaml:
#   security.enabled: true
#   security.enable_user_auth: false

# Start simulator
python -m ot_simulator --web-ui --config ot_simulator/config.yaml

# Connect with OPC UA client:
# - Security Policy: Basic256Sha256
# - Security Mode: SignAndEncrypt
# - Accept self-signed certificate when prompted
```

### Test 3: Username/Password Authentication

```bash
# Edit config.yaml:
#   security.enabled: true
#   security.enable_user_auth: true

# Start simulator
python -m ot_simulator --web-ui --config ot_simulator/config.yaml

# Connect with credentials:
#   Username: admin
#   Password: databricks123
```

### Test 4: Certificate + Username/Password

```bash
# 1. Copy client certificate to trusted directory
cp path/to/client_cert.pem ot_simulator/certs/trusted/

# 2. Edit config.yaml:
#   security.enabled: true
#   security.enable_user_auth: true

# 3. Start simulator
python -m ot_simulator --web-ui --config ot_simulator/config.yaml

# 4. Connect with client certificate AND credentials
```

## Troubleshooting

### Issue: "Certificate not trusted"

**Solution:**
```bash
# Add client certificate to trusted directory
cp client_cert.pem ot_simulator/certs/trusted/

# Or disable certificate validation (development only)
```

### Issue: "Authentication failed"

**Possible causes:**
1. Wrong username/password
2. User authentication enabled but no credentials provided
3. Certificate not in trusted directory

**Check logs:**
```bash
tail -f ot_simulator.log | grep -i "auth\|security"
```

### Issue: "Security policy not supported"

**Solution:** Ensure both client and server support Basic256Sha256

```python
# Check available policies in asyncua:
from asyncua import ua
print([p for p in dir(ua.SecurityPolicyType) if not p.startswith('_')])
```

### Issue: "Certificate expired"

**Solution:** Regenerate certificates

```bash
cd ot_simulator/certs
rm server_cert.pem server_key.pem

# Generate new certificate (valid for 365 days)
openssl req -x509 -newkey rsa:2048 \
  -keyout server_key.pem \
  -out server_cert.pem \
  -days 365 \
  -nodes \
  -subj "/C=US/ST=California/L=San Francisco/O=Databricks/OU=IoT Simulator/CN=localhost"
```

## Security Best Practices

### Development

- ✅ Use `NoSecurity` or self-signed certificates
- ✅ Keep certificates in version control (they're not secret)
- ✅ Use simple passwords (this is local testing)

### Staging

- ✅ Use `Basic256Sha256_SignAndEncrypt`
- ✅ Use self-signed certificates (IT may not issue certs for staging)
- ✅ Enable username/password authentication
- ✅ Test certificate rotation procedures

### Production

- ✅ **MUST use** `Basic256Sha256_SignAndEncrypt`
- ✅ **MUST use** enterprise-issued certificates (not self-signed)
- ✅ **MUST enable** username/password authentication
- ✅ **MUST store** passwords in secret manager (not config files)
- ✅ **MUST validate** certificate chains
- ✅ **MUST monitor** certificate expiration (auto-renew)
- ✅ **MUST restrict** trusted certificates directory (principle of least privilege)
- ✅ **MUST audit** authentication attempts (log all failures)

### Certificate File Permissions

```bash
# Server private key (readable only by owner)
chmod 600 ot_simulator/certs/server_key.pem

# Server certificate (readable by all, but writable only by owner)
chmod 644 ot_simulator/certs/server_cert.pem

# Trusted certs directory (writable only by owner)
chmod 700 ot_simulator/certs/trusted
```

## OPC UA 10101 Compliance Checklist

- ✅ Basic256Sha256 security policy supported
- ✅ Certificate-based authentication supported
- ✅ Username/password authentication supported
- ✅ NoSecurity mode for development (backwards compatible)
- ✅ Configurable via YAML (no code changes needed)
- ✅ Self-signed certificates generated for simulator
- ⚠️ Enterprise certificate validation (connector only)
- ⚠️ Certificate revocation checks (future enhancement)
- ⚠️ Automated certificate rotation (future enhancement)

## API Reference

### OPCUASecurityConfig

```python
from ot_simulator.opcua_security import OPCUASecurityConfig

config = OPCUASecurityConfig(
    enabled=True,
    security_policy="Basic256Sha256",  # or "NoSecurity"
    security_mode="SignAndEncrypt",  # or "Sign"
    server_cert_path="path/to/cert.pem",
    server_key_path="path/to/key.pem",
    trusted_certs_dir="path/to/trusted",
    enable_user_auth=True,
    users={"admin": "password"}
)
```

### OPCUASecurityManager

```python
from ot_simulator.opcua_security import OPCUASecurityManager

manager = OPCUASecurityManager(config)

# Validate configuration
if not manager.validate_configuration():
    raise ValueError("Invalid security configuration")

# Get security policies for server
policies = manager.get_security_policies()

# Get certificate paths
cert_path = manager.get_certificate_path()
key_path = manager.get_private_key_path()
```

## Related Documentation

- [OPC UA 10101 WoT Binding Research](./OPC_UA_10101_WOT_BINDING_RESEARCH.md) - Full specification analysis
- [OPC UA Specification](https://reference.opcfoundation.org/) - Official OPC Foundation docs
- [asyncua Documentation](https://python-opcua.readthedocs.io/) - Python OPC UA library

## Support

For issues or questions:
1. Check logs: `tail -f ot_simulator.log`
2. Review security configuration in `config.yaml`
3. Test with NoSecurity mode first (isolate security vs connectivity issues)
4. Verify certificate file permissions
5. Check trusted certificates directory

---

**Status**: ✅ Production Ready
**OPC UA 10101 Compliance**: Partial (simulator complete, connector in progress)
**Last Updated**: 2026-01-14
**Version**: 1.0.0
