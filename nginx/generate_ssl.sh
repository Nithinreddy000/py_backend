#!/bin/bash
#
# SSL Certificate Generator Script for Development
# This script generates self-signed SSL certificates for development use
#

set -e

# Create directory if it doesn't exist
mkdir -p ssl
cd ssl

echo "Generating self-signed SSL certificates for development..."

# Generate 2048-bit RSA private key
openssl genrsa -out nginx.key 2048

# Generate CSR (Certificate Signing Request)
openssl req -new -key nginx.key -out nginx.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in nginx.csr -signkey nginx.key -out nginx.crt

# Generate DHE parameters
echo "Generating DHE parameters (this may take a moment)..."
openssl dhparam -out dhparam.pem 2048

# Set permissions
chmod 600 nginx.key dhparam.pem
chmod 644 nginx.crt

echo "SSL certificates generated successfully!"
echo "Files created:"
echo "  - nginx.key (private key)"
echo "  - nginx.crt (certificate)"
echo "  - dhparam.pem (DH parameters)"
echo ""
echo "NOTE: These are self-signed certificates for DEVELOPMENT use only."
echo "      Do NOT use these certificates in production environments."

cd .. 