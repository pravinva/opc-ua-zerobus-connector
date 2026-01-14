# OPC UA Certificates Directory

This directory contains self-signed certificates for OPC UA server development and testing.

**⚠️ DO NOT USE IN PRODUCTION** - These are self-signed certificates for development only.

## Quick Setup

Generate self-signed certificates:

```bash
cd ot_simulator/certs

# Generate server certificate and private key
openssl req -x509 -newkey rsa:2048 \
  -keyout server_key.pem \
  -out server_cert.pem \
  -days 365 \
  -nodes \
  -subj "/C=US/ST=California/L=San Francisco/O=Databricks/OU=IoT Simulator/CN=localhost"

# Create trusted certificates directory
mkdir -p trusted

# Set proper permissions
chmod 600 server_key.pem
chmod 644 server_cert.pem
chmod 700 trusted
```

## Files

- `server_cert.pem` - Server X.509 certificate (RSA 2048-bit, 365 days validity)
- `server_key.pem` - Server private key (**never commit this file**)
- `trusted/` - Directory for trusted client certificates

## Production Setup

For production, use certificates issued by your organization's Certificate Authority:

1. Generate a Certificate Signing Request (CSR)
2. Submit CSR to your CA
3. Receive signed certificate
4. Install certificate and private key
5. Update `config.yaml` with paths

See [OPC_UA_SECURITY_GUIDE.md](../../OPC_UA_SECURITY_GUIDE.md) for detailed instructions.

## Security Notes

- Private keys are protected by `.gitignore` (never committed to version control)
- Self-signed certificates are acceptable for development/testing
- Production deployments MUST use CA-signed certificates
- Rotate certificates before expiration (365 days for self-signed)
- Monitor certificate expiration dates

## Troubleshooting

### Certificate expired

```bash
# Check expiration date
openssl x509 -in server_cert.pem -noout -enddate

# If expired, regenerate
rm server_cert.pem server_key.pem
# Run generation command above
```

### Permission denied

```bash
# Fix file permissions
chmod 600 server_key.pem
chmod 644 server_cert.pem
```

### Client certificate not trusted

```bash
# Add client certificate to trusted directory
cp path/to/client_cert.pem trusted/
```
