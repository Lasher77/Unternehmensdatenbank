# OpenSearch TLS certificates

This directory contains a self-signed certificate (`opensearch.crt`) and its
corresponding private key (`opensearch.key`) for local development.

## Generating a new certificate

Run the provided script to create a new key and certificate:

```bash
./generate_certs.sh
```

You can customise the common name and validity period:

```bash
CN=my-hostname DAYS=730 ./generate_certs.sh
```

The script ensures the files are readable by the OpenSearch process by setting
permissions to `640`.
