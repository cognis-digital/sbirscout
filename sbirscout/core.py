"""Core engine for SBIRSCOUT.

The data model is a normalized ``Topic`` regardless of source agency. The
scoring engine is a deterministic, explainable weighted model that combines:

  * keyword/capability match against the topic text
  * phase fit (firm preference vs. solicitation phase)
  * funding attractiveness (award ceiling, normalized)
  * deadline urgency (days remaining, bucketed)
  * STTR research-partner requirement penalty (if firm has no partner)

All weights are explicit so a bid/no-bid decision can be audited.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Recognized normalized source identifiers and their canonical agency labels.
SOURCES: Dict[str, str] = {
    "dsip": "DoD SBIR/STTR (DSIP)",
    "sbir_gov": "SBIR.gov (cross-agency)",
    "nih": "NIH/HHS",
}

_SOURCE_ALIASES = {
    "dod": "dsip",
    "defense": "dsip",
    "dsip": "dsip",
    "sbir.gov": "sbir_gov",
    "sbir_gov": "sbir_gov",
    "sbirgov": "sbir_gov",
    "sba": "sbir_gov",
    "nih": "nih",
    "hhs": "nih",
}

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-\+/]*")

# Phases the firm might prefer; normalized to a small set.
_VALID_PHASES = {"I", "II", "III", "DIRECT_II"}


def normalize_source(raw: str) -> str:
    """Map a free-form source string to a canonical SOURCES key."""
    if not raw:
        return "sbir_gov"
    key = re.sub(r"[^a-z0-9_.]", "", raw.strip().lower())
    return _SOURCE_ALIASES.get(key, key if key in SOURCES else "sbir_gov")


def _normalize_phase(raw: Any) -> str:
    s = str(raw or "").strip().upper().replace("PHASE", "").strip()
    s = s.replace(" ", "_").replace("DIRECT_TO_II", "DIRECT_II")
    s = {"1": "I", "2": "II", "3": "III"}.get(s, s)
    return s if s in _VALID_PHASES else "I"


def _tokens(text: str) -> List[str]:
    return _WORD_RE.findall((text or "").lower())


@dataclass
class Topic:
    """A normalized solicitation topic from any source."""

    topic_id: str
    title: str
    agency: str = ""
    source: str = "sbir_gov"
    program: str = "SBIR"  # SBIR or STTR
    phase: str = "I"
    keywords: List[str] = field(default_factory=list)
    description: str = ""
    award_ceiling: float = 0.0
    close_date: Optional[str] = None  # ISO YYYY-MM-DD
    url: str = ""

    def __post_init__(self) -> None:
        self.source = normalize_source(self.source)
        self.program = "STTR" if str(self.program).upper().strip() == "STTR" else "SBIR"
        self.phase = _normalize_phase(self.phase)
        self.keywords = [k.strip().lower() for k in self.keywords if str(k).strip()]
        try:
            self.award_ceiling = float(self.award_ceiling or 0.0)
        except (TypeError, ValueError):
            self.award_ceiling = 0.0

    def text_blob(self) -> str:
        return " ".join([self.title, self.description, " ".join(self.keywords)])

    def days_until_close(self, today: Optional[date] = None) -> Optional[int]:
        if not self.close_date:
            return None
        try:
            d = datetime.strptime(self.close_date, "%Y-%m-%d").date()
        except ValueError:
            return None
        return (d - (today or date.today())).days


@dataclass
class CapabilityProfile:
    """The bidding firm's capabilities and preferences."""

    capabilities: List[str] = field(default_factory=list)
    preferred_phases: List[str] = field(default_factory=lambda: ["I"])
    has_research_partner: bool = False  # required for STTR
    min_award: float = 0.0

    def __post_init__(self) -> None:
        self.capabilities = [c.strip().lower() for c in self.capabilities if str(c).strip()]
        self.preferred_phases = [_normalize_phase(p) for p in self.preferred_phases] or ["I"]


@dataclass
class ScoredTopic:
    topic: Topic
    score: float
    components: Dict[str, float]
    reasons: List[str]
    bid_recommendation: str  # GO / CONSIDER / PASS

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self.topic)
        d.update(
            {
                "score": round(self.score, 2),
                "components": {k: round(v, 2) for k, v in self.components.items()},
                "reasons": self.reasons,
                "bid_recommendation": self.bid_recommendation,
            }
        )
        return d


# Scoring weights (sum of positive caps ~= 100). Kept explicit for auditability.
_W_MATCH = 50.0
_W_PHASE = 15.0
_W_FUNDING = 20.0
_W_URGENCY = 15.0
_PARTNER_PENALTY = 40.0


def _match_score(topic: Topic, profile: CapabilityProfile) -> tuple[float, List[str]]:
    if not profile.capabilities:
        return 0.0, []
    blob_tokens = set(_tokens(topic.text_blob()))
    matched: List[str] = []
    for cap in profile.capabilities:
        cap_tokens = _tokens(cap)
        if not cap_tokens:
            continue
        # A capability hits if all of its tokens appear in the topic blob.
        if all(t in blob_tokens for t in cap_tokens):
            matched.append(cap)
    frac = len(matched) / len(profile.capabilities)
    return frac * _W_MATCH, matched


def _phase_score(topic: Topic, profile: CapabilityProfile) -> float:
    return _W_PHASE if topic.phase in profile.preferred_phases else 0.0


def _funding_score(topic: Topic) -> float:
    # Normalize against a typical $2M Phase II ceiling; cap at full weight.
    if topic.award_ceiling <= 0:
        return 0.0
    frac = min(topic.award_ceiling / 2_000_000.0, 1.0)
    return frac * _W_FUNDING


