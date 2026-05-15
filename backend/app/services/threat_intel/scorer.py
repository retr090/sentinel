from typing import Any, Dict, Tuple


def calculate_risk_score(enrichments: Dict[str, Any]) -> Tuple[float, str]:
    score = 0.0

    gn = enrichments.get("greynoise", {})
    if isinstance(gn, dict) and not gn.get("error"):
        cls = (gn.get("classification") or "").lower()
        if cls == "malicious":
            score += 30
        elif cls == "benign":
            score -= 20
        if gn.get("noise"):
            score += 10

    av = enrichments.get("alienvault", {})
    if isinstance(av, dict) and not av.get("error"):
        pulse_count = (av.get("pulse_info") or {}).get("count", 0) or 0
        score += min(pulse_count * 3, 20)
        rep = av.get("reputation")
        if rep is not None and rep < 0:
            score += 10

    uh = enrichments.get("urlhaus", {})
    if isinstance(uh, dict) and not uh.get("error"):
        if uh.get("query_status") == "ok":
            urls = uh.get("urls") or []
            online = sum(1 for u in urls if isinstance(u, dict) and u.get("url_status") == "online")
            offline = len(urls) - online
            score += min(online * 15 + offline * 5, 35)
            if uh.get("url_status") == "online":
                score += 25

    tf = enrichments.get("threatfox", {})
    if isinstance(tf, dict) and not tf.get("error"):
        if tf.get("query_status") == "ok":
            data = tf.get("data") or []
            if data and isinstance(data, list):
                conf = data[0].get("confidence_level", 0) or 0
                score += min(conf / 5.0, 15)

    mb = enrichments.get("malwarebazaar", {})
    if isinstance(mb, dict) and not mb.get("error"):
        if mb.get("query_status") == "ok":
            score += 25

    vt = enrichments.get("virustotal", {})
    if isinstance(vt, dict) and not vt.get("error"):
        stats = vt.get("last_analysis_stats") or {}
        mal = stats.get("malicious", 0) or 0
        if mal > 5:
            score += 20
        elif mal > 0:
            score += 10

    ab = enrichments.get("abuseipdb", {})
    if isinstance(ab, dict) and not ab.get("error"):
        confidence = ab.get("abuse_confidence_score", 0)
        if confidence >= 80:
            score += 30
        elif confidence >= 50:
            score += 20
        elif confidence >= 25:
            score += 10
        elif confidence > 0:
            score += 5
        reports = ab.get("total_reports", 0)
        if reports > 100:
            score += 10
        elif reports > 10:
            score += 5

    shodan = enrichments.get("shodan", {})
    if isinstance(shodan, dict) and not shodan.get("error"):
        vulns = shodan.get("vulns") or []
        if vulns and isinstance(vulns[0], dict) and "cvss" in vulns[0]:
            # Full Shodan API — score by highest CVSS
            max_cvss = max((v.get("cvss") or 0 for v in vulns), default=0)
            score += min(float(max_cvss) * 2, 20) + min(len(vulns) * 1.5, 10)
        else:
            # InternetDB — only CVE IDs, no CVSS
            score += min(len(vulns) * 5, 15)

    xon = enrichments.get("xposedornot", {})
    if isinstance(xon, dict) and not xon.get("error"):
        breach_count = xon.get("breach_count", 0)
        if breach_count > 10:
            score += 20
        elif breach_count > 5:
            score += 14
        elif breach_count > 0:
            score += 8
        if xon.get("paste_count", 0) > 0:
            score += 5
        if xon.get("exposed_emails", 0) > 0:
            score += 5

    lc = enrichments.get("leakcheck", {})
    if isinstance(lc, dict) and not lc.get("error"):
        if lc.get("found"):
            score += min(lc.get("leak_count", 0) * 4, 20)

    dns_data = enrichments.get("dns", {})
    if isinstance(dns_data, dict) and not dns_data.get("error") and "has_mx" in dns_data:
        if dns_data.get("disposable"):
            score += 30
        elif not dns_data.get("has_mx"):
            score += 15

    hunter = enrichments.get("hunter", {})
    if isinstance(hunter, dict) and not hunter.get("error"):
        status = (hunter.get("status") or "").lower()
        if status in ("invalid", "disposable"):
            score += 20
        elif status == "risky":
            score += 10

    # CIRCL CVE (new format with cvss_score key)
    circl_data = enrichments.get("circl_cve", {})
    if isinstance(circl_data, dict) and not circl_data.get("error"):
        try:
            cvss = float(circl_data.get("cvss_score", 0) or 0)
            if cvss >= 9.0:
                score += 80
            elif cvss >= 7.0:
                score += 55
            elif cvss >= 4.0:
                score += 30
            elif cvss > 0:
                score += 10
            if circl_data.get("exploit_available"):
                score += 15
        except (TypeError, ValueError):
            pass

    # NVD fallback when no circl_cve data
    nvd_data = enrichments.get("nvd", {})
    if isinstance(nvd_data, dict) and not nvd_data.get("error") and not circl_data.get("cvss_score"):
        try:
            cvss = (
                nvd_data.get("cvss")
                or (nvd_data.get("metrics", {}).get("cvssMetricV31", [{}])[0].get("cvssData", {}).get("baseScore"))
                or (nvd_data.get("metrics", {}).get("cvssMetricV30", [{}])[0].get("cvssData", {}).get("baseScore"))
                or (nvd_data.get("metrics", {}).get("cvssMetricV2", [{}])[0].get("cvssData", {}).get("baseScore"))
            )
            if cvss is not None:
                score += min(float(cvss) * 10, 100)
        except (IndexError, KeyError, TypeError, ValueError):
            pass

    score = max(0.0, min(100.0, round(score, 1)))

    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"
    elif score > 0:
        level = "low"
    else:
        level = "clean"

    return score, level
