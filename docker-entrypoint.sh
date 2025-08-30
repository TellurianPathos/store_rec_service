#!/bin/bash

# Production-ready entrypoint script for AI recommendation service
# Handles initialization, health checks, and graceful shutdown

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local host="$2"
    local port="$3"
    local max_attempts=30
    local attempt=1

    log "Waiting for $service_name to be ready at $host:$port..."

    while [ $attempt -le $max_attempts ]; do
        if command_exists nc && nc -z "$host" "$port"; then
            log_success "$service_name is ready!"
            return 0
        elif command_exists curl && curl -f --connect-timeout 1 "http://$host:$port" >/dev/null 2>&1; then
            log_success "$service_name is ready!"
            return 0
        fi

        log "Attempt $attempt/$max_attempts: $service_name not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "$service_name is not ready after $max_attempts attempts"
    return 1
}

# Function to check environment variables
check_env_vars() {
    log "Checking environment variables..."

    # Check required environment variables for production
    if [ "$ENVIRONMENT" = "production" ]; then
        local required_vars=(
            "ENVIRONMENT"
        )

        for var in "${required_vars[@]}"; do
            if [ -z "${!var}" ]; then
                log_error "Required environment variable $var is not set"
                return 1
            fi
        done

        # Warn about missing optional but recommended variables
        local optional_vars=(
            "LOG_LEVEL"
            "SECURITY_REQUIRE_API_KEY"
            "AI_OPENAI_API_KEY"
            "AI_ANTHROPIC_API_KEY"
        )

        for var in "${optional_vars[@]}"; do
            if [ -z "${!var}" ]; then
                log_warn "Optional environment variable $var is not set"
            fi
        done
    fi

    log_success "Environment variables check completed"
}

# Function to check data files
check_data_files() {
    log "Checking data files..."

    local data_path="${DATA_PATH:-data/generic_dataset.csv}"
    
    if [ -f "$data_path" ]; then
        local file_size=$(stat -f%z "$data_path" 2>/dev/null || stat -c%s "$data_path" 2>/dev/null || echo "unknown")
        log_success "Data file found: $data_path (size: $file_size bytes)"
    else
        log_warn "Data file not found: $data_path"
        log "Service will run with limited functionality"
    fi

    # Check ML models directory
    local model_path="${MODEL_PATH:-ml_models}"
    if [ -d "$model_path" ]; then
        local model_count=$(find "$model_path" -name "*.pkl" -o -name "*.joblib" | wc -l)
        log_success "ML models directory found: $model_path ($model_count model files)"
    else
        log_warn "ML models directory not found: $model_path"
        mkdir -p "$model_path"
        log "Created ML models directory: $model_path"
    fi
}

# Function to check external dependencies
check_external_deps() {
    log "Checking external dependencies..."

    # Check Redis if configured
    if [ -n "$REDIS_HOST" ] && [ "$REDIS_HOST" != "localhost" ]; then
        local redis_port="${REDIS_PORT:-6379}"
        if wait_for_service "Redis" "$REDIS_HOST" "$redis_port"; then
            log_success "Redis connection verified"
        else
            log_error "Failed to connect to Redis at $REDIS_HOST:$redis_port"
            if [ "$ENVIRONMENT" = "production" ]; then
                return 1
            fi
        fi
    fi

    # Check database if configured
    if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ]; then
        local db_port="${DB_PORT:-5432}"
        if wait_for_service "Database" "$DB_HOST" "$db_port"; then
            log_success "Database connection verified"
        else
            log_error "Failed to connect to database at $DB_HOST:$db_port"
            if [ "$ENVIRONMENT" = "production" ]; then
                return 1
            fi
        fi
    fi

    log_success "External dependencies check completed"
}

