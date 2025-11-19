# Frontend

## Setup

```bash
npm install
npm run dev
```

Create `.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
NEXT_PUBLIC_FAKE_TASK_POLL=true
```

## Features

- Suche mit Facetten und Export
- Detailansicht
- Mehrdatei-Import mit Upload-Progress

Screenshots:

![Search](docs/search.png)
![Import](docs/import.png)

## Salesforce Match API Tester

Die HTML-Datei `public/salesforce-api-tester.html` hilft Dir, das
`/api/salesforce/match-company` Endpoint unserer Datenbank vor der eigentlichen Salesforce
Integration zu testen. Öffne die Datei direkt im Browser, stelle Basis-URL und Token ein und
fülle die Query-Felder für Name, Adresse, Website usw. aus – der Request-Body wird daraus
automatisch generiert (alternativ kannst Du eigenes JSON einfügen). Das Tool zeigt Dir eine
cURL-Vorschau, sendet den Request samt optionaler Header und visualisiert Status,
Antwort-Header sowie den Body.
