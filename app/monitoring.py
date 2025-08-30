"""
Comprehensive monitoring and metrics for the AI recommendation service.
Production-ready observability with Prometheus metrics, health checks, and performance monitoring.
"""
import time
import asyncio
import psutil
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import threading
import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
)

from app.logger import get_logger
from app.exceptions import ServiceUnavailableError

logger = get_logger(__name__)

# ================================
# PROMETHEUS METRICS
# ================================

# Create custom registry for isolation
metrics_registry = CollectorRegistry()

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=metrics_registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=metrics_registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint'],
    registry=metrics_registry
)

# AI service metrics
ai_requests_total = Counter(
    'ai_requests_total',
    'Total number of AI service requests',
    ['provider', 'model', 'status'],
    registry=metrics_registry
)

ai_request_duration_seconds = Histogram(
    'ai_request_duration_seconds',
    'AI request duration in seconds',
    ['provider', 'model'],
    registry=metrics_registry
)

ai_token_usage_total = Counter(
    'ai_token_usage_total',
    'Total AI tokens used',
    ['provider', 'model', 'type'],
    registry=metrics_registry
)

# Recommendation metrics
recommendations_generated_total = Counter(
    'recommendations_generated_total',
    'Total recommendations generated',
    ['user_type', 'ai_enhanced'],
    registry=metrics_registry
)

recommendation_quality_score = Histogram(
    'recommendation_quality_score',
    'Recommendation quality scores',
    ['type'],
    registry=metrics_registry
)

# System metrics
system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=metrics_registry
)

system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=metrics_registry
)

system_disk_usage_percent = Gauge(
    'system_disk_usage_percent',
    'System disk usage percentage',
    registry=metrics_registry
)

# Application metrics
app_info = Info(
    'app_info',
    'Application information',
    registry=metrics_registry
)

active_users = Gauge(
    'active_users_total',
    'Number of active users',
    ['time_window'],
    registry=metrics_registry
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=metrics_registry
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=metrics_registry
)

# Error metrics
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'endpoint'],
    registry=metrics_registry
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service'],
    registry=metrics_registry
)


# ================================
# PERFORMANCE MONITORING
# ================================

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_bytes: int
    disk_percent: float
    active_connections: int
    response_time_avg: float
    error_rate: float


class PerformanceMonitor:
    """System performance monitoring"""
    
    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 data points
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Initialize app info
        app_info.info({
            'version': os.getenv('VERSION', '1.0.0'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            'startup_time': datetime.utcnow().isoformat()
        })
    
    def start(self):
        """Start performance monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self.thread.start()
        logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop performance monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _collect_metrics(self):
        """Collect system metrics periodically"""
        while self.running:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_info = psutil.virtual_memory()
                disk_info = psutil.disk_usage('/')
                
                # Update Prometheus metrics
                system_cpu_usage_percent.set(cpu_percent)
                system_memory_usage_bytes.set(memory_info.used)
                system_disk_usage_percent.set(disk_info.percent)
                
                # Calculate application metrics
                active_connections = len(psutil.net_connections())
                
                # Store metrics history
                metrics = PerformanceMetrics(
                    timestamp=datetime.utcnow(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory_info.percent,
                    memory_bytes=memory_info.used,
                    disk_percent=disk_info.percent,
                    active_connections=active_connections,
                    response_time_avg=self._calculate_avg_response_time(),
                    error_rate=self._calculate_error_rate()
                )
                
                self.metrics_history.append(metrics)
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error collecting performance metrics: {e}", exc_info=True)
                time.sleep(self.collection_interval)
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time from recent requests"""
        # This would typically use request timing data
        # For now, return a placeholder
        return 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate from recent requests"""
        # This would typically use request error data
        # For now, return a placeholder
        return 0.0
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, hours: int = 24) -> List[PerformanceMetrics]:
        """Get metrics history for the specified number of hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]


# ================================
# REQUEST TRACKING
# ================================

