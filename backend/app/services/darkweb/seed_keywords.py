from datetime import datetime
import uuid

DEFAULT_KEYWORDS = [
    # ── CRITICAL — Military ──────────────
    {
        "keyword": "Sri Lanka Air Force",
        "aliases": ["SLAF", "airforce.lk", "Air Force Sri Lanka"],
        "category": "Military",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Sri Lanka Army",
        "aliases": ["SLA", "army.lk", "Sri Lanka Army HQ"],
        "category": "Military",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Sri Lanka Navy",
        "aliases": ["SLN", "navy.lk"],
        "category": "Military",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    {
        "keyword": "mil.lk",
        "aliases": [],
        "category": "Military",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Ministry of Defence Sri Lanka",
        "aliases": ["mod.gov.lk", "Sri Lanka Defence"],
        "category": "Military",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    # ── CRITICAL — Government ────────────
    {
        "keyword": "gov.lk",
        "aliases": [],
        "category": "Government",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Central Bank Sri Lanka",
        "aliases": ["CBSL", "cbsl.gov.lk", "Central Bank of Sri Lanka"],
        "category": "Finance",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Sri Lanka Police",
        "aliases": ["police.lk", "SL Police"],
        "category": "Government",
        "priority": "CRITICAL",
        "alert_mode": "immediate",
    },
    # ── HIGH — Government ────────────────
    {
        "keyword": "Sri Lanka Customs",
        "aliases": ["customs.gov.lk", "Sri Lanka Customs Department"],
        "category": "Government",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Election Commission Sri Lanka",
        "aliases": ["elections.gov.lk"],
        "category": "Government",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Ministry of Foreign Affairs Sri Lanka",
        "aliases": ["mfa.gov.lk", "Sri Lanka Foreign Ministry"],
        "category": "Government",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    # ── HIGH — Finance ───────────────────
    {
        "keyword": "Bank of Ceylon",
        "aliases": ["boc.lk", "BOC Sri Lanka"],
        "category": "Finance",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    {
        "keyword": "People's Bank Sri Lanka",
        "aliases": ["peoplesbank.lk", "Peoples Bank LK"],
        "category": "Finance",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    # ── HIGH — Infrastructure ────────────
    {
        "keyword": "Ceylon Electricity Board",
        "aliases": ["CEB", "ceb.lk"],
        "category": "Infrastructure",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Sri Lanka Telecom",
        "aliases": ["SLT", "slt.lk", "Sri Lanka Telecom PLC"],
        "category": "Infrastructure",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Sri Lanka Ports Authority",
        "aliases": ["SLPA", "slpa.lk", "Port of Colombo"],
        "category": "Infrastructure",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Bandaranaike International Airport",
        "aliases": ["BIA", "CMB airport", "airport.lk"],
        "category": "Infrastructure",
        "priority": "HIGH",
        "alert_mode": "immediate",
    },
    {
        "keyword": "Sri Lanka Railways",
        "aliases": ["railway.gov.lk"],
        "category": "Infrastructure",
        "priority": "HIGH",
        "alert_mode": "daily",
    },
    # ── HIGH — Healthcare ────────────────
    {
        "keyword": "National Hospital Colombo",
        "aliases": ["nhsl.health.gov.lk"],
        "category": "Healthcare",
        "priority": "HIGH",
        "alert_mode": "daily",
    },
    {
        "keyword": "health.gov.lk",
        "aliases": ["Ministry of Health Sri Lanka"],
        "category": "Healthcare",
        "priority": "HIGH",
        "alert_mode": "daily",
    },
    # ── MEDIUM — General ─────────────────
    {
        "keyword": "Sri Lanka",
        "aliases": ["SriLanka", "LKA"],
        "category": "General",
        "priority": "MEDIUM",
        "alert_mode": "daily",
    },
    {
        "keyword": "Colombo",
        "aliases": ["Colombo Sri Lanka"],
        "category": "General",
        "priority": "MEDIUM",
        "alert_mode": "daily",
    },
    {
        "keyword": ".lk",
        "aliases": [],
        "category": "General",
        "priority": "MEDIUM",
        "alert_mode": "daily",
    },
    # ── MEDIUM — Telecom ─────────────────
    {
        "keyword": "Dialog Axiata",
        "aliases": ["dialog.lk", "Dialog Sri Lanka"],
        "category": "Infrastructure",
        "priority": "MEDIUM",
        "alert_mode": "daily",
    },
    {
        "keyword": "Mobitel Sri Lanka",
        "aliases": ["mobitel.lk"],
        "category": "Infrastructure",
        "priority": "MEDIUM",
        "alert_mode": "daily",
    },
    # ── LOW — Education ──────────────────
    {
        "keyword": "University of Colombo",
        "aliases": ["cmb.ac.lk"],
        "category": "Education",
        "priority": "LOW",
        "alert_mode": "weekly",
    },
    {
        "keyword": "ac.lk",
        "aliases": [],
        "category": "Education",
        "priority": "LOW",
        "alert_mode": "weekly",
    },
]


async def seed_default_keywords(db):
    """Seed default Sri Lanka keywords on first run. Skip if already exists."""
    from sqlalchemy import select
    from app.models.darkweb import DarkWebKeyword

    result = await db.execute(select(DarkWebKeyword).limit(1))
    existing = result.scalar_one_or_none()

    if existing:
        print("Keywords already seeded — skipping")
        return 0

    count = 0
    for kw_data in DEFAULT_KEYWORDS:
        kw = DarkWebKeyword(
            id=uuid.uuid4(),
            keyword=kw_data["keyword"],
            aliases=kw_data.get("aliases", []),
            category=kw_data["category"],
            priority=kw_data["priority"],
            alert_mode=kw_data.get("alert_mode", "daily"),
            is_active=True,
            hit_count=0,
            created_at=datetime.utcnow(),
        )
        db.add(kw)
        count += 1

    await db.commit()
    print(f"Seeded {count} default keywords")
    return count
