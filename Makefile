# Makefile for AI Recommendation Service
# Production-ready development and deployment automation

.PHONY: help install install-dev test test-coverage lint format type-check security-check
.PHONY: build build-dev run run-dev stop clean logs shell
.PHONY: deploy deploy-prod migrate backup restore
.PHONY: docker-build docker-push docker-pull
.PHONY: monitoring setup-monitoring

# Default target
.DEFAULT_GOAL := help

# Variables
APP_NAME := ai-recommendation-service
VERSION := $(shell grep -m1 version pyproject.toml | tr -s ' ' | tr -d '"' | cut -d' ' -f3)
DOCKER_REGISTRY := your-registry.com
DOCKER_IMAGE := $(DOCKER_REGISTRY)/$(APP_NAME)
COMPOSE_FILE := docker-compose.yml
COMPOSE_DEV_FILE := docker-compose.dev.yml

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Help target
help: ## Show this help message
	@echo "$(BLUE)AI Recommendation Service - Development & Deployment Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# ================================
# DEVELOPMENT SETUP
# ================================

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	uv sync --no-dev
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	uv sync --dev
	@echo "$(GREEN)Development dependencies installed successfully!$(NC)"

setup: install-dev ## Setup development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	cp .env.example .env
	mkdir -p logs data/cache ml_models
	@echo "$(GREEN)Development environment setup complete!$(NC)"
	@echo "$(YELLOW)Please edit .env file with your configuration$(NC)"

# ================================
# CODE QUALITY
# ================================

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	python -m pytest tests/ -v --tb=short

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	python integration_tests.py

lint: ## Run linting (ruff)
	@echo "$(BLUE)Running linter...$(NC)"
	ruff check app/ tests/
	@echo "$(GREEN)Linting complete!$(NC)"

format: ## Format code with black and ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	ruff format app/ tests/
	ruff check --fix app/ tests/
	@echo "$(GREEN)Code formatting complete!$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	mypy app/
	@echo "$(GREEN)Type checking complete!$(NC)"

security-check: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	@echo "Checking for known vulnerabilities in dependencies..."
	pip-audit
	@echo "$(GREEN)Security checks complete!$(NC)"

quality: lint type-check test ## Run all quality checks

# ================================
# DOCKER OPERATIONS
# ================================

build: ## Build production Docker image
	@echo "$(BLUE)Building production Docker image...$(NC)"
	docker build -t $(APP_NAME):$(VERSION) -t $(APP_NAME):latest .
	@echo "$(GREEN)Docker image built successfully!$(NC)"

build-dev: ## Build development Docker image
	@echo "$(BLUE)Building development Docker image...$(NC)"
	docker build -t $(APP_NAME):dev --target builder .
	@echo "$(GREEN)Development Docker image built successfully!$(NC)"

run: ## Run application with Docker Compose
	@echo "$(BLUE)Starting application services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)Services started! Access the app at http://localhost:8000$(NC)"

run-dev: ## Run development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose -f $(COMPOSE_DEV_FILE) up -d
	@echo "$(GREEN)Development environment started!$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)PgAdmin: http://localhost:8080$(NC)"
	@echo "$(YELLOW)Redis Commander: http://localhost:8081$(NC)"

stop: ## Stop all services
	@echo "$(BLUE)Stopping all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down
	docker-compose -f $(COMPOSE_DEV_FILE) down
	@echo "$(GREEN)All services stopped!$(NC)"

logs: ## Show application logs
	docker-compose -f $(COMPOSE_FILE) logs -f ai-recommendation-service

logs-dev: ## Show development logs
	docker-compose -f $(COMPOSE_DEV_FILE) logs -f ai-recommendation-service-dev

shell: ## Get shell access to running container
	docker-compose -f $(COMPOSE_FILE) exec ai-recommendation-service bash

shell-dev: ## Get shell access to development container
	docker-compose -f $(COMPOSE_DEV_FILE) exec ai-recommendation-service-dev bash

clean: ## Clean up Docker resources
	@echo "$(BLUE)Cleaning up Docker resources...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans
	docker-compose -f $(COMPOSE_DEV_FILE) down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)Cleanup complete!$(NC)"

# ================================
# MONITORING AND OBSERVABILITY
# ================================

monitoring: ## Start monitoring stack (Prometheus + Grafana)
	@echo "$(BLUE)Starting monitoring stack...$(NC)"
	docker-compose --profile monitoring up -d
	@echo "$(GREEN)Monitoring started!$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/admin)$(NC)"

