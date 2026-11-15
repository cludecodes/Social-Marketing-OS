"""Deterministic offline content engine for Developmental Psychology education.

Used when no AI provider key is configured AND as the structured fallback for
every agent. Knowledge base contains only well-established, classic findings
(Piaget, Vygotsky, Erikson, Ainsworth, Bandura, Baumrind, CDC/WHO milestone
frameworks). No invented citations, no fabricated studies, no diagnosis.
"""
from __future__ import annotations

import hashlib
import random
import re
from datetime import datetime, timedelta

BRAND_FALLBACK = "MindGrove Academy"

TOPICS = [
    {"id": "sensorimotor", "title": "Sensorimotor stage (0–2 years)", "domain": "Cognitive development",
     "fact": "Piaget described how infants build knowledge through senses and actions; object permanence emerges around 8 months.",
     "evidence": "established theory", "audience": ["parents", "educators"], "formats": ["infographic", "carousel", "pin", "reel"]},
    {"id": "object_permanence", "title": "Object permanence", "domain": "Cognitive development",
     "fact": "Object permanence — knowing things exist when out of sight — typically develops between 4 and 8 months.",
     "evidence": "established research", "audience": ["parents"], "formats": ["infographic", "reel", "post"]},
    {"id": "zpd", "title": "Zone of proximal development", "domain": "Learning theories",
     "fact": "Vygotsky's ZPD describes what a learner can do with guidance but not yet alone; scaffolding bridges the gap.",
     "evidence": "established theory", "audience": ["educators", "students"], "formats": ["carousel", "infographic", "video"]},
    {"id": "scaffolding", "title": "Scaffolding in learning", "domain": "Learning theories",
     "fact": "Scaffolding breaks tasks into steps with support that fades as competence grows.",
     "evidence": "established theory", "audience": ["educators", "parents"], "formats": ["carousel", "guide", "post"]},
    {"id": "attachment", "title": "Attachment styles in infants", "domain": "Attachment theory",
     "fact": "Ainsworth's Strange Situation identified secure, avoidant, ambivalent and disorganized attachment patterns.",
     "evidence": "established research", "audience": ["parents", "students"], "formats": ["infographic", "carousel", "video"]},
    {"id": "secure_base", "title": "Secure base effect", "domain": "Attachment theory",
     "fact": "A reliable caregiver acts as a secure base from which children explore the world.",
     "evidence": "established research", "audience": ["parents"], "formats": ["quote", "post", "pin"]},
    {"id": "erikkson", "title": "Erikson's psychosocial stages", "domain": "Lifespan psychology",
     "fact": "Erikson proposed eight psychosocial stages, each with a central conflict from infancy to old age.",
     "evidence": "established theory", "audience": ["students", "enthusiasts"], "formats": ["carousel", "infographic", "video"]},
    {"id": "theory_of_mind", "title": "Theory of mind", "domain": "Cognitive development",
     "fact": "Children usually begin passing false-belief tasks around age 4–5, showing they understand others can hold different beliefs.",
     "evidence": "established research", "audience": ["parents", "educators", "students"], "formats": ["infographic", "reel", "post"]},
    {"id": "language", "title": "Language development milestones", "domain": "Language development",
     "fact": "Most children say first words around 12 months and two-word phrases by 24 months; ranges vary widely.",
     "evidence": "established milestone framework", "audience": ["parents"], "formats": ["infographic", "guide", "pin"]},
    {"id": "executive_function", "title": "Executive function in childhood", "domain": "Cognitive development",
     "fact": "Working memory, inhibition and cognitive flexibility develop through childhood and predict school readiness.",
     "evidence": "established research", "audience": ["educators", "parents"], "formats": ["carousel", "guide", "video"]},
    {"id": "adolescent_brain", "title": "Adolescent brain development", "domain": "Adolescent psychology",
     "fact": "The prefrontal cortex keeps maturing into the mid-20s, which helps explain teen risk-taking and reward sensitivity.",
     "evidence": "established research", "audience": ["parents", "educators", "students"], "formats": ["infographic", "reel", "video"]},
    {"id": "growth_mindset", "title": "Growth mindset", "domain": "Learning theories",
     "fact": "Praise for effort and strategy, rather than fixed ability, supports persistence (Dweck's research line).",
     "evidence": "established research", "audience": ["parents", "educators"], "formats": ["quote", "carousel", "post"]},
    {"id": "social_learning", "title": "Social learning theory", "domain": "Learning theories",
     "fact": "Bandura showed children learn behaviours by observing others (Bobo doll experiments).",
     "evidence": "established research", "audience": ["students", "educators"], "formats": ["video", "carousel", "post"]},
    {"id": "parenting_styles", "title": "Parenting styles and outcomes", "domain": "Parenting and education",
     "fact": "Baumrind described authoritative, authoritarian, permissive and uninvolved styles; authoritative is linked to better outcomes on average.",
     "evidence": "established research", "audience": ["parents", "students"], "formats": ["infographic", "carousel", "guide"]},
    {"id": "play", "title": "The role of play", "domain": "Child development",
     "fact": "Play supports language, self-regulation and social skills; guided play is a powerful teaching tool.",
     "evidence": "established research", "audience": ["parents", "educators"], "formats": ["post", "pin", "carousel"]},
    {"id": "emotional_regulation", "title": "Emotional regulation in toddlers", "domain": "Emotional development",
     "fact": "Toddlers learn regulation through co-regulation: a calm adult helps the child return to baseline.",
     "evidence": "established research", "audience": ["parents"], "formats": ["reel", "infographic", "post"]},
    {"id": "temperament", "title": "Temperament differences", "domain": "Child development",
     "fact": "Children show stable temperament traits (easy, difficult, slow-to-warm-up) from early infancy.",
     "evidence": "established research", "audience": ["parents", "educators"], "formats": ["post", "carousel"]},
    {"id": "concrete_operational", "title": "Concrete operational stage (7–11)", "domain": "Cognitive development",
     "fact": "Children master conservation, classification and seriation during Piaget's concrete operational stage.",
     "evidence": "established theory", "audience": ["educators", "students"], "formats": ["infographic", "video"]},
    {"id": "formal_operational", "title": "Formal operational thought", "domain": "Cognitive development",
     "fact": "Abstract, hypothetical reasoning emerges around age 12 in Piaget's framework, though timing varies across cultures and tasks.",
     "evidence": "established theory", "audience": ["educators", "students"], "formats": ["carousel", "video"]},
    {"id": "bilingualism", "title": "Bilingualism and development", "domain": "Language development",
     "fact": "Raising bilingual children supports cognitive flexibility; code-mixing is normal, not confusion.",
     "evidence": "established research", "audience": ["parents", "educators"], "formats": ["post", "carousel", "guide"]},
    {"id": "grief_aging", "title": "Development across the lifespan", "domain": "Adult development",
     "fact": "Development continues after childhood: adulthood involves generativity, wisdom research, and changing cognition with age.",
     "evidence": "established theory", "audience": ["enthusiasts", "students"], "formats": ["video", "carousel", "post"]},
    {"id": "observational_learning", "title": "Modeling and imitation", "domain": "Learning theories",
     "fact": "Children imitate observed adult behaviour, including media models — consistent with social learning theory.",
     "evidence": "established research", "audience": ["parents", "educators"], "formats": ["reel", "post"]},
    {"id": "sleep_development", "title": "Sleep and child development", "domain": "Child development",
     "fact": "Consistent sleep routines support memory consolidation and emotional regulation in children.",
     "evidence": "established research", "audience": ["parents"], "formats": ["infographic", "guide", "pin"]},
    {"id": "math_anxiety", "title": "Math anxiety in students", "domain": "Adolescent psychology",
     "fact": "Math anxiety is common and workable: low-stakes practice and strategy focus reduce it.",
     "evidence": "established research", "audience": ["educators", "parents"], "formats": ["carousel", "post"]},
    {"id": "peer_relations", "title": "Friendship and social development", "domain": "Social development",
     "fact": "Friendships teach negotiation, empathy and conflict repair — key social skills in middle childhood.",
     "evidence": "established research", "audience": ["parents", "educators"], "formats": ["post", "carousel"]},
    {"id": "adverse_childhood", "title": "ACEs and resilience", "domain": "Emotional development",
     "fact": "Adverse childhood experiences are linked to later health risks; stable relationships buffer stress (resilience research).",
     "evidence": "established research", "audience": ["educators", "parents"], "formats": ["guide", "video", "post"]},
]

