.PHONY: up down logs test backend-test frontend-build

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f backend frontend

test backend-test:
	cd backend && python -m pytest -q

frontend-build:
	cd frontend && npm run build
