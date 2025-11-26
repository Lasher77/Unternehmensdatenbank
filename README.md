# BVMW Companies Backend

This project provides an API for managing company data in Germany.

## Schnellstart

F\u00fcr eine lokale Entwicklungsumgebung mit Docker steht ein Hilfsskript bereit:

```bash
./scripts/dev-start.sh
```

Das Skript kopiert bei Bedarf die Beispieldatei `.env.example`, startet alle Docker-Services
und f\u00fchrt s\u00e4mtliche SQL-Migrationen aus. Anschlie\u00dfend ist das Backend unter
<http://localhost:8080> erreichbar. Das Frontend kann danach mit

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080 npm run dev
```

gestartet werden.

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

   Die Datenbank nutzt ein schlankes PostgreSQL 16 Alpine Image.

4. SQL-Migrationen ausführen:

   ```bash
   docker compose run --rm backend python scripts/run_migrations.py
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

   Starte PostgreSQL, Redis, OpenSearch und MinIO auf den entsprechenden Ports und führe die SQL-Skripte in `backend/migrations`
   (z. B. mit `python backend/scripts/run_migrations.py`) in deiner Datenbank aus.

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
docker compose run --rm backend python scripts/run_migrations.py
```

Swagger UI: <http://localhost:8080/docs>
MinIO Console: <http://localhost:9001>

### OpenSearch neu aufbauen

Um den Firmenindex nach Imports oder Schemaänderungen neu aufzubauen, nutze das bestehende Backend-Image und rufe das Skript innerhalb des Containers auf:

```bash
docker compose run --rm backend python scripts/reindex_companies.py
```

Der Container arbeitet im Verzeichnis `/app`; dank eines Symlinks funktioniert auch der ältere Pfad `python backend/scripts/reindex_companies.py` wieder.

### Salesforce Matching API Token

Die Salesforce-Matching-Endpunkte erwarten einen Bearer-Token in der `Authorization`-Headerzeile.
Lege dazu in deiner `.env` den Wert `SALESFORCE_MATCH_API_TOKEN=<geheimes-token>` fest und
verwende bei Anfragen z. B. `Authorization: Bearer <geheimes-token>`. Ohne konfigurierten Token
werden die Endpunkte automatisch gesperrt.

Du kannst das HTML-Tool `frontend/public/salesforce-api-tester.html` direkt im Browser öffnen,
um Anfragen gegen das Match- oder Ping-Endpoint zusammenzuklicken. Das Tool zeigt gleichzeitig
den fertigen `curl`-Befehl an.

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

Der Worker führt vor dem Start automatisch `scripts/run_migrations.py` aus, damit
alle SQL-Migrationen—including die Erweiterung der `persons`-Tabelle und die
Unique-Constraint—angewendet sind.

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

Salesforce Match Endpoint:

```bash
curl -X POST 'http://localhost:8080/api/salesforce/match-company' \
  -H 'Authorization: Bearer <dein-token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "name": "Müritz",
      "email": "kontakt@mueritz.de",
      "website": "mueritz.de",
      "city": "Berlin",
      "country": "DE"
    },
    "options": {
      "min_score": 0.5,
      "max_results": 10
    }
  }'
```