PLATFORM_RULES = {
    "instagram": {"caption_max": 2200, "hashtags": 8, "style": "warm, hook first, line breaks, emoji sparingly"},
    "facebook": {"caption_max": 600, "hashtags": 3, "style": "conversational, question at end"},
    "pinterest": {"caption_max": 500, "hashtags": 5, "style": "SEO keywords, descriptive, no hype"},
    "youtube": {"caption_max": 5000, "hashtags": 5, "style": "title hook, description with chapters"},
    "threads": {"caption_max": 500, "hashtags": 3, "style": "punchy, thread-style, one idea"},
    "linkedin": {"caption_max": 1300, "hashtags": 5, "style": "professional, educator angle"},
    "x": {"caption_max": 280, "hashtags": 2, "style": "terse, single punchline"},
    "tiktok": {"caption_max": 300, "hashtags": 4, "style": "short hook, trend-aware"},
}

HASHTAG_POOLS = {
    "developmentalpsychology": ["developmentalpsychology", "childdevelopment", "psychologyfacts", "parentingtips", "earlyeducation"],
    "education": ["edutok", "teachersofinstagram", "psychologyeducation", "learnpsychology", "educationmatters"],
    "parenting": ["parentingscience", "gentleparenting", "toddlerlife", "parenting101", "mindfulparenting"],
    "students": ["psychologystudent", "alevelpsychology", "appsychology", "psychologymcq", "studemment"],
    "research": ["evidencebased", "psychologyresearch", "scienceoflearning", "developmentalscience"],
}

