"""SBIRSCOUT - SBIR/STTR topic discovery with bid scoring.

Aggregates and normalizes SBIR/STTR solicitation topics from multiple
federal sources (DoD DSIP, SBIR.gov, NIH) into a single digest, then
ranks them against a firm's capability profile using a transparent,
explainable bid-fit score.

Standard library only. Zero install. No network required for core scoring.
"""
from .core import (
    Topic,
    CapabilityProfile,
    ScoredTopic,
    load_topics,
    parse_topics,
    score_topic,
    score_topics,
    digest,
    normalize_source,
    SOURCES,
)

TOOL_NAME = "sbirscout"
TOOL_VERSION = "1.0.0"

__all__ = [
    "Topic",
    "CapabilityProfile",
    "ScoredTopic",
    "load_topics",
    "parse_topics",
    "score_topic",
    "score_topics",
    "digest",
    "normalize_source",
    "SOURCES",
    "TOOL_NAME",
    "TOOL_VERSION",
]
