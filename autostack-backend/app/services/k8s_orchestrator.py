"""
Kubernetes-like container orchestrator for MVP
Simulates K8s concepts: Pods, Services, Health Checks, Scaling
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    print("Docker SDK not available - using mock mode")


@dataclass
class PodSpec:
    """Kubernetes-like Pod specification"""
    name: str
    image: str
    port: int
    env_vars: Dict[str, str]
    labels: Dict[str, str]
    container_name: str


@dataclass
class ServiceSpec:
    """Kubernetes-like Service specification"""
    name: str
    selector: Dict[str, str]
    ports: List[int]
    type: str = "ClusterIP"


@dataclass
class PodStatus:
    """Pod status information"""
    phase: str  # Pending, Running, Succeeded, Failed, Unknown
    conditions: Dict[str, bool]
    start_time: Optional[datetime]
    ready: bool
    restart_count: int
    container_status: Dict[str, any]


class KubernetesSimulator:
    """Simulates Kubernetes orchestration concepts"""
    
    def __init__(self):
        self.pods: Dict[str, Dict] = {}
        self.services: Dict[str, Dict] = {}
        self.deployments: Dict[str, Dict] = {}
        self.health_checks: Dict[str, Dict] = {}
        
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
                self.docker_available = True
            except Exception as e:
                print(f"Docker not available: {e}")
                self.docker_available = False
        else:
            self.docker_available = False
    
    async def create_pod(self, spec: PodSpec) -> Dict:
        """Create a pod (simulates K8s Pod creation)"""
        pod_id = str(uuid.uuid4())
        
        pod = {
            "id": pod_id,
            "name": spec.name,
            "spec": spec,
            "status": PodStatus(
                phase="Pending",
                conditions={"PodScheduled": False, "Initialized": False, "Ready": False},
                start_time=datetime.utcnow(),
                ready=False,
                restart_count=0,
                container_status={}
            ),
            "created_at": datetime.utcnow(),
            "container_id": None
        }
        
        self.pods[pod_id] = pod
        
        # Simulate pod scheduling and initialization
        await self._simulate_pod_lifecycle(pod_id)
        
        return pod
    
    async def _simulate_pod_lifecycle(self, pod_id: str):
        """Simulate Kubernetes pod lifecycle phases"""
        phases = [
            ("PodScheduled", 2),  # 2 seconds to schedule
            ("Initialized", 3),   # 3 seconds to initialize
            ("Running", 5)        # 5 seconds to start running
        ]
        
        for phase, delay in phases:
            await asyncio.sleep(delay)
            
            if pod_id in self.pods:
                pod = self.pods[pod_id]
                pod["status"].conditions[phase] = True
                
                if phase == "Running":
                    pod["status"].phase = "Running"
                    pod["status"].ready = True
                    
                    # Actually start the container if Docker is available
                    if self.docker_available:
                        await self._start_container(pod_id)
                
                # Broadcast status update
                await self._broadcast_pod_status(pod_id)
    
    async def _start_container(self, pod_id: str):
        """Start actual Docker container"""
        if not self.docker_available or pod_id not in self.pods:
            return
        
        pod = self.pods[pod_id]
        spec = pod["spec"]
        
        try:
            # Create and start container
            container = self.docker_client.containers.run(
                spec.image,
                name=f"autostack-{spec.name}-{pod_id[:8]}",
                ports={f"{spec.port}/tcp": spec.port},
                environment=spec.env_vars,
                detach=True,
                remove=False
            )
            
            pod["container_id"] = container.id
            pod["status"].container_status = {
                "container_id": container.id,
                "image": spec.image,
                "restart_count": 0,
                "ready": True
            }
            
        except Exception as e:
            print(f"Failed to start container: {e}")
            pod["status"].phase = "Failed"
            pod["status"].container_status = {
                "error": str(e),
                "ready": False
            }
    
    async def create_service(self, spec: ServiceSpec) -> Dict:
        """Create a service (simulates K8s Service)"""
        service_id = str(uuid.uuid4())
        
        service = {
            "id": service_id,
            "name": spec.name,
            "spec": spec,
            "endpoints": [],  # Will be populated by matching pods
            "created_at": datetime.utcnow()
        }
        
        self.services[service_id] = service
        
        # Find matching pods and create endpoints
        await self._update_service_endpoints(service_id)
        
        return service
    
    async def _update_service_endpoints(self, service_id: str):
        """Update service endpoints based on pod labels"""
        if service_id not in self.services:
            return
        
        service = self.services[service_id]
        selector = service["spec"].selector
        
        # Find pods matching the selector
        matching_pods = []
        for pod in self.pods.values():
            if all(pod["spec"].labels.get(k) == v for k, v in selector.items()):
                if pod["status"].ready:
                    matching_pods.append({
                        "pod_id": pod["id"],
                        "pod_name": pod["name"],
                        "ip": "127.0.0.1",  # In real K8s, this would be pod IP
                        "ports": service["spec"].ports
                    })
        
        service["endpoints"] = matching_pods
    
    async def get_pod_metrics(self, pod_id: str) -> Dict:
        """Get pod metrics (simulates K8s metrics server)"""
        if pod_id not in self.pods:
            return {}
        
        pod = self.pods[pod_id]
        
        if self.docker_available and pod["container_id"]:
            try:
                container = self.docker_client.containers.get(pod["container_id"])
                stats = container.stats(stream=False)
                
                # Parse Docker stats
                cpu_usage = self._calculate_cpu_percent(stats)
                memory_usage = stats["memory_stats"]["usage"]
                memory_limit = stats["memory_stats"]["limit"]
                network_rx = stats["networks"]["eth0"]["rx_bytes"]
                network_tx = stats["networks"]["eth0"]["tx_bytes"]
                
                return {
                    "cpu_usage_percent": cpu_usage,
                    "memory_usage_bytes": memory_usage,
                    "memory_limit_bytes": memory_limit,
                    "memory_usage_percent": (memory_usage / memory_limit) * 100,
                    "network_rx_bytes": network_rx,
                    "network_tx_bytes": network_tx,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                print(f"Failed to get container stats: {e}")
        
        # Return mock metrics if Docker not available
        return {
            "cpu_usage_percent": 25.5,
            "memory_usage_bytes": 134217728,  # 128MB
            "memory_limit_bytes": 268435456,  # 256MB
            "memory_usage_percent": 50.0,
            "network_rx_bytes": 1024000,
            "network_tx_bytes": 512000,
            "timestamp": datetime.utcnow().isoformat(),
            "mock": True
        }
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU usage percentage from Docker stats"""
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
    
    async def health_check(self, pod_id: str) -> Dict:
        """Perform health check (simulates K8s readiness/liveness probes)"""
        if pod_id not in self.pods:
            return {"healthy": False, "reason": "Pod not found"}
        
        pod = self.pods[pod_id]
        
        if not pod["status"].ready:
            return {"healthy": False, "reason": "Pod not ready"}
        
        if self.docker_available and pod["container_id"]:
            try:
                container = self.docker_client.containers.get(pod["container_id"])
                container.reload()
                
                if container.status == "running":
                    # Simulate HTTP health check
                    return {
                        "healthy": True,
                        "status": container.status,
                        "health": "healthy",
                        "last_check": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "healthy": False,
                        "reason": f"Container status: {container.status}",
                        "last_check": datetime.utcnow().isoformat()
                    }
                    
            except Exception as e:
                return {"healthy": False, "reason": str(e)}
        
        # Mock health check
        return {
            "healthy": True,
            "status": "running",
            "health": "healthy",
            "last_check": datetime.utcnow().isoformat(),
            "mock": True
        }
    
    async def scale_deployment(self, deployment_name: str, replicas: int) -> Dict:
        """Scale deployment (simulates K8s Deployment scaling)"""
        if deployment_name not in self.deployments:
            return {"error": "Deployment not found"}
        
        deployment = self.deployments[deployment_name]
        current_replicas = len(deployment["pods"])
        
        if replicas > current_replicas:
            # Scale up
            for i in range(replicas - current_replicas):
                pod_spec = deployment["pod_spec"]
                pod_spec.name = f"{deployment_name}-{i+1}"
                pod = await self.create_pod(pod_spec)
                deployment["pods"].append(pod["id"])
                
        elif replicas < current_replicas:
            # Scale down
            pods_to_remove = deployment["pods"][replicas:]
            for pod_id in pods_to_remove:
                await self.delete_pod(pod_id)
            deployment["pods"] = deployment["pods"][:replicas]
        
        deployment["replicas"] = replicas
        
        return {
            "deployment": deployment_name,
            "old_replicas": current_replicas,
            "new_replicas": replicas,
            "pods": deployment["pods"]
        }
    
    async def delete_pod(self, pod_id: str):
        """Delete a pod"""
        if pod_id not in self.pods:
            return
        
        pod = self.pods[pod_id]
        
        # Stop and remove container if it exists
        if self.docker_available and pod["container_id"]:
            try:
                container = self.docker_client.containers.get(pod["container_id"])
                container.stop()
                container.remove()
            except Exception as e:
                print(f"Failed to remove container: {e}")
        
        # Remove pod
        del self.pods[pod_id]
    
    async def _broadcast_pod_status(self, pod_id: str):
        """Broadcast pod status update via WebSocket"""
        if pod_id not in self.pods:
            return
        
        pod = self.pods[pod_id]
        
        # This would broadcast to WebSocket clients
        # For now, we'll just store the status update
        status_update = {
            "type": "pod_status",
            "pod_id": pod_id,
            "pod_name": pod["name"],
            "status": pod["status"].phase,
            "ready": pod["status"].ready,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store for monitoring
        self.health_checks[pod_id] = status_update
    
    def get_cluster_status(self) -> Dict:
        """Get overall cluster status (like kubectl get pods)"""
        running_pods = sum(1 for pod in self.pods.values() if pod["status"].phase == "Running")
        total_pods = len(self.pods)
        
        return {
            "total_pods": total_pods,
            "running_pods": running_pods,
            "services": len(self.services),
            "deployments": len(self.deployments),
            "docker_available": self.docker_available,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global orchestrator instance
k8s_simulator = KubernetesSimulator()