CLAIM_BAN = ["cure", "guaranteed", "instantly fix", "diagnose", "your child is", "all children", "never", "always makes", "proven to make"]
SAFE_PHRASES = ["on average", "research suggests", "evidence indicates", "typically", "in studies", "tends to", "can support", "one framework"]

CITATIONS_KB = [
    "Piaget, J. (1952). The Origins of Intelligence in Children.",
    "Vygotsky, L. S. (1978). Mind in Society.",
    "Erikson, E. H. (1950). Childhood and Society.",
    "Ainsworth, M. D. S., et al. (1978). Patterns of Attachment.",
    "Bandura, A., Ross, D., & Ross, S. A. (1961). Transmission of aggression through imitation of aggressive models. Journal of Abnormal and Social Psychology.",
    "Baumrind, D. (1966). Effects of authoritative parental control on child behavior. Child Development.",
    "Dweck, C. S. (2006). Mindset: The New Psychology of Success.",
    "Wimmer, H., & Perner, J. (1983). Beliefs about beliefs: Representation and constraining function of wrong beliefs in young children's understanding of deception. Cognition.",
    "Blakemore, S.-J. (2018). Inventing Ourselves: The Secret Life of the Teenage Brain.",
    "CDC. (2024). Developmental Milestones (CDC's Act Early).",
]


def topic_by_id(tid: str) -> dict:
    for t in TOPICS:
        if t["id"] == tid:
            return t
    raise KeyError(tid)


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def pick_topics(count: int = 5, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed if seed is not None else int(datetime.utcnow().timestamp()))
    pool = list(TOPICS)
    rng.shuffle(pool)
    return pool[:count]


