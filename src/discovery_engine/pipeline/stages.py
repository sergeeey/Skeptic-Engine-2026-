from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StageContract:
    name: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]


PIPELINE_STAGES: tuple[StageContract, ...] = (
    StageContract(
        name="acquisition",
        purpose="Collect candidate sources from selected domains.",
        inputs=("domain briefs", "seed queries", "source manifests"),
        outputs=("raw source manifests",),
    ),
    StageContract(
        name="dqops",
        purpose="Deduplicate and score sources for authority, bias, freshness, and relevance.",
        inputs=("raw source manifests",),
        outputs=("normalized source records", "discard log"),
    ),
    StageContract(
        name="semantic_core",
        purpose="Extract entities, mechanisms, methods, limitations, and unresolved phenomena.",
        inputs=("normalized source records",),
        outputs=("ontology graph", "cross-domain candidate links"),
    ),
    StageContract(
        name="hypothesis_generation",
        purpose="Generate structured candidate hypotheses from evidence-backed links.",
        inputs=("ontology graph", "cross-domain candidate links"),
        outputs=("candidate hypothesis cards",),
    ),
    StageContract(
        name="skeptic",
        purpose="Downgrade banal, weak, or already-known candidates.",
        inputs=("candidate hypothesis cards",),
        outputs=("challenged hypothesis cards",),
    ),
    StageContract(
        name="arbiter",
        purpose="Rank hypotheses and promote the strongest shortlist.",
        inputs=("challenged hypothesis cards",),
        outputs=("ranked shortlist", "top-5 board"),
    ),
    StageContract(
        name="validation_design",
        purpose="Attach Python-first experiments and falsification tests.",
        inputs=("top-5 board",),
        outputs=("validation plans", "execution backlog"),
    ),
)
