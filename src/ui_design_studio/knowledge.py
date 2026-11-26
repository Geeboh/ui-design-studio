"""Bounded, provenance-preserving selection of project knowledge rules."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


class KnowledgeError(ValueError):
    """Knowledge catalog is malformed or exceeds a selection bound."""


@dataclass(frozen=True)
class KnowledgeRule:
    rule_id: str
    topic: str
    principle: str
    applies_when: str
    action: str
    check: str
    authority: str
    source_ids: tuple[str, ...]
    source_locators: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.rule_id, "topic": self.topic, "principle": self.principle, "appliesWhen": self.applies_when, "action": self.action, "check": self.check, "authority": self.authority, "sourceIds": list(self.source_ids), "sourceLocators": self.source_locators}


def load_rules(path: str | Path) -> tuple[KnowledgeRule, ...]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schemaVersion") not in {"1.0", "1.0.0"} or not isinstance(value.get("rules"), list):
        raise KnowledgeError("knowledge catalog schema is unsupported")
    rules = []
    for item in value["rules"]:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip() for key in ("id", "topic", "principle", "appliesWhen", "action", "check", "authority")):
            raise KnowledgeError("knowledge rule is incomplete")
        sources = item.get("sourceIds", [])
        locators = item.get("sourceLocators", {})
        if not isinstance(sources, list) or not isinstance(locators, dict) or any(not isinstance(source, str) or not source.strip() for source in sources):
            raise KnowledgeError("knowledge provenance is malformed")
        if not sources and item["authority"] != "engineering-proposal":
            raise KnowledgeError("source-informed knowledge requires provenance")
        rules.append(KnowledgeRule(item["id"], item["topic"], item["principle"], item["appliesWhen"], item["action"], item["check"], item["authority"], tuple(sources), {str(key): str(value) for key, value in locators.items()}))
    return tuple(rules)


def select_rules(rules: tuple[KnowledgeRule, ...], query: str, *, limit: int = 8) -> list[KnowledgeRule]:
    if not isinstance(query, str) or not query.strip():
        raise KnowledgeError("knowledge query is required")
    if not isinstance(limit, int) or not 1 <= limit <= 32:
        raise KnowledgeError("knowledge selection limit must be between 1 and 32")
    terms = {term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2}
    ranked = []
    for rule in rules:
        haystack = " ".join((rule.topic, rule.principle, rule.applies_when, rule.action, rule.check)).lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            ranked.append((score, rule.rule_id, rule))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[:limit]]
