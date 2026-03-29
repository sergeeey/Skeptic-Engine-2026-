"""Bridge-tag extraction from text via curated keyword dictionary."""

from __future__ import annotations

# Canonical bridge tags with trigger phrases (all lowercase).
BRIDGE_TAG_TRIGGERS: dict[str, list[str]] = {
    "control": [
        "control system",
        "control theory",
        "controller",
        "feedback control",
        "closed-loop",
        "pid control",
        "adaptive control",
        "robust control",
    ],
    "estimation": [
        "state estimation",
        "kalman filter",
        "bayesian inference",
        "parameter estimation",
        "particle filter",
        "observer design",
    ],
    "feedback": [
        "feedback loop",
        "feedback regulation",
        "negative feedback",
        "positive feedback",
        "homeostasis",
    ],
    "graph": [
        "graph neural",
        "graph network",
        "knowledge graph",
        "graph theory",
        "graph convolution",
        "message passing",
        "node classification",
    ],
    "information_theory": [
        "information theory",
        "entropy",
        "mutual information",
        "channel capacity",
        "information bottleneck",
        "rate-distortion",
    ],
    "optimization": [
        "optimization",
        "gradient descent",
        "evolutionary algorithm",
        "genetic algorithm",
        "bayesian optimization",
        "objective function",
    ],
    "topology": [
        "persistent homology",
        "topological data analysis",
        "betti number",
        "simplicial complex",
        "topological feature",
        "tda",
    ],
    "surrogates": [
        "surrogate model",
        "meta-model",
        "emulator",
        "proxy model",
        "reduced-order model",
    ],
    "mof": [
        "metal-organic framework",
        "mof ",
        "mofs ",
        "porous material",
        "reticular chemistry",
        "linker",
        "secondary building unit",
    ],
    "stability": [
        "thermal stability",
        "chemical stability",
        "phase stability",
        "solvent removal",
        "degradation",
        "decomposition temperature",
    ],
    "catalysis": [
        "catalysis",
        "catalyst",
        "catalytic",
        "enzymatic",
        "electrocatalysis",
    ],
    "self_assembly": [
        "self-assembly",
        "self-assembling",
        "spontaneous assembly",
        "supramolecular",
    ],
    "single_cell": [
        "single-cell",
        "single cell",
        "scrna-seq",
        "scrnaseq",
        "single-cell rna",
        "cell atlas",
    ],
    "drug_resistance": [
        "drug resistance",
        "antibiotic resistance",
        "antimicrobial resistance",
        "resistant strain",
        "multidrug resistant",
    ],
    "reinforcement_learning": [
        "reinforcement learning",
        "reward signal",
        "policy gradient",
        "q-learning",
        "multi-armed bandit",
    ],
    "transfer_learning": [
        "transfer learning",
        "domain adaptation",
        "fine-tuning",
        "pre-trained model",
        "foundation model",
    ],
    "llps": [
        "liquid-liquid phase separation",
        "llps",
        "phase separation",
        "condensate",
        "intrinsically disordered",
    ],
    "koopman": [
        "koopman operator",
        "koopman",
        "dynamic mode decomposition",
        "spectral analysis of dynamics",
    ],
}


def extract_bridge_tags(
    text: str,
    *,
    extra_keywords: list[str] | None = None,
) -> list[str]:
    """Return bridge tags matched from *text* via case-insensitive substring search.

    *extra_keywords* (e.g. API-provided keywords) are also checked.
    """
    combined = text.lower()
    if extra_keywords:
        combined = combined + " " + " ".join(kw.lower() for kw in extra_keywords)

    matched: list[str] = []
    for tag, triggers in BRIDGE_TAG_TRIGGERS.items():
        for trigger in triggers:
            if trigger in combined:
                matched.append(tag)
                break

    return sorted(set(matched))
