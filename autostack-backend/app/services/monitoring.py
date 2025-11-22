"""
Real monitoring service for AutoStack MVP
Replaces mock monitoring with actual system metrics
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psutil
from pathlib import Path

from sqlalchemy import select, func

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from ..db import AsyncSessionLocal
from ..models import Deployment, DeploymentContainer
from .container_runtime import record_health_check
from .real_k8s_orchestrator import get_cluster_snapshot


class RealMonitoringService:
    """Real monitoring service that collects actual metrics"""
    
    def __init__(self):
        self.metrics_history: Dict[str, List[Dict]] = {}
        self.alerts: List[Dict] = []
        self.start_time = datetime.utcnow()
        self.runtime_health_failures: Dict[str, int] = {}
        
    async def collect_system_metrics(self) -> Dict:
        """Collect real system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process_count = len(psutil.pids())
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "system": {
                    "cpu": {
                        "percent": cpu_percent,
                        "count": cpu_count,
                        "frequency_mhz": cpu_freq.current if cpu_freq else None
                    },
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "used": memory.used,
                        "swap_total": swap.total,
                        "swap_used": swap.used,
                        "swap_percent": swap.percent
                    },
                    "disk": {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percent": (disk.used / disk.total) * 100,
                        "read_bytes": disk_io.read_bytes if disk_io else 0,
                        "write_bytes": disk_io.write_bytes if disk_io else 0
                    },
                    "network": {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv
                    },
                    "processes": {
                        "count": process_count,
                        "running": len([p for p in psutil.process_iter() if p.status() == 'running'])
                    }
                }
            }
            
            # Store in history
            self._store_metric("system", metrics)
            
            return metrics
            
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "system": {}
            }
    
    async def collect_docker_metrics(self) -> Dict:
        """Collect Docker container metrics"""
        if not DOCKER_AVAILABLE:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Docker not available",
                "containers": []
            }
        
        try:
            docker_client = docker.from_env()
            containers = docker_client.containers.list(all=True)
            
            container_metrics = []
            for container in containers:
                try:
                    stats = container.stats(stream=False)
                    
                    # Parse container stats
                    cpu_usage = self._calculate_container_cpu(stats)
                    memory_usage = stats["memory_stats"]["usage"]
                    memory_limit = stats["memory_stats"]["limit"]
                    
                    container_info = {
                        "id": container.id[:12],
                        "name": container.name,
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else container.image.id,
                        "cpu_percent": cpu_usage,
                        "memory_usage": memory_usage,
                        "memory_limit": memory_limit,
                        "memory_percent": (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0,
                        "network_rx": stats.get("networks", {}).get("eth0", {}).get("rx_bytes", 0),
                        "network_tx": stats.get("networks", {}).get("eth0", {}).get("tx_bytes", 0),
                        "created": container.attrs["Created"],
                        "started": container.attrs.get("State", {}).get("StartedAt")
                    }
                    
                    container_metrics.append(container_info)
                    
                except Exception as e:
                    container_metrics.append({
                        "id": container.id[:12],
                        "name": container.name,
                        "error": str(e)
                    })
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "containers": container_metrics,
                "total_containers": len(containers),
                "running_containers": len([c for c in containers if c.status == "running"])
            }
            
            self._store_metric("docker", metrics)
            return metrics
            
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "containers": []
            }
    
    async def collect_deployment_metrics(self) -> Dict:
        """Collect deployment-specific metrics"""
        try:
            snapshot = get_cluster_snapshot(None)
            pods_raw = snapshot.get("pods", [])
            services_raw = snapshot.get("services", [])
            deployments_raw = snapshot.get("deployments", [])

            total_pods = len(pods_raw)
            running_pods = sum(
                1 for pod in pods_raw if pod.get("status", {}).get("phase") == "Running"
            )

            cluster_status = {
                "total_pods": total_pods,
                "running_pods": running_pods,
                "services": len(services_raw),
                "deployments": len(deployments_raw),
                "docker_available": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

            pod_metrics = []
            for pod in pods_raw:
                meta = pod.get("metadata", {})
                status = pod.get("status", {})
                container_statuses = status.get("containerStatuses", []) or []
                ready = bool(container_statuses) and all(
                    cs.get("ready") for cs in container_statuses
                )
                container_id = (
                    container_statuses[0].get("containerID") if container_statuses else None
                )

                pod_metrics.append(
                    {
                        "pod_id": meta.get("uid") or meta.get("name"),
                        "pod_name": meta.get("name"),
                        "status": status.get("phase"),
                        "ready": ready,
                        "metrics": {},
                        "health": {
                            "healthy": ready and status.get("phase") == "Running",
                            "reason": None,
                            "status": status.get("phase"),
                            "last_check": datetime.utcnow().isoformat(),
                        },
                        "created_at": meta.get("creationTimestamp"),
                    }
                )

            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "cluster": cluster_status,
                "pods": pod_metrics,
                "deployments": len(deployments_raw),
                "services": len(services_raw),
            }
            
            self._store_metric("deployments", metrics)
            return metrics
            
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "cluster": {},
                "pods": []
            }
    
    async def collect_application_metrics(self) -> Dict:
        """Collect application-specific metrics"""
        try:
            # AutoStack application metrics
            from ..db import AsyncSessionLocal
            from ..models import Deployment, User
            
            async with AsyncSessionLocal() as db:
                # Deployment metrics (all users)
                total_deployments_result = await db.execute(
                    select(func.count()).select_from(Deployment).where(Deployment.is_deleted.is_(False))
                )
                total_deployments = total_deployments_result.scalar() or 0

                success_deployments_result = await db.execute(
                    select(func.count()).select_from(Deployment).where(
                        Deployment.status == "success",
                        Deployment.is_deleted.is_(False),
                    )
                )
                success_deployments = success_deployments_result.scalar() or 0

                failed_deployments_result = await db.execute(
                    select(func.count()).select_from(Deployment).where(
                        Deployment.status == "failed",
                        Deployment.is_deleted.is_(False),
                    )
                )
                failed_deployments = failed_deployments_result.scalar() or 0

                # User metrics
                total_users_result = await db.execute(select(func.count()).select_from(User))
                total_users = total_users_result.scalar() or 0

                active_cutoff = datetime.utcnow() - timedelta(days=30)
                active_users_result = await db.execute(
                    select(func.count()).select_from(User).where(User.created_at > active_cutoff)
                )
                active_users = active_users_result.scalar() or 0

                # Recent activity (last 24h)
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_deployments_result = await db.execute(
                    select(func.count()).select_from(Deployment).where(
                        Deployment.created_at > recent_cutoff,
                        Deployment.is_deleted.is_(False),
                    )
                )
                recent_deployments = recent_deployments_result.scalar() or 0

            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "application": {
                    "deployments": {
                        "total": total_deployments,
                        "successful": success_deployments,
                        "failed": failed_deployments,
                        "success_rate": (success_deployments) / max(total_deployments or 1, 1) * 100,
                        "last_24h": recent_deployments,
                    },
                    "users": {
                        "total": total_users,
                        "active_30d": active_users,
                    }
                }
            }
            
            self._store_metric("application", metrics)
            return metrics
            
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "application": {}
            }
    
    def _calculate_container_cpu(self, stats: Dict) -> float:
        """Calculate CPU usage percentage for container"""
        try:
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                         stats["precpu_stats"]["system_cpu_usage"]
            
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * \
                              len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"]) * 100
                return round(cpu_percent, 2)
        except (KeyError, ZeroDivisionError):
            pass
        
        return 0.0
    
    def _store_metric(self, metric_type: str, metrics: Dict):
        """Store metrics in history"""
        if metric_type not in self.metrics_history:
            self.metrics_history[metric_type] = []
        
        self.metrics_history[metric_type].append(metrics)
        
        # Keep only last 100 entries per metric type
        if len(self.metrics_history[metric_type]) > 100:
            self.metrics_history[metric_type] = self.metrics_history[metric_type][-100:]
    
    async def get_metrics_summary(self) -> Dict:
        """Get comprehensive metrics summary"""
        # Collect all metrics types
        system_metrics = await self.collect_system_metrics()
        docker_metrics = await self.collect_docker_metrics()
        deployment_metrics = await self.collect_deployment_metrics()
        application_metrics = await self.collect_application_metrics()
        
        # Calculate uptime
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "system": system_metrics.get("system", {}),
            "docker": docker_metrics,
            "deployments": deployment_metrics,
            "application": application_metrics.get("application", {}),
            "alerts": self._check_alerts(system_metrics, docker_metrics, deployment_metrics)
        }
    
    def _check_alerts(self, system_metrics: Dict, docker_metrics: Dict, deployment_metrics: Dict) -> List[Dict]:
        """Check for alert conditions"""
        alerts = []
        
        # System alerts
        system = system_metrics.get("system", {})
        if system.get("cpu", {}).get("percent", 0) > 80:
            alerts.append({
                "type": "warning",
                "message": "High CPU usage detected",
                "value": system["cpu"]["percent"],
                "threshold": 80,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        if system.get("memory", {}).get("percent", 0) > 85:
            alerts.append({
                "type": "warning", 
                "message": "High memory usage detected",
                "value": system["memory"]["percent"],
                "threshold": 85,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        if system.get("disk", {}).get("percent", 0) > 90:
            alerts.append({
                "type": "critical",
                "message": "Disk space critically low",
                "value": system["disk"]["percent"],
                "threshold": 90,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Docker alerts
        if docker_metrics.get("running_containers", 0) == 0 and docker_metrics.get("total_containers", 0) > 0:
            alerts.append({
                "type": "warning",
                "message": "No running containers",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Deployment alerts
        failed_pods = len([p for p in deployment_metrics.get("pods", []) if p.get("status") == "Failed"])
        if failed_pods > 0:
            alerts.append({
                "type": "warning",
                "message": f"{failed_pods} failed pods detected",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        self.alerts.extend(alerts)
        
        # Keep only last 50 alerts
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
        
        return alerts
    
    async def get_metrics_history(self, metric_type: str, hours: int = 24) -> List[Dict]:
        """Get historical metrics for a specific type"""
        if metric_type not in self.metrics_history:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            metric for metric in self.metrics_history[metric_type]
            if datetime.fromisoformat(metric["timestamp"].replace("Z", "+00:00")) > cutoff_time
        ]
    
    async def check_runtime_health(self) -> None:
        """Periodically verify health of running deployment containers.

        For each running DeploymentContainer, perform an HTTP health check and track
        consecutive failures per deployment. After 3 consecutive failed checks, mark
        the deployment as failed and emit an alert that surfaces in /api/monitoring/alerts.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DeploymentContainer, Deployment)
                .join(Deployment, DeploymentContainer.deployment_id == Deployment.id)
                .where(DeploymentContainer.status == "running", Deployment.is_deleted.is_(False))
            )
            rows = result.all()

            for container, deployment in rows:
                url = deployment.deployed_url or f"http://{container.host}:{container.port}/"
                try:
                    hc = await record_health_check(db, deployment, url)
                    healthy = hc.is_live
                except Exception:
                    healthy = False

                key = str(deployment.id)
                if not healthy:
                    failures = self.runtime_health_failures.get(key, 0) + 1
                    self.runtime_health_failures[key] = failures
                    if failures >= 3:
                        reason = "Deployment failing health checks"
                        existing = deployment.failed_reason or ""
                        if reason not in existing:
                            deployment.failed_reason = (existing + "\n" if existing else "") + reason
                        if deployment.status != "failed":
                            deployment.status = "failed"
                        self.alerts.append(
                            {
                                "type": "critical",
                                "message": f"Deployment {deployment.id} failing health checks",
                                "value": None,
                                "threshold": 3,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                else:
                    # Reset failure counter on success
                    if key in self.runtime_health_failures:
                        self.runtime_health_failures[key] = 0

            await db.commit()
    
    async def start_monitoring(self, interval: int = 30):
        """Start continuous monitoring"""
        while True:
            try:
                await self.get_metrics_summary()
                await self.check_runtime_health()
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(interval)


# Global monitoring instance
monitoring_service = RealMonitoringService()
