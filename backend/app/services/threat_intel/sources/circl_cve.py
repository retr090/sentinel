import re
import httpx

_HEADERS = {"User-Agent": "SENTINEL-OSINT/1.0", "Accept": "application/json"}

_EXPLOIT_KEYWORDS = {
    "exploit", "exploited", "exploiting", "exploitable",
    "metasploit", "proof-of-concept", "poc", "nuclei",
    "actively exploited", "exploited in the wild", "weaponized",
}


def _check_exploit(refs: list, summary: str) -> bool:
    summary_lower = summary.lower()
    if any(kw in summary_lower for kw in {"actively exploited", "exploited in the wild", "weaponized"}):
        return True
    return any(
        any(kw in str(r).lower() for kw in _EXPLOIT_KEYWORDS)
        for r in refs
    )


async def lookup(cve_id: str) -> dict:
    cve_id = cve_id.upper().strip()
    if not re.match(r'^CVE-\d{4}-\d+$', cve_id):
        return {"error": "invalid CVE format"}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(
                f"https://cve.circl.lu/api/cve/{cve_id}",
                headers=_HEADERS,
            )
            if r.status_code == 404:
                return {"error": "CVE not found", "cve_id": cve_id}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}
            data = r.json()
            if not data:
                return {"error": "empty response"}
            return _normalize(cve_id, data)
    except httpx.TimeoutException:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


def _normalize(cve_id: str, data: dict) -> dict:
    if data.get("dataVersion") is None and data.get("id"):
        return _from_legacy(cve_id, data)
    return _from_v5(cve_id, data)


def _from_legacy(cve_id: str, data: dict) -> dict:
    raw_cvss3 = data.get("cvss3") or data.get("cvss-v3")
    raw_cvss2 = data.get("cvss") or data.get("cvss2")
    try:
        cvss_v3 = float(raw_cvss3) if raw_cvss3 is not None else None
    except (TypeError, ValueError):
        cvss_v3 = None
    try:
        cvss_v2 = float(raw_cvss2) if raw_cvss2 is not None else None
    except (TypeError, ValueError):
        cvss_v2 = None

    cvss_score = float(cvss_v3 or cvss_v2 or 0)
    severity = _score_to_severity(cvss_score)

    refs = data.get("references", [])
    if refs and isinstance(refs[0], dict):
        refs = [r.get("url", "") for r in refs if r.get("url")]
    refs = [r for r in refs if r][:5]

    cpes = data.get("vulnerable_configuration", [])[:8]
    if cpes and isinstance(cpes[0], dict):
        cpes = [c.get("id", "") for c in cpes if c.get("id")]

    access = data.get("access", {})
    exploit_available = _check_exploit(refs, data.get("summary", "") or data.get("details", ""))

    return {
        "cve_id": data.get("id", cve_id),
        "summary": data.get("summary", data.get("details", "")),
        "cvss_v3": cvss_v3,
        "cvss_v2": cvss_v2,
        "cvss_score": cvss_score,
        "severity": severity,
        "cwe": data.get("cwe", ""),
        "published": data.get("Published", data.get("published", "")),
        "modified": data.get("Modified", data.get("modified", "")),
        "references": refs,
        "vulnerable_products": cpes,
        "access_vector": access.get("vector", ""),
        "access_complexity": access.get("complexity", ""),
        "exploit_available": exploit_available,
    }


def _from_v5(cve_id: str, data: dict) -> dict:
    meta = data.get("cveMetadata", {})
    cna = data.get("containers", {}).get("cna", {})
    adps = data.get("containers", {}).get("adp", [])

    descriptions = cna.get("descriptions", [])
    summary = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

    cvss_v3 = cvss_v2 = cvss_vector = severity = None
    for source in [cna] + adps:
        for metric in source.get("metrics", []):
            if "cvssV3_1" in metric or "cvssV3_0" in metric:
                m = metric.get("cvssV3_1") or metric.get("cvssV3_0")
                cvss_v3 = m.get("baseScore")
                cvss_vector = m.get("vectorString")
                severity = m.get("baseSeverity")
                break
            elif "cvssV2_0" in metric:
                m = metric["cvssV2_0"]
                cvss_v2 = m.get("baseScore")
                if not severity:
                    severity = m.get("baseSeverity")
        if cvss_v3 is not None:
            break

    cvss_score = float(cvss_v3 or cvss_v2 or 0)
    if not severity:
        severity = _score_to_severity(cvss_score)

    cwe = ""
    for pt in cna.get("problemTypes", []):
        for desc in pt.get("descriptions", []):
            if desc.get("type") == "CWE":
                cwe = desc.get("cweId", "")
                break
        if cwe:
            break

    refs = [ref["url"] for ref in cna.get("references", [])[:5] if ref.get("url")]

    products = []
    for affected in cna.get("affected", [])[:8]:
        vendor = affected.get("vendor", "")
        product = affected.get("product", "")
        if vendor and product:
            products.append(f"{vendor} {product}")
        elif product:
            products.append(product)

    access_vector = access_complexity = ""
    if cvss_vector:
        av_match = re.search(r'AV:([NALP])', cvss_vector)
        ac_match = re.search(r'AC:([LMH])', cvss_vector)
        if av_match:
            access_vector = {"N": "NETWORK", "A": "ADJACENT", "L": "LOCAL", "P": "PHYSICAL"}.get(
                av_match.group(1), av_match.group(1)
            )
        if ac_match:
            access_complexity = {"L": "LOW", "M": "MEDIUM", "H": "HIGH"}.get(
                ac_match.group(1), ac_match.group(1)
            )

    exploit_available = _check_exploit(refs, data.get("summary", "") or data.get("details", ""))

    return {
        "cve_id": meta.get("cveId", cve_id),
        "summary": summary,
        "cvss_v3": float(cvss_v3) if cvss_v3 is not None else None,
        "cvss_v2": float(cvss_v2) if cvss_v2 is not None else None,
        "cvss_score": cvss_score,
        "severity": severity,
        "cwe": cwe,
        "published": meta.get("datePublished", ""),
        "modified": meta.get("dateUpdated", ""),
        "references": refs,
        "vulnerable_products": products,
        "access_vector": access_vector,
        "access_complexity": access_complexity,
        "exploit_available": exploit_available,
    }


def _score_to_severity(score: float) -> str:
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "NONE"