def _urgency_score(days: Optional[int]) -> tuple[float, str]:
    if days is None:
        return _W_URGENCY * 0.5, "no close date"
    if days < 0:
        return 0.0, f"closed {abs(days)}d ago"
    if days <= 7:
        return _W_URGENCY * 0.4, f"closes in {days}d (tight)"
    if days <= 30:
        return _W_URGENCY, f"closes in {days}d (actionable)"
    if days <= 90:
        return _W_URGENCY * 0.7, f"closes in {days}d"
    return _W_URGENCY * 0.4, f"closes in {days}d (distant)"


def score_topic(
    topic: Topic, profile: CapabilityProfile, today: Optional[date] = None
) -> ScoredTopic:
    """Compute an explainable bid-fit score for one topic."""
    reasons: List[str] = []
    components: Dict[str, float] = {}

    match_pts, matched = _match_score(topic, profile)
    components["capability_match"] = match_pts
    if matched:
        reasons.append("matches: " + ", ".join(sorted(matched)))
    else:
        reasons.append("no capability keywords matched")

    phase_pts = _phase_score(topic, profile)
    components["phase_fit"] = phase_pts
    if phase_pts:
        reasons.append(f"phase {topic.phase} preferred")
    else:
        reasons.append(f"phase {topic.phase} not preferred")

    fund_pts = _funding_score(topic)
    components["funding"] = fund_pts
    if topic.award_ceiling:
        reasons.append(f"ceiling ${topic.award_ceiling:,.0f}")

    days = topic.days_until_close(today)
    urg_pts, urg_reason = _urgency_score(days)
    components["urgency"] = urg_pts
    reasons.append(urg_reason)

    penalty = 0.0
    if topic.program == "STTR" and not profile.has_research_partner:
        penalty = _PARTNER_PENALTY
        reasons.append("STTR requires research partner (none on file)")
    components["sttr_partner_penalty"] = -penalty

    below_min = topic.award_ceiling and profile.min_award and topic.award_ceiling < profile.min_award
    if below_min:
        reasons.append("below firm min award")

    raw = match_pts + phase_pts + fund_pts + urg_pts - penalty
    score = max(0.0, min(100.0, raw))

    if days is not None and days < 0:
        rec = "PASS"
    elif below_min:
        rec = "PASS"
    elif score >= 60 and match_pts >= _W_MATCH * 0.4:
        rec = "GO"
    elif score >= 35:
        rec = "CONSIDER"
    else:
        rec = "PASS"

    return ScoredTopic(topic, score, components, reasons, rec)


def score_topics(
    topics: Iterable[Topic],
    profile: CapabilityProfile,
    today: Optional[date] = None,
) -> List[ScoredTopic]:
    scored = [score_topic(t, profile, today) for t in topics]
    scored.sort(key=lambda s: (-s.score, s.topic.days_until_close(today) or 9999))
    return scored


def parse_topics(raw: Any) -> List[Topic]:
    """Build Topic objects from parsed JSON (dict with 'topics' or a list)."""
    if isinstance(raw, dict):
        items = raw.get("topics", [])
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("input must be a JSON object with 'topics' or a JSON list")
    topics: List[Topic] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise ValueError(f"topic #{i} is not an object")
        topics.append(
            Topic(
                topic_id=str(it.get("topic_id") or it.get("id") or f"T{i+1}"),
                title=str(it.get("title") or ""),
                agency=str(it.get("agency") or ""),
                source=str(it.get("source") or "sbir_gov"),
                program=str(it.get("program") or "SBIR"),
                phase=it.get("phase", "I"),
                keywords=list(it.get("keywords") or []),
                description=str(it.get("description") or ""),
                award_ceiling=it.get("award_ceiling", 0),
                close_date=it.get("close_date"),
                url=str(it.get("url") or ""),
            )
        )
    return topics


def load_topics(path: str) -> List[Topic]:
    with open(path, "r", encoding="utf-8") as fh:
        return parse_topics(json.load(fh))


def _profile_from_raw(raw: Any) -> CapabilityProfile:
    if isinstance(raw, dict):
        return CapabilityProfile(
            capabilities=list(raw.get("capabilities") or []),
            preferred_phases=list(raw.get("preferred_phases") or ["I"]),
            has_research_partner=bool(raw.get("has_research_partner", False)),
            min_award=float(raw.get("min_award") or 0.0),
        )
    return CapabilityProfile(capabilities=list(raw or []))


def digest(
    topics: Sequence[Topic],
    profile: CapabilityProfile,
    today: Optional[date] = None,
    top: Optional[int] = None,
) -> Dict[str, Any]:
    """Produce a full ranked digest with per-source and recommendation rollups."""
    scored = score_topics(topics, profile, today)
    if top:
        scored = scored[:top]
    by_source: Dict[str, int] = {}
    by_rec: Dict[str, int] = {"GO": 0, "CONSIDER": 0, "PASS": 0}
    for s in scored:
        label = SOURCES.get(s.topic.source, s.topic.source)
        by_source[label] = by_source.get(label, 0) + 1
        by_rec[s.bid_recommendation] = by_rec.get(s.bid_recommendation, 0) + 1
    return {
        "tool": "sbirscout",
        "generated": (today or date.today()).isoformat(),
        "total_topics": len(scored),
        "by_source": by_source,
        "by_recommendation": by_rec,
        "topics": [s.to_dict() for s in scored],
    }
