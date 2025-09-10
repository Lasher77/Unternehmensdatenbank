# BVMW Companies Backend

This project provides an API for managing company data in Germany.

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
