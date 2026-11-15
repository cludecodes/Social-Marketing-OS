"""Agent 04 — Educational Psychology Research Agent: scientifically responsible content."""
from __future__ import annotations

from datetime import datetime

from ..models import ContentIdea, ResearchReport
from ..ai.content_engine import TOPICS, topic_by_id, CITATIONS_KB, claim_safety_check
from .base import BaseAgent, register


@register
class ResearchAgent(BaseAgent):
    key = "research"
    name = "Educational Psychology Research Agent"
    role = "Produces scientifically responsible educational content: distinguishes evidence levels, uses only real classic citations, never diagnoses."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        topic_id = payload.get("topic_id") or TOPICS[0]["id"]
        topic = topic_by_id(topic_id)
        evidence = topic["evidence"]
        claims = [topic["fact"]]
        issues = []
        for c in claims:
            issues += claim_safety_check(c)
        citation_used = next((c for c in CITATIONS_KB if topic["domain"].split()[0].lower() in c.lower()), CITATIONS_KB[0])
        report = {
            "topic": topic["title"],
            "domain": topic["domain"],
            "evidence_level": evidence,
            "claims": claims,
            "safety_flags": issues,
            "citation": citation_used,
            "disclaimer": "Educational content only; not diagnosis, treatment, or medical advice. Consult a qualified professional for individual concerns.",
            "method": "Curated classic literature only; no invented studies or fabricated DOIs.",
            "generated_at": datetime.utcnow().isoformat(),
        }
        db.add(ResearchReport(title=f"Research brief: {topic['title']}", kind="education", topic=topic["title"],
                              summary=f"Evidence level: {evidence}. {len(claims)} claim(s) screened; {len(issues)} safety flag(s).",
                              data=report, source="research_agent"))
        # Link to matching idea if present
        idea = db.query(ContentIdea).filter(ContentIdea.topic == topic["title"]).first()
        if idea:
            idea.status = "researched"
        if issues:
            self.alert("warning", "Research claim safety flags", "; ".join(issues))
        return {"status": "done", "topic": topic["title"], "evidence_level": evidence, "safety_flags": issues}
