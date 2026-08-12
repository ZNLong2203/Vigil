SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help install up down logs seed api worker web web-build dev smoke chaos fixtures models twist digest fmt test clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install dependencies (uv)
	uv sync
	@test -f .env || (cp .env.example .env && echo "→ created .env from .env.example")

up: ## Start the local emulator stack (Firestore, Pub/Sub, GCS, Jaeger)
	docker compose up -d
	@echo "waiting for emulators…"
	@until docker compose ps --format '{{.Service}} {{.Health}}' 2>/dev/null \
	  | grep -E '^(firestore|pubsub) healthy' | wc -l | grep -q 2; do sleep 2; done
	@echo "✓ firestore  localhost:8080"
	@echo "✓ pubsub     localhost:8085"
	@echo "✓ gcs        localhost:4443"
	@echo "✓ jaeger UI  http://localhost:16686"

down: ## Stop the local stack
	docker compose down -v

logs: ## Tail emulator logs
	docker compose logs -f

seed: ## Create topics, subscription and bucket inside the emulators
	uv run python scripts/bootstrap_local.py

fixtures: ## Regenerate the synthetic corpus (PDFs, photos, voice notes)
	uv run python scripts/generate_synthetic_data.py
	uv run python scripts/generate_synthetic_images.py
	uv run python scripts/generate_synthetic_audio.py

digest: ## Render the weekly digest (Gemini text, Veo video, Lyria cues)
	FIRESTORE_EMULATOR_HOST= uv run python -m vigil.digest_demo

twist: ## Put a deliberately gamed instruction through the eval gate
	FIRESTORE_EMULATOR_HOST= uv run python -m vigil.fleet.twist_demo

models: ## Check credentials and list the model ids this account can use
	uv run python scripts/check_models.py

api: ## Run the API (http://localhost:8000/docs)
	uv run uvicorn vigil.api:app --reload --port 8000 --app-dir src

worker: ## Run the background worker
	uv run python -m vigil.worker

web: ## Run the UI in dev mode (http://localhost:3000)
	cd web && npm run dev

web-build: ## Build the UI to a static bundle (web/out)
	cd web && npm install --silent && npm run build

dev: up seed ## Start everything, then print what to run next
	@echo
	@echo "Now open three terminals:"
	@echo "  make api      # ingress   → http://localhost:8000/docs"
	@echo "  make worker   # background execution"
	@echo "  make web      # UI        → http://localhost:3000"
	@echo "Then:  make smoke"

smoke: ## Send one event through the whole pipeline
	@bash scripts/smoke_test.sh

chaos: ## Kill the worker mid-flight — proves resume + exactly-once
	@bash scripts/demo_chaos.sh

fmt: ## Format and lint
	uv run ruff format . && uv run ruff check --fix .

test: ## Run tests
	uv run pytest -q

clean: down ## Stop the stack and remove local artifacts
	rm -rf .pytest_cache .ruff_cache **/__pycache__
