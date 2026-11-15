"""Agent 02 — Audience Research Agent: personas + content opportunities."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..models import AudiencePersona, PlatformMetric, ResearchReport
from ..ai.content_engine import TOPICS
from .base import BaseAgent, register


@register
class AudienceAgent(BaseAgent):
    key = "audience"
    name = "Audience Research Agent"
    role = "Resears developmental-psychology interests, student/parent/educator needs, demographics, FAQs, trends; builds personas."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        metrics = db.query(PlatformMetric).filter(PlatformMetric.date >= since).all()
        followers = sum(m.followers for m in metrics)
        engagements = sum(m.likes + m.comments + m.shares + m.saves for m in metrics)

        personas = [
            {"name": "Curious Parent", "segment": "parents", "demographics": "25-40, caregivers of 0-12",
             "interests": ["milestones", "toddler behaviour", "sleep", "language"],
             "pain_points": ["developmental worry", "screen time", "tantrums"],
             "content_hooks": ["Is my child on track?", "What to do when..."]},
            {"name": "Classroom Educator", "segment": "educators", "demographics": "teachers, preschool-primary",
             "interests": ["learning theories", "scaffolding", "classroom management"],
             "pain_points": ["differentiation", "engagement", "behaviour support"],
             "content_hooks": ["Evidence-based teaching tips", "Psych 101 for class"]},
            {"name": "Psychology Student", "segment": "students", "demographics": "16-25, A-level/undergrad",
             "interests": ["theories", "studies", "exam prep", "research methods"],
             "pain_points": ["jargon", "exam recall", "applying studies"],
             "content_hooks": ["60-second explainers", "Study breakdowns"]},
            {"name": "Lifelong Learner", "segment": "enthusiasts", "demographics": "25-60, general interest",
             "interests": ["teen brain", "aging", "memory", "wellbeing"],
             "pain_points": ["myth-busting", "accessible science"],
             "content_hooks": ["Myth vs science", "Brain facts"]},
        ]
        for p in personas:
            row = db.query(AudiencePersona).filter_by(name=p["name"]).first()
            if row is None:
                db.add(AudiencePersona(name=p["name"], segment=p["segment"], demographics=p["demographics"],
                                       interests=p["interests"], pain_points=p["pain_points"], content_hooks=p["content_hooks"]))

        report = {
            "audience_size_signal": followers,
            "engagement_signal_30d": engagements,
            "personas": len(personas),
            "top_interests": [t["title"] for t in TOPICS[:5]],
            "faq_seeds": [
                "When do babies get object permanence?",
                "What is the zone of proximal development?",
                "How do I support emotional regulation in toddlers?",
                "What are the parenting styles and outcomes?",
            ],
            "method": "Offline deterministic engine using lawful aggregate platform metrics + established literature themes. No individual tracking.",
        }
        db.add(ResearchReport(title="Audience research digest", kind="audience", topic="Developmental psychology audiences",
                              summary="Personas refreshed; interests, pain points and FAQ seeds generated.",
                              data=report, source="audience_agent"))
        return {"status": "done", "personas": len(personas), "engagement_30d": engagements}