def headline(topic: dict, variant: int = 0) -> str:
    hooks = [
        f"{topic['title']}: what the research actually says",
        f"{topic['title']} — explained in 60 seconds",
        f"Why {topic['title'].lower()} matters more than you think",
        f"{topic['title']}: a no-jargon guide",
        f"3 things to know about {topic['title'].lower()}",
    ]
    return hooks[variant % len(hooks)]


def caption_for(platform: str, topic: dict, variant: int = 0) -> str:
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["instagram"])
    base = topic["fact"]
    opens = [
        f"{topic['title']}",
        f"Quick explainer: {topic['title'].lower()}",
        f"Parents & educators: {topic['title'].lower()}",
        f"Psych 101: {topic['title'].lower()}",
    ]
    ctas = {
        "instagram": ["Save this for later.", "Share with a parent who needs this.", "Follow for daily psych science."],
        "facebook": ["What questions do you have? Ask below.", "Tag a parent or teacher who would find this useful.", "Share if this helped."],
        "pinterest": [f"Save this guide for later. {topic['domain']} resources.", "Bookmark for your classroom or parenting toolkit."],
        "youtube": ["Watch the full explainer on the channel.", "Subscribe for weekly developmental psych videos."],
        "threads": ["Agree? Repost.", "Add your experience below."],
        "linkedin": ["How do you apply this in your classroom or practice?", "Follow for evidence-based education content."],
        "x": ["Repost if useful.", "Save this thread."],
        "tiktok": ["Follow for more 60-second psych lessons.", "Comment your question."],
    }
    open_line = opens[variant % len(opens)]
    cta_list = ctas.get(platform, ctas["instagram"])
    cta = cta_list[variant % len(cta_list)]
    caption = f"{open_line}\n\n{base}\n\n{cta}"
    if platform in ("instagram", "facebook", "youtube", "linkedin", "pinterest"):
        caption += "\n\nEducational content only - not diagnosis or medical advice."
    caption = caption[: rules["caption_max"]]
    tags = hashtags_for(topic, platform)
    if tags:
        caption = caption + "\n\n" + " ".join("#" + t for t in tags)
    return caption


def hashtags_for(topic: dict, platform: str) -> list[str]:
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["instagram"])
    pool_key = {"parents": "parenting", "educators": "education", "students": "students", "enthusiasts": "research"}.get(topic["audience"][0], "developmentalpsychology")
    pool = HASHTAG_POOLS[pool_key]
    extra = [t.lower().replace(" ", "") for t in topic["title"].split(":")[:1]]
    merged = list(dict.fromkeys(extra + pool))
    return merged[: rules["hashtags"]]


def carousel_slides(topic: dict, slides: int = 5) -> list[dict]:
    out = [{"heading": topic.get("title", "Topic"), "bullets": [topic.get("fact", ""), f"Domain: {topic.get('domain', 'Education')}"]}]
    if topic["id"] == "zpd":
        bullets = [
            "Zone of proximal development = what a learner can do WITH help.",
            "Too easy = boredom. Too hard = frustration.",
            "Scaffolding: model, prompt, fade support.",
            "Tip: ask 'what's the next small step?'",
        ]
    elif topic["id"] == "attachment":
        bullets = [
            "Secure: uses caregiver as base, upset by absence, soothed by return.",
            "Avoidant: little distress, avoids contact.",
            "Ambivalent: clingy, hard to soothe.",
            "Disorganized: contradictory responses (rare, often linked to risk).",
        ]
    elif topic["id"] == "parenting_styles":
        bullets = [
            "Authoritative: high warmth + high structure (best average outcomes).",
            "Authoritarian: low warmth, high control.",
            "Permissive: high warmth, low structure.",
            "Uninvolved: low warmth, low structure.",
        ]
    else:
        bullets = [
            f"What it is: {topic['fact']}",
            "Why it matters: it shapes learning, behaviour and wellbeing.",
            "Practical tip: keep expectations age-appropriate and consistent.",
            "Myth check: development has wide normal ranges — avoid labels.",
        ]
    for b in bullets[: slides - 1]:
        out.append({"heading": b.split(":")[0] if ":" in b else "Key point", "bullets": [b]})
    out.append({"heading": "Remember", "bullets": ["Educational content only — not diagnosis or medical advice.", "Brand: " + BRAND_FALLBACK]})
    return out


