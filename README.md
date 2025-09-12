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

   Die Datenbank nutzt ein PostgreSQL-Image mit PostGIS-Erweiterung.

4. SQL-Migrationen ausführen:

   ```bash
   for f in backend/migrations/*.sql; do
     docker compose exec -T db psql -U postgres -d companies -f "$f"
   done
   ```

5. Frontend starten (optional):

   Das Frontend ben\u00f6tigt die Umgebungsvariable `NEXT_PUBLIC_API_BASE_URL`, die auf die Basis-URL des Backends zeigt.

    ```bash
    cd frontend
    npm install
    echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8080" > .env.local
    npm run dev
    ```

Die API ist anschlie\u00dfend unter <http://localhost:8080> erreichbar und die Weboberfl\u00e4che unter <http://localhost:3000>.


## Lokale Installation ohne Docker

1. Voraussetzungen installieren:

   - Python 3.11+
   - PostgreSQL, Redis, OpenSearch und MinIO müssen lokal laufen
   - Optional: Node.js für das Frontend

2. Repository klonen und ins Projektverzeichnis wechseln:

   ```bash
   git clone <repository-url>
   cd Unternehmensdatenbank
   ```

3. Python-Abhängigkeiten installieren:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

4. Konfiguration anpassen:

   ```bash
   cp .env.example .env
   ```

   In `.env` die Hostnamen auf `localhost` ändern, z. B.:

   ```
   POSTGRES_HOST=localhost
   REDIS_HOST=localhost
   OPENSEARCH_HOST=localhost
   S3_ENDPOINT_URL=http://localhost:9000
   ```

   Starte PostgreSQL, Redis, OpenSearch und MinIO auf den entsprechenden Ports und führe die SQL-Skripte in `backend/migrations` in deiner Datenbank aus.

5. Backend starten:

   ```bash
   uvicorn backend.app.main:app --reload
   ```

6. Frontend starten (optional):

   Das Frontend ben\u00f6tigt die Umgebungsvariable `NEXT_PUBLIC_API_BASE_URL`, die auf die Basis-URL des Backends zeigt.

    ```bash
    cd frontend
    npm install
    echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8080" > .env.local
    npm run dev
    ```

Die API ist anschließend unter <http://localhost:8080> erreichbar und die Weboberfläche unter <http://localhost:3000>.


## Development

```bash
cp .env.example .env
docker compose up --build
for f in backend/migrations/*.sql; do
  docker compose exec -T db psql -U postgres -d companies -f "$f"
done
```

Swagger UI: <http://localhost:8080/docs>
MinIO Console: <http://localhost:9001>

### OpenSearch über HTTPS

Setze in deiner `.env` die Variable `OPENSEARCH_USE_SSL=true`, wenn dein OpenSearch-Cluster über HTTPS erreichbar ist.
Die Anwendung prüft Zertifikate dabei nicht (`verify_certs=False`), sodass selbstsignierte Zertifikate akzeptiert werden.
Für produktive Umgebungen sollte ein vertrauenswürdiges Zertifikat genutzt und die Prüfung aktiviert werden.

### Example Requests

Import (requires running worker service):

Start the Celery worker before triggering an import:

```bash
docker compose up worker
```

Then run the import:

```bash
curl -F "label=Q3_2025" -F "file=@/path/to/file.jsonl" http://localhost:8080/api/imports
```

The initial task parses the NDJSON file and loads the data into staging tables.
Afterwards a follow-up Celery task promotes the staged rows into the `companies`
and `events` tables, using `source_id` to upsert existing entries and linking
records to the corresponding `ingestion_run`.

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
