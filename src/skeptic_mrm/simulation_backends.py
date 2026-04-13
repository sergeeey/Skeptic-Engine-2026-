"""SE-MRM simulation backends — abstract interface + stubs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.schemas.simulation_run import SimulationRun


class ISimulationBackend(ABC):
    """Abstract interface for an atomistic simulation backend."""

    @abstractmethod
    def relax(self, candidate: MaterialCandidate, config: dict[str, Any] | None = None) -> SimulationRun:
        """Relax structure and return simulation run record."""

    @abstractmethod
    def simulate(
        self,
        candidate: MaterialCandidate,
        scenario: dict[str, Any],
    ) -> SimulationRun:
        """Run a simulation scenario (temperature ramp, pressure, etc.)."""

    @abstractmethod
    def supports(self) -> dict[str, Any]:
        """Return supported features (elements, temperature range, pressure range)."""


class MatterSimBackendStub(ISimulationBackend):
    """Stub for Microsoft MatterSim integration.

    MatterSim provides efficient atomistic simulations across elements,
    temperatures 0-5000 K and pressures up to 1000 GPa.

    Real integration requires:
    - pip install mattersim
    - model checkpoint
    - GPU recommended
    """

    def __init__(self) -> None:
        self._version = "mattersim-stub-0.1"
        self._run_counter = 0

    def relax(self, candidate: MaterialCandidate, config: dict[str, Any] | None = None) -> SimulationRun:
        self._run_counter += 1
        run_id = f"sim_{self._run_counter:06d}"
        return SimulationRun(
            run_id=run_id,
            candidate_id=candidate.candidate_id,
            backend="mattersim",
            tier=1,
            config_version=self._version,
            status="completed",
            metrics={
                "relaxation_converged": True,
                "energy_proxy": -2.13,
                "dynamic_stability_proxy": 0.71,
                "temperature_resilience": 0.63,
                "pressure_resilience": 0.58,
            },
            artifacts={"trajectory_uri": f"stub://traj/{run_id}.npz"},
        )

    def simulate(
        self,
        candidate: MaterialCandidate,
        scenario: dict[str, Any],
    ) -> SimulationRun:
        self._run_counter += 1
        run_id = f"sim_{self._run_counter:06d}"
        scenario_type = scenario.get("type", "unknown")
        return SimulationRun(
            run_id=run_id,
            candidate_id=candidate.candidate_id,
            backend="mattersim",
            tier=1,
            config_version=self._version,
            status="completed",
            metrics={
                "scenario_type": 0.0,  # encoded as float for type consistency
                "scenario_value": scenario.get("value", 0.0),
                "collapsed": 0.0,
                "property_drop": 0.05,
            },
            artifacts={"trajectory_uri": f"stub://traj/{run_id}.npz"},
        )

    def supports(self) -> dict[str, Any]:
        return {
            "name": "MatterSim",
            "version": self._version,
            "status": "stub",
            "elements": "all",
            "temperature_range_K": (0, 5000),
            "pressure_range_GPa": (0, 1000),
            "note": "Real integration requires mattersim package",
        }


class JaxMdBackendExperimental(ISimulationBackend):
    """Experimental JAX MD backend.

    JAX MD is a research project with possible API-breaking changes.
    This backend is marked experimental and should NOT be the default.

    See: https://github.com/jax-md/jax-md
    """

    def __init__(self) -> None:
        self._version = "jaxmd-experimental-0.1"
        self._run_counter = 0

    def relax(self, candidate: MaterialCandidate, config: dict[str, Any] | None = None) -> SimulationRun:
        self._run_counter += 1
        return SimulationRun(
            run_id=f"jaxmd_{self._run_counter:06d}",
            candidate_id=candidate.candidate_id,
            backend="jaxmd",
            tier=2,
            config_version=self._version,
            status="completed",
            metrics={"relaxation_converged": True, "energy_proxy": -1.87},
            artifacts={},
        )

    def simulate(
        self,
        candidate: MaterialCandidate,
        scenario: dict[str, Any],
    ) -> SimulationRun:
        self._run_counter += 1
        return SimulationRun(
            run_id=f"jaxmd_{self._run_counter:06d}",
            candidate_id=candidate.candidate_id,
            backend="jaxmd",
            tier=2,
            config_version=self._version,
            status="completed",
            metrics={"scenario_type": 0.0, "collapsed": 0.0},
            artifacts={},
        )

    def supports(self) -> dict[str, Any]:
        return {
            "name": "JAX MD",
            "version": self._version,
            "status": "experimental",
            "warning": "API may change without notice",
        }
