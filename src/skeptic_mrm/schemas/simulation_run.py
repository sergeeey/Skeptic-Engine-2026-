"""SimulationRun schema."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimulationRun:
    """Records a single simulation run for a material candidate."""

    run_id: str
    candidate_id: str
    backend: str  # "mattersim", "jaxmd", "dft_hook", etc.
    tier: int  # 0=heuristic, 1=ML atomistic, 2=expensive validation
    config_version: str
    status: str  # "completed", "failed", "timeout", "diverged"
    metrics: dict[str, float | bool] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)  # uri paths

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "backend": self.backend,
            "tier": self.tier,
            "config_version": self.config_version,
            "status": self.status,
            "metrics": dict(self.metrics),
            "artifacts": dict(self.artifacts),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SimulationRun":
        return cls(
            run_id=data["run_id"],
            candidate_id=data["candidate_id"],
            backend=data["backend"],
            tier=data["tier"],
            config_version=data["config_version"],
            status=data["status"],
            metrics=data.get("metrics", {}),
            artifacts=data.get("artifacts", {}),
        )
