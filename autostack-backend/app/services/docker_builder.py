from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path


def build_static_site_image(artifacts_dir: Path, deployment_id: uuid.UUID) -> str:
    """Build a simple nginx-based Docker image serving the deployment artifacts."""
    if shutil.which("docker") is None:
        raise RuntimeError("Docker CLI not available on host")

    image_tag = f"autostack-deployment-{deployment_id}".lower()
    dockerfile_path = artifacts_dir / ".autostack.Dockerfile"
    dockerfile_path.write_text(
        "\n".join(
            [
                "FROM nginx:alpine",
                "COPY . /usr/share/nginx/html",
            ]
        )
    )

    try:
        subprocess.run(
            ["docker", "build", "-t", image_tag, "-f", str(dockerfile_path), str(artifacts_dir)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime dependent
        stdout = exc.stdout.decode(errors="ignore") if exc.stdout else ""
        stderr = exc.stderr.decode(errors="ignore") if exc.stderr else ""
        raise RuntimeError(stderr or stdout or "docker build failed") from exc
    finally:
        if dockerfile_path.exists():
            dockerfile_path.unlink()

    return image_tag