# Function to validate Python dependencies
check_python_deps() {
    log "Checking Python dependencies..."

    # Check critical dependencies
    python -c "
import sys
import importlib
import pkg_resources

critical_packages = [
    'fastapi',
    'uvicorn',
    'pydantic',
    'scikit-learn',
    'pandas',
    'numpy'
]

missing_packages = []
for package in critical_packages:
    try:
        importlib.import_module(package.replace('-', '_'))
        print(f'✓ {package} - OK')
    except ImportError:
        missing_packages.append(package)
        print(f'✗ {package} - MISSING', file=sys.stderr)

if missing_packages:
    print(f'Missing critical packages: {missing_packages}', file=sys.stderr)
    sys.exit(1)
else:
    print('All critical Python dependencies are available')
"

    if [ $? -ne 0 ]; then
        log_error "Python dependencies check failed"
        return 1
    fi

    log_success "Python dependencies check completed"
}

# Function to run pre-startup validation
run_validation() {
    log "Running pre-startup validation..."

    # Run all checks
    check_env_vars || return 1
    check_data_files || return 1
    check_external_deps || return 1
    check_python_deps || return 1

    log_success "All validation checks passed!"
}

# Function to setup logging directory
setup_logging() {
    local log_dir="${LOG_DIR:-logs}"
    
    if [ ! -d "$log_dir" ]; then
        mkdir -p "$log_dir"
        log "Created logging directory: $log_dir"
    fi

    # Ensure proper permissions
    chmod 755 "$log_dir"
}

# Function to handle graceful shutdown
cleanup() {
    log "Received shutdown signal, initiating graceful shutdown..."
    
    # Kill the main process if it exists
    if [ -n "$MAIN_PID" ]; then
        log "Stopping main application process (PID: $MAIN_PID)..."
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        
        # Wait for graceful shutdown
        for i in $(seq 1 30); do
            if ! kill -0 "$MAIN_PID" 2>/dev/null; then
                log_success "Application stopped gracefully"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            log_warn "Forcing application shutdown..."
            kill -KILL "$MAIN_PID" 2>/dev/null || true
        fi
    fi
    
    log "Cleanup completed"
    exit 0
}

# Function to start the application
start_application() {
    log "Starting AI Recommendation Service..."

    # Set default values
    local host="${HOST:-0.0.0.0}"
    local port="${PORT:-8000}"
    local workers="${WORKERS:-1}"
    local log_level="${LOG_LEVEL:-info}"

    # Build uvicorn command
    local cmd=(
        "uvicorn"
        "app.main:app"
        "--host" "$host"
        "--port" "$port"
        "--log-level" "$log_level"
    )

    # Add workers for production
    if [ "$ENVIRONMENT" = "production" ] && [ "$workers" -gt 1 ]; then
        cmd+=("--workers" "$workers")
    fi

    # Add reload for development
    if [ "$ENVIRONMENT" = "development" ]; then
        cmd+=("--reload")
    fi

    # Log the startup command
    log "Starting with command: ${cmd[*]}"
    log "Environment: ${ENVIRONMENT:-development}"
    log "Host: $host, Port: $port, Workers: $workers"

    # Start the application in background
    "${cmd[@]}" &
    MAIN_PID=$!

    log "Application started with PID: $MAIN_PID"

    # Wait for the application to start
    sleep 5

    # Check if application is running
    if kill -0 "$MAIN_PID" 2>/dev/null; then
        log_success "AI Recommendation Service is running successfully!"
        
        # Wait for the main process to finish
        wait "$MAIN_PID"
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            log "Application exited normally"
        else
            log_error "Application exited with code: $exit_code"
        fi
        
        exit $exit_code
    else
        log_error "Application failed to start"
        exit 1
    fi
}

# Main execution
main() {
    log "=== AI Recommendation Service Startup ==="
    log "Version: ${VERSION:-unknown}"
    log "Environment: ${ENVIRONMENT:-development}"
    log "Python version: $(python --version)"
    
    # Setup signal handlers for graceful shutdown
    trap cleanup SIGTERM SIGINT SIGQUIT

    # Setup logging
    setup_logging

    # Run validation unless disabled
    if [ "${SKIP_VALIDATION:-false}" != "true" ]; then
        run_validation || {
            log_error "Validation failed, exiting..."
            exit 1
        }
    else
        log_warn "Validation skipped (SKIP_VALIDATION=true)"
    fi

    # Execute the provided command or start default application
    if [ $# -eq 0 ]; then
        start_application
    else
        log "Executing custom command: $*"
        exec "$@"
    fi
}

# Run main function with all arguments
main "$@"