"""DeploymentSource backed by a local JSON file listing releases — no CI/CD

vendor API, no network. This is the local adapter for the
`DeploymentSource` interface; a real deployment would swap in something
like a GitHub Actions or Argo Rollouts adapter satisfying the same
`Protocol` (see app/integrations/base.py).

Releases are read newest-first: shopmock's `data/deployments.json` (and
any adapter reading a similar append-style release log) appends each new
deployment to the end of the list.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.errors import NotFoundError
from app.integrations.types import DeploymentInfo


class LocalFileDeploymentSource:
    def __init__(self, deployments_path: str) -> None:
        self.deployments_path = Path(deployments_path).resolve()
        if not self.deployments_path.is_file():
            raise ValueError(f"{self.deployments_path} is not a file.")

    def _read_all(self) -> list[DeploymentInfo]:
        raw_list = json.loads(self.deployments_path.read_text(encoding="utf-8"))
        deployments = [
            DeploymentInfo(
                service=raw["service"],
                version=raw["version"],
                commit_sha=raw.get("commit_sha"),
                deployed_at=datetime.fromisoformat(raw["deployed_at"]),
                status=raw["status"],
            )
            for raw in raw_list
        ]
        deployments.sort(key=lambda d: d.deployed_at, reverse=True)
        return deployments

    async def get_deployment(self, version: str) -> DeploymentInfo:
        deployments = await asyncio.to_thread(self._read_all)
        for deployment in deployments:
            if deployment.version == version:
                return deployment
        raise NotFoundError(f"No deployment with version {version!r}.")

    async def list_releases(self, *, limit: int = 20) -> list[DeploymentInfo]:
        deployments = await asyncio.to_thread(self._read_all)
        return deployments[:limit]

    async def get_service_version(self) -> str:
        deployments = await asyncio.to_thread(self._read_all)
        if not deployments:
            raise NotFoundError("No deployments recorded — cannot determine current version.")
        return deployments[0].version
