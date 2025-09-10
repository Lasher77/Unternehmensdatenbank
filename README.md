# BVMW Companies Backend

This project provides an API for managing company data in Germany.

## Lokale Installation auf macOS

1. Voraussetzungen installieren (einmalig):

   - [Docker Desktop f\u00fcr Mac](https://www.docker.com/products/docker-desktop/)
   - Optional: [Homebrew](https://brew.sh/) und Node.js f\u00fcr das Frontend (`brew install node`)

2. Repository klonen und ins Projektverzeichnis wechseln:

   ```bash
   git clone <repository-url>
   cd Unternehmensdatenbank
   ```

3. Backend starten:

   ```bash
   cp .env.example .env
   docker compose up --build
   ```

4. Frontend starten (optional):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Die API ist anschlie\u00dfend unter <http://localhost:8080> erreichbar und die Weboberfl\u00e4che unter <http://localhost:3000>.

## Development

```bash
cp .env.example .env
docker compose up --build
```

Swagger UI: <http://localhost:8080/docs>
MinIO Console: <http://localhost:9001>

### Example Requests

Import:
```bash
curl -F "label=Q3_2025" -F "file=@/path/to/file.jsonl" http://localhost:8080/api/imports
```

Search:
```bash
curl -X POST http://localhost:8080/api/search/companies -H "Content-Type: application/json" \
  -d '{"q":"Miele","city":"G\u00fctersloh","page":1,"per_page":20}'
```

Export:
```bash
curl -X POST http://localhost:8080/api/exports -H "Content-Type: application/json" \
  -d '{"format":"csv","wz":"62.01","state":"BY"}'
```
