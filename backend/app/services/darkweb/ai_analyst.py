"""
AI-powered classifier for forum intelligence results.

Uses Groq (llama-3.3-70b-versatile) to distinguish actual data breach posts
from news/discussion threads, and to extract structured intelligence.

Falls back gracefully to keyword-based results if GROQ_API_KEY is not set
or the API call fails — the caller always gets a usable result list back.
"""
import json
import asyncio
import re
from typing import Dict, List, Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Max concurrent Groq calls — stays well within rate limits
_SEM = asyncio.Semaphore(3)

_PROMPT = """\
You are a threat intelligence analyst reviewing a post from Breached.st, a cybercrime forum \
(Leaks section). Determine whether this post contains actual compromised/leaked data, or is \
just news, commentary, or discussion about a breach.

Post title: {title}
Post snippet: {snippet}
Keyword that triggered this result: {keyword}

Respond with ONLY valid JSON — no markdown, no explanation:
{{
  "is_breach": true or false,
  "confidence": 0.0 to 1.0,
  "severity": "CRITICAL" or "HIGH" or "MEDIUM" or "LOW",
  "victim_org": "organisation name" or null,
  "data_types": ["e.g. email addresses", "passwords", "national IDs"],
  "record_count": "e.g. 150,000 records" or null,
  "threat_actor": "group or handle" or null,
  "summary": "One or two sentence analyst summary of exactly what was found."
}}

Classification rules:
- is_breach = true  → post is sharing, selling, or dumping actual data/credentials/access
- is_breach = false → post is news, discussion, defacement report, or just references the keyword
- severity = CRITICAL → govt / military / critical infrastructure data (.gov.lk, police, military)
- severity = HIGH    → banking, healthcare, telecom, large commercial database (>10k records)
- severity = MEDIUM  → general user data, smaller datasets
- severity = LOW     → unclear scope or very limited exposure\
"""


def _extract_json(text: str) -> Optional[dict]:
    """Parse JSON from model output, handling markdown code fences."""
    text = text.strip()
    # Strip ```json ... ``` wrapper if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find the outermost JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


async def classify_post(title: str, snippet: str, keyword: str) -> Optional[Dict]:
    """
    Classify a single forum post via Groq.
    Returns the parsed analysis dict, or None on failure.
    """
    if not settings.GROQ_API_KEY:
        return None

    prompt = _PROMPT.format(
        title=title[:400],
        snippet=(snippet or "")[:600],
        keyword=keyword[:100],
    )

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        async with _SEM:
            resp = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=350,
            )

        raw = resp.choices[0].message.content or ""
        result = _extract_json(raw)
        if result is None:
            logger.warning("AI analyst: failed to parse JSON", raw=raw[:200])
        return result

    except Exception as exc:
        logger.warning("AI analyst: Groq call failed", error=str(exc))
        return None


async def enrich_results(results: List[Dict]) -> List[Dict]:
    """
    Run AI classification on a batch of forum results.

    - Posts the AI is confident (>=0.80) are NOT real data breaches are dropped.
    - Surviving results are enriched: severity, victim_org, threat_actor updated,
      and full AI analysis stored in raw_data['ai_analysis'].
    - If GROQ_API_KEY is absent or all calls fail, the original list is returned unchanged.
    """
    if not settings.GROQ_API_KEY or not results:
        return results

    logger.info(f"AI analyst: classifying {len(results)} forum results")

    tasks = [
        classify_post(
            r.get("title", ""),
            r.get("snippet", ""),
            r.get("keyword_matched", ""),
        )
        for r in results
    ]
    analyses = await asyncio.gather(*tasks, return_exceptions=True)

    enriched = []
    dropped = 0

    for result, analysis in zip(results, analyses):
        if isinstance(analysis, Exception) or analysis is None:
            # API failure — keep the result with its keyword-based fields
            enriched.append(result)
            continue

        is_breach = analysis.get("is_breach", True)
        confidence = float(analysis.get("confidence", 0.0))

        # Drop only when AI is confident this isn't real data
        if not is_breach and confidence >= 0.80:
            logger.info(
                "AI analyst: dropped non-breach",
                title=result.get("title", "")[:60],
                confidence=confidence,
            )
            dropped += 1
            continue

        # Overwrite severity with AI judgment (more accurate than keyword heuristic)
        ai_severity = analysis.get("severity")
        if ai_severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            result["severity"] = ai_severity

        # Fill in extracted fields if not already set by the scraper
        if analysis.get("victim_org") and not result.get("victim_org"):
            result["victim_org"] = analysis["victim_org"]
        if analysis.get("threat_actor") and not result.get("threat_actor"):
            result["threat_actor"] = analysis["threat_actor"]

        # Store full AI output for display in the UI
        result.setdefault("raw_data", {})["ai_analysis"] = {
            "is_breach": is_breach,
            "confidence": confidence,
            "data_types": analysis.get("data_types") or [],
            "record_count": analysis.get("record_count"),
            "summary": analysis.get("summary") or "",
        }

        enriched.append(result)

    logger.info(
        f"AI analyst: kept {len(enriched)}, dropped {dropped} of {len(results)}"
    )
    return enriched