ollama: ## Start Ollama for local AI
	@echo "$(BLUE)Starting Ollama service...$(NC)"
	docker-compose --profile ollama up -d
	@echo "$(GREEN)Ollama started at http://localhost:11434$(NC)"
	@echo "$(YELLOW)To download a model: docker exec -it ai-recommendation-ollama ollama pull llama2$(NC)"

load-balancer: ## Start Nginx load balancer
	@echo "$(BLUE)Starting load balancer...$(NC)"
	docker-compose --profile load-balancer up -d
	@echo "$(GREEN)Load balancer started!$(NC)"

# ================================
# DEPLOYMENT
# ================================

deploy-staging: build ## Deploy to staging environment
	@echo "$(BLUE)Deploying to staging...$(NC)"
	@echo "$(YELLOW)This would typically push to staging servers$(NC)"
	docker tag $(APP_NAME):$(VERSION) $(DOCKER_IMAGE):staging-$(VERSION)
	# docker push $(DOCKER_IMAGE):staging-$(VERSION)
	@echo "$(GREEN)Staging deployment complete!$(NC)"

deploy-prod: build security-check ## Deploy to production
	@echo "$(RED)WARNING: This will deploy to production!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	@echo "$(BLUE)Deploying to production...$(NC)"
	docker tag $(APP_NAME):$(VERSION) $(DOCKER_IMAGE):$(VERSION)
	docker tag $(APP_NAME):$(VERSION) $(DOCKER_IMAGE):latest
	# docker push $(DOCKER_IMAGE):$(VERSION)
	# docker push $(DOCKER_IMAGE):latest
	@echo "$(GREEN)Production deployment complete!$(NC)"

# ================================
# DATABASE OPERATIONS
# ================================

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec ai-recommendation-service python -c "
	from app.database import migrate_database
	migrate_database()
	"
	@echo "$(GREEN)Migrations complete!$(NC)"

backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(NC)"
	mkdir -p backups
	docker-compose -f $(COMPOSE_FILE) exec postgres pg_dump -U recommendations_user recommendations > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backup created in backups/ directory$(NC)"

restore: ## Restore database (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "$(RED)Please specify BACKUP_FILE=path/to/backup.sql$(NC)"; exit 1; fi
	@echo "$(BLUE)Restoring database from $(BACKUP_FILE)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U recommendations_user -d recommendations < $(BACKUP_FILE)
	@echo "$(GREEN)Database restored successfully!$(NC)"

# ================================
# MAINTENANCE
# ================================

health-check: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)API health check failed$(NC)"
	@docker-compose -f $(COMPOSE_FILE) ps
	@echo "$(GREEN)Health check complete!$(NC)"

update-deps: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	uv sync --upgrade
	@echo "$(GREEN)Dependencies updated!$(NC)"

generate-requirements: ## Generate requirements.txt from pyproject.toml
	@echo "$(BLUE)Generating requirements.txt...$(NC)"
	uv export --no-hashes > requirements.txt
	@echo "$(GREEN)requirements.txt generated!$(NC)"

# ================================
# UTILITY TARGETS
# ================================

docs: ## Generate API documentation
	@echo "$(BLUE)Starting documentation server...$(NC)"
	@echo "$(YELLOW)API docs will be available at http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Make sure the service is running first$(NC)"

init-data: ## Initialize sample data
	@echo "$(BLUE)Initializing sample data...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec ai-recommendation-service python scripts/init_sample_data.py
	@echo "$(GREEN)Sample data initialized!$(NC)"

benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running performance benchmarks...$(NC)"
	python scripts/benchmark.py
	@echo "$(GREEN)Benchmarks complete!$(NC)"

# ================================
# CI/CD HELPERS
# ================================

ci-test: install-dev lint type-check test security-check ## Run all CI checks
	@echo "$(GREEN)All CI checks passed!$(NC)"

ci-build: build ## Build for CI/CD pipeline
	@echo "$(GREEN)CI build complete!$(NC)"

version: ## Show current version
	@echo "$(BLUE)Current version: $(GREEN)$(VERSION)$(NC)"

# ================================
# QUICK COMMANDS
# ================================

quick-start: build run ## Quick start (build and run)
	@echo "$(GREEN)Quick start complete! Service running at http://localhost:8000$(NC)"

dev-start: setup run-dev ## Quick development start
	@echo "$(GREEN)Development environment ready!$(NC)"

full-stack: run-dev monitoring ollama ## Start full development stack with monitoring
	@echo "$(GREEN)Full development stack is running!$(NC)"