from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class K8sDeploymentConfig:
    name: str
    image: str
    port: int
    env: Dict[str, str]
    labels: Dict[str, str]
    namespace: str = "default"


def _run_kubectl(args: List[str], input_data: str | None = None) -> str:
    cmd = ["kubectl"] + args
    proc = subprocess.run(
        cmd,
        input=input_data.encode("utf-8") if input_data is not None else None,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"kubectl {' '.join(args)} failed: {proc.stderr.decode(errors='ignore')}")
    return proc.stdout.decode("utf-8")


def apply_manifest(yaml_str: str) -> None:
    """Apply a YAML manifest via `kubectl apply -f -`."""
    _run_kubectl(["apply", "-f", "-"], input_data=yaml_str)


def build_static_app_manifests(cfg: K8sDeploymentConfig) -> str:
    """Generate a minimal Deployment+Service manifest for a static web app container."""
    labels = {"app": cfg.name, **cfg.labels}
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": cfg.name, "namespace": cfg.namespace, "labels": labels},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": labels},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "containers": [
                        {
                            "name": cfg.name,
                            "image": cfg.image,
                            "ports": [{"containerPort": cfg.port}],
                            "env": [
                                {"name": k, "value": v}
                                for k, v in cfg.env.items()
                            ],
                        }
                    ]
                },
            },
        },
    }

    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": f"{cfg.name}-svc", "namespace": cfg.namespace, "labels": labels},
        "spec": {
            "selector": labels,
            "ports": [{"port": 80, "targetPort": cfg.port}],
            "type": "NodePort",
        },
    }

    # Simple multi-doc YAML using json + `---` separators (kubectl accepts this)
    return "---\n" + "\n---\n".join(
        json.dumps(obj, indent=2) for obj in (manifest, service)
    )


def deploy_static_app(cfg: K8sDeploymentConfig) -> Dict[str, Any]:
    """Generate and apply Deployment+Service for a static web app.

    Returns basic identifiers so callers can record them.
    """
    yaml_str = build_static_app_manifests(cfg)
    apply_manifest(yaml_str)

    node_port: int | None = None
    svc_name = f"{cfg.name}-svc"
    try:
        svc_json = _run_kubectl(
            [
                "get",
                "service",
                svc_name,
                "-o",
                "json",
                "-n",
                cfg.namespace,
            ]
        )
        svc = json.loads(svc_json or "{}")
        ports = (svc.get("spec", {}) or {}).get("ports", []) or []
        if ports:
            node_port = ports[0].get("nodePort")
    except Exception:
        node_port = None

    return {
        "namespace": cfg.namespace,
        "deployment_name": cfg.name,
        "service_name": svc_name,
        "labels": cfg.labels,
        "node_port": node_port,
    }


def get_cluster_snapshot(namespace: str | None = None) -> Dict[str, Any]:
    """Return a snapshot of pods, services, and deployments using kubectl JSON output."""
    ns_args = ["-n", namespace] if namespace else []

    def get(kind: str) -> List[Dict[str, Any]]:
        out = _run_kubectl(["get", kind, "-o", "json"] + ns_args)
        data = json.loads(out or "{}")
        return data.get("items", [])

    pods = get("pods")
    services = get("services")
    deployments = get("deployments")

    return {
        "pods": pods,
        "services": services,
        "deployments": deployments,
    }
