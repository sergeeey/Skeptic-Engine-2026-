from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CandidateFamilyProfile:
    candidate_id: str
    family_name: str
    query_templates: tuple[str, ...]
    anchor_terms: tuple[str, ...]
    downgrade_terms: tuple[str, ...] = field(default_factory=tuple)


_PROFILES: dict[str, CandidateFamilyProfile] = {
    "H10": CandidateFamilyProfile(
        candidate_id="H10",
        family_name="mof_graph_benchmark",
        query_templates=(
            "MOF synthesizability graph neural network benchmark descriptor baseline",
            "MOF stability proxy benchmark CGCNN MOFormer solvent removal stability",
            "metal organic framework free energy synthesizability benchmark graph model",
        ),
        anchor_terms=(
            "mof",
            "metal-organic framework",
            "synthesizability",
            "solvent removal stability",
            "thermal stability",
            "graph neural network",
            "cgcnn",
            "moformer",
            "descriptor baseline",
        ),
        downgrade_terms=(
            "free energy",
            "benchmark",
            "stability proxy",
        ),
    ),
    "H4": CandidateFamilyProfile(
        candidate_id="H4",
        family_name="tda_cancer_resistance",
        query_templates=(
            "topological data analysis cancer drug resistance single cell transition",
            "persistent homology resistant state transition single-cell RNA-seq melanoma",
            "TDA oncology relapse prediction single-cell benchmark pseudotime velocity",
        ),
        anchor_terms=(
            "topological data analysis",
            "persistent homology",
            "single-cell",
            "drug resistance",
            "resistant state",
            "melanoma",
            "relapse",
            "pseudotime",
            "rna velocity",
        ),
        downgrade_terms=(
            "transition",
            "relapse prediction",
            "single-cell benchmark",
        ),
    ),
    "H20": CandidateFamilyProfile(
        candidate_id="H20",
        family_name="soc_degradation_topology",
        query_templates=(
            "persistent homology solid oxide cell degradation early warning microstructure",
            "SOC electrode degradation topology prediction persistence image microstructure",
            "solid oxide fuel cell persistent homology longitudinal degradation benchmark",
        ),
        anchor_terms=(
            "persistent homology",
            "solid oxide cell",
            "solid oxide fuel cell",
            "degradation",
            "electrode microstructure",
            "persistence image",
            "longitudinal",
            "early warning",
        ),
        downgrade_terms=(
            "microstructure prediction",
            "degradation characterization",
            "polarization curve",
        ),
    ),
    "H1": CandidateFamilyProfile(
        candidate_id="H1",
        family_name="koopman_llps_idp",
        query_templates=(
            "koopman operator LLPS intrinsically disordered protein trajectory",
            "VAMP MSM condensate dynamics intrinsically disordered protein phase separation",
            "slow mode analysis LLPS IDP molecular dynamics benchmark",
        ),
        anchor_terms=(
            "koopman",
            "vamp",
            "markov state model",
            "llps",
            "phase separation",
            "intrinsically disordered protein",
            "condensate dynamics",
            "trajectory",
        ),
        downgrade_terms=(
            "slow modes",
            "molecular kinetics",
            "trajectory benchmark",
        ),
    ),
    "H2": CandidateFamilyProfile(
        candidate_id="H2",
        family_name="glass_topology_benchmark",
        query_templates=(
            "persistent homology metallic glass cooling rate deformation benchmark",
            "topological descriptors metallic glass stress strain amorphous materials",
            "glass science persistent homology machine learning transition proxy benchmark",
        ),
        anchor_terms=(
            "persistent homology",
            "metallic glass",
            "cooling rate",
            "deformation",
            "stress strain",
            "amorphous materials",
            "transition proxy",
            "structural descriptors",
        ),
        downgrade_terms=(
            "glass science review",
            "machine learning",
            "mechanical properties",
        ),
    ),
}


def get_candidate_family_profile(candidate_id: str) -> CandidateFamilyProfile | None:
    return _PROFILES.get(candidate_id.upper())


def list_candidate_family_profiles() -> list[CandidateFamilyProfile]:
    return list(_PROFILES.values())