def video_script(topic: dict) -> dict:
    return {
        "title": f"{topic['title']} in 60 seconds",
        "scenes": [
            {"seconds": 0, "text": f"Hook: {headline(topic, 0)}", "visual": "title_card"},
            {"seconds": 8, "text": topic["fact"], "visual": "fact_card"},
            {"seconds": 20, "text": "Why it matters: builds learning, behaviour and wellbeing.", "visual": "icon_list"},
            {"seconds": 32, "text": "Practical tip: keep it age-appropriate, calm and consistent.", "visual": "tip_card"},
            {"seconds": 44, "text": "Educational content only — not diagnosis or medical advice.", "visual": "disclaimer_card"},
            {"seconds": 52, "text": "Follow for daily developmental psych science.", "visual": "end_card"},
        ],
        "duration": 60,
    }


def idea_score(topic: dict, trend: float, seed: int = 0) -> float:
    rng = random.Random(seed)
    relevance = 85 + rng.randint(-5, 5)
    interest = 70 + rng.randint(-10, 10)
    shareability = 60 + rng.randint(-10, 20)
    edu = 90
    freshness = 50 + trend * 40
    feasibility = 80
    return round(0.22 * relevance + 0.16 * interest + 0.16 * shareability + 0.18 * edu + 0.12 * freshness + 0.16 * feasibility, 1)


def normalize_for_dedupe(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text.lower())
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def duplicate_key(text: str) -> str:
    return stable_hash(normalize_for_dedupe(text))[:16]


def daily_plan(date: datetime | None = None, max_posts: int = 6) -> list[dict]:
    date = date or datetime.utcnow()
    rng = random.Random(date.strftime("%Y-%m-%d"))
    topics = pick_topics(6, seed=rng.randint(0, 10 ** 9))
    plan = []
    formats = ["infographic", "carousel", "pin", "reel", "post", "short_video"]
    for i, t in enumerate(topics[:max_posts]):
        plan.append({
            "topic_id": t["id"],
            "format": formats[i % len(formats)],
            "platforms": ["instagram", "facebook", "pinterest", "threads"] if i % 2 == 0 else ["instagram", "facebook", "youtube", "linkedin"],
            "seed": rng.randint(0, 10 ** 9),
        })
    return plan


def now_pkt() -> datetime:
    # Asia/Karachi = UTC+5, no DST
    return datetime.utcnow() + timedelta(hours=5)


def claim_safety_check(text: str) -> list[str]:
    hits = []
    low = text.lower()
    for banned in CLAIM_BAN:
        if re.search(r"(?<![a-z])" + re.escape(banned.lower()) + r"(?![a-z])", low):
            hits.append(f"absolute/unsafe phrase: '{banned}'")
    if not any(p in low for p in SAFE_PHRASES):
        hits.append("missing hedging phrase (research suggests / on average / typically)")
    return hits


def hedged_body(topic: dict) -> str:
    """Fact text with a hedging clause appended when the fact lacks one,
    so published/rendered body text never reads as an absolute claim."""
    fact = topic["fact"]
    if any(p in fact.lower() for p in SAFE_PHRASES):
        return fact
    return fact + " Research suggests this is a typical pattern, and outcomes vary by context."


if __name__ == "__main__":
    t = TOPICS[0]
    print(headline(t))
    print(caption_for("instagram", t))
    print(carousel_slides(t, 4))
