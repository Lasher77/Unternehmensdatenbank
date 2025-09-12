#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="$(dirname "$0")"

openssl req -x509 -nodes -days "${DAYS:-365}" -newkey rsa:2048 \
  -keyout "${CERT_DIR}/opensearch.key" \
  -out "${CERT_DIR}/opensearch.crt" \
  -subj "/CN=${CN:-localhost}"

# Ensure the OpenSearch process can read the files
chmod 640 "${CERT_DIR}/opensearch.key" "${CERT_DIR}/opensearch.crt"