class RequestTracker:
    """Track request patterns and user activity"""
    
    def __init__(self):
        self.active_requests: Dict[str, float] = {}
        self.user_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'error_count': 0,
            'last_access': None
        })
    
    def start_request(self, request_id: str, endpoint: str, method: str):
        """Record the start of a request"""
        self.active_requests[request_id] = time.time()
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
    
    def end_request(
        self,
        request_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: Optional[str] = None
    ):
        """Record the end of a request"""
        if request_id not in self.active_requests:
            return
        
        # Calculate duration
        start_time = self.active_requests.pop(request_id)
        duration = time.time() - start_time
        
        # Update Prometheus metrics
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).dec()
        
        # Update endpoint statistics
        stats = self.endpoint_stats[f"{method} {endpoint}"]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['last_access'] = datetime.utcnow()
        
        if status_code >= 400:
            stats['error_count'] += 1
            errors_total.labels(
                error_type=f"http_{status_code}",
                endpoint=endpoint
            ).inc()
        
        # Track user activity
        if user_id:
            self.user_activity[user_id].append(time.time())
            self._update_active_users_metrics()
    
    def _update_active_users_metrics(self):
        """Update active users metrics"""
        current_time = time.time()
        
        # Count active users in different time windows
        for window_name, window_seconds in [
            ('1_minute', 60),
            ('5_minutes', 300),
            ('1_hour', 3600)
        ]:
            active_count = 0
            cutoff_time = current_time - window_seconds
            
            for user_id, activity in self.user_activity.items():
                if activity and activity[-1] >= cutoff_time:
                    active_count += 1
            
            active_users.labels(time_window=window_name).set(active_count)
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get endpoint statistics"""
        stats = {}
        for endpoint, data in self.endpoint_stats.items():
            if data['count'] > 0:
                stats[endpoint] = {
                    'count': data['count'],
                    'avg_response_time': data['total_time'] / data['count'],
                    'error_rate': data['error_count'] / data['count'],
                    'last_access': data['last_access'].isoformat() if data['last_access'] else None
                }
        return stats


# ================================
# HEALTH CHECKS
# ================================

@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    check_function: callable
    timeout: float = 5.0
    critical: bool = True


class HealthMonitor:
    """Comprehensive health monitoring"""
    
    def __init__(self):
        self.health_checks: List[HealthCheck] = []
        self.last_health_status: Dict[str, Any] = {}
    
    def register_check(self, check: HealthCheck):
        """Register a health check"""
        self.health_checks.append(check)
        logger.info(f"Registered health check: {check.name}")
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and return status"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {},
            'summary': {
                'total_checks': len(self.health_checks),
                'passed': 0,
                'failed': 0,
                'critical_failed': 0
            }
        }
        
        for check in self.health_checks:
            check_result = await self._run_single_check(check)
            health_status['checks'][check.name] = check_result
            
            if check_result['status'] == 'pass':
                health_status['summary']['passed'] += 1
            else:
                health_status['summary']['failed'] += 1
                if check.critical:
                    health_status['summary']['critical_failed'] += 1
        
        # Determine overall health status
        if health_status['summary']['critical_failed'] > 0:
            health_status['status'] = 'unhealthy'
        elif health_status['summary']['failed'] > 0:
            health_status['status'] = 'degraded'
        
        self.last_health_status = health_status
        return health_status
    
    async def _run_single_check(self, check: HealthCheck) -> Dict[str, Any]:
        """Run a single health check"""
        start_time = time.time()
        result = {
            'status': 'fail',
            'duration_seconds': 0.0,
            'message': '',
            'critical': check.critical
        }
        
        try:
            # Run the check with timeout
            check_task = asyncio.create_task(self._execute_check(check))
            await asyncio.wait_for(check_task, timeout=check.timeout)
            
            result['status'] = 'pass'
            result['message'] = f'{check.name} is healthy'
            
        except asyncio.TimeoutError:
            result['message'] = f'{check.name} check timed out after {check.timeout}s'
            
        except Exception as e:
            result['message'] = f'{check.name} check failed: {str(e)}'
            
        finally:
            result['duration_seconds'] = round(time.time() - start_time, 3)
        
        return result
    
    async def _execute_check(self, check: HealthCheck):
        """Execute a health check function"""
        if asyncio.iscoroutinefunction(check.check_function):
            return await check.check_function()
        else:
            return check.check_function()


# ================================
# MONITORING MIDDLEWARE
# ================================

class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request monitoring and metrics collection"""
    
    def __init__(self, app, request_tracker: RequestTracker):
        super().__init__(app)
        self.request_tracker = request_tracker
    
    async def dispatch(self, request: Request, call_next):
        # Skip monitoring for metrics endpoint
        if request.url.path == '/metrics':
            return await call_next(request)
        
        request_id = getattr(request.state, 'request_id', 'unknown')
        endpoint = request.url.path
        method = request.method
        user_id = None  # Extract from request if available
        
        # Start tracking request
        self.request_tracker.start_request(request_id, endpoint, method)
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            # Handle exceptions and record error metrics
            status_code = 500
            errors_total.labels(
                error_type=type(e).__name__,
                endpoint=endpoint
            ).inc()
            raise
            
        finally:
            # End tracking request
            self.request_tracker.end_request(
                request_id, endpoint, method, status_code, user_id
            )
        
        return response


