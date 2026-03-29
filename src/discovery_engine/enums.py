from enum import Enum


class SourceType(str, Enum):
    PAPER = "paper"
    REVIEW = "review"
    PREPRINT = "preprint"
    PATENT = "patent"
    DATASET = "dataset"
    REPOSITORY = "repository"
    REPORT = "report"


class EvidenceStatus(str, Enum):
    FACT = "fact"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"
    UNKNOWN = "unknown"


class RiskTier(str, Enum):
    LOW_HANGING = "low_hanging"
    MEDIUM_RISK = "medium_risk"
    MOONSHOT = "moonshot"
