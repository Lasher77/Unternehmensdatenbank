fmt:
black backend

lint:
ruff backend

test:
pytest -q

up:
docker compose up --build