# ================================
# GLOBAL INSTANCES
# ================================

# Global monitoring instances
performance_monitor = PerformanceMonitor()
request_tracker = RequestTracker()
health_monitor = HealthMonitor()


# ================================
# MONITORING ENDPOINTS
# ================================

async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(metrics_registry),
        media_type=CONTENT_TYPE_LATEST
    )


async def get_health_status():
    """Comprehensive health check endpoint"""
    return await health_monitor.run_health_checks()


async def get_performance_metrics():
    """Get current performance metrics"""
    current_metrics = performance_monitor.get_current_metrics()
    if not current_metrics:
        return {"message": "No metrics available yet"}
    
    return {
        "timestamp": current_metrics.timestamp.isoformat(),
        "cpu_percent": current_metrics.cpu_percent,
        "memory_percent": current_metrics.memory_percent,
        "memory_bytes": current_metrics.memory_bytes,
        "disk_percent": current_metrics.disk_percent,
        "active_connections": current_metrics.active_connections,
        "response_time_avg": current_metrics.response_time_avg,
        "error_rate": current_metrics.error_rate
    }


async def get_endpoint_stats():
    """Get endpoint statistics"""
    return request_tracker.get_endpoint_stats()


# ================================
# UTILITY FUNCTIONS
# ================================

def record_ai_request(provider: str, model: str, duration: float, tokens_used: int = 0, success: bool = True):
    """Record AI service request metrics"""
    status = 'success' if success else 'error'
    
    ai_requests_total.labels(
        provider=provider,
        model=model,
        status=status
    ).inc()
    
    ai_request_duration_seconds.labels(
        provider=provider,
        model=model
    ).observe(duration)
    
    if tokens_used > 0:
        ai_token_usage_total.labels(
            provider=provider,
            model=model,
            type='total'
        ).inc(tokens_used)


def record_recommendation_generated(user_type: str = 'regular', ai_enhanced: bool = False, quality_score: float = 0.0):
    """Record recommendation generation metrics"""
    recommendations_generated_total.labels(
        user_type=user_type,
        ai_enhanced=str(ai_enhanced).lower()
    ).inc()
    
    if quality_score > 0:
        recommendation_quality_score.labels(type='ai' if ai_enhanced else 'content').observe(quality_score)


def record_cache_hit(cache_type: str = 'general'):
    """Record cache hit"""
    cache_hits_total.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = 'general'):
    """Record cache miss"""
    cache_misses_total.labels(cache_type=cache_type).inc()


def update_circuit_breaker_state(service: str, state: str):
    """Update circuit breaker state metric"""
    state_values = {'closed': 0, 'open': 1, 'half-open': 2}
    circuit_breaker_state.labels(service=service).set(state_values.get(state, 0))


def start_monitoring():
    """Start all monitoring components"""
    performance_monitor.start()
    logger.info("Monitoring system started")


def stop_monitoring():
    """Stop all monitoring components"""
    performance_monitor.stop()
    logger.info("Monitoring system stopped")