"""Map external API categories to project domains."""

from __future__ import annotations

# Project domains: biology, materials_science, control_information_theory, interdisciplinary

_DOMAIN_MAP: dict[str, str] = {
    # ---- bioRxiv categories ----
    "biochemistry": "biology",
    "bioinformatics": "biology",
    "biophysics": "biology",
    "cancer biology": "biology",
    "cell biology": "biology",
    "developmental biology": "biology",
    "ecology": "biology",
    "evolutionary biology": "biology",
    "genetics": "biology",
    "genomics": "biology",
    "immunology": "biology",
    "microbiology": "biology",
    "molecular biology": "biology",
    "neuroscience": "biology",
    "pharmacology and toxicology": "biology",
    "physiology": "biology",
    "plant biology": "biology",
    "synthetic biology": "biology",
    "systems biology": "control_information_theory",
    "bioengineering": "control_information_theory",
    # ---- Semantic Scholar fieldsOfStudy ----
    "biology": "biology",
    "medicine": "biology",
    "agricultural and food sciences": "biology",
    "environmental science": "biology",
    "chemistry": "materials_science",
    "materials science": "materials_science",
    "physics": "materials_science",
    "geology": "materials_science",
    "computer science": "control_information_theory",
    "engineering": "control_information_theory",
    "mathematics": "control_information_theory",
    # ---- Zenodo keywords (common) ----
    "dataset": "interdisciplinary",
    "software": "control_information_theory",
    "machine learning": "control_information_theory",
    "deep learning": "control_information_theory",
    "metal-organic framework": "materials_science",
    "mof": "materials_science",
    "polymer": "materials_science",
    "crystal": "materials_science",
    "catalyst": "materials_science",
    "genomics": "biology",
    "proteomics": "biology",
    "transcriptomics": "biology",
    "neuroscience": "biology",
}


def map_domain(categories: list[str]) -> str:
    """Return the best-matching project domain for a list of API categories.

    Returns the first match; falls back to ``"interdisciplinary"``.
    """
    for cat in categories:
        key = cat.strip().lower()
        if key in _DOMAIN_MAP:
            return _DOMAIN_MAP[key]
    return "interdisciplinary"
