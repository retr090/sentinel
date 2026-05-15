import json
from app.core.config import settings

SUSPICIOUS_PORTS = {
    4444: "Metasploit C2",
    1080: "SOCKS Proxy",
    3389: "RDP Exposed",
    5900: "VNC Exposed",
    6667: "IRC Botnet C2",
    8080: "Common C2/Proxy",
    8443: "Alternate HTTPS C2",
    9001: "Tor Relay",
    31337: "Classic Backdoor",
    1337: "Common Backdoor",
    4899: "Radmin Remote",
    5555: "Android Debug Bridge",
    7777: "Common Backdoor",
}

MALWARE_CATEGORIES = {
    3: "Fraud", 4: "DDoS Attack", 7: "Phishing",
    9: "Open Proxy", 11: "Email Spam", 14: "Port Scan",
    15: "Hacking", 16: "SQL Injection", 18: "Brute Force",
    19: "Bad Bot", 21: "Web App Attack", 22: "SSH Attack",
    23: "IoT Attack",
}


def rule_based_analysis(ioc_type: str, value: str, score: int, level: str, sources: dict) -> dict:
    findings = []
    actions = []
    category = "Unknown Threat"
    confidence = "LOW"
    sources_flagged = 0
    sources_total = 0

    gn = sources.get("greynoise", {})
    if not gn.get("error"):
        sources_total += 1
        if gn.get("classification") == "malicious":
            sources_flagged += 1
            findings.append("GreyNoise classifies this as malicious")
        elif gn.get("classification") == "benign":
            findings.append("GreyNoise identifies this as benign internet infrastructure")
        if gn.get("noise"):
            findings.append("Actively scanning the internet (noise source)")

    ab = sources.get("abuseipdb", {})
    if not ab.get("error"):
        sources_total += 1
        conf = ab.get("abuse_confidence_score", 0)
        reports = ab.get("total_reports", 0)
        users = ab.get("num_distinct_users", 0)
        if conf >= 50:
            sources_flagged += 1
            findings.append(
                f"AbuseIPDB: {conf}% confidence — {reports} reports from {users} distinct users"
            )
            cats = []
            for r in ab.get("reports", []):
                for c in r.get("categories", []):
                    label = MALWARE_CATEGORIES.get(c)
                    if label and label not in cats:
                        cats.append(label)
            if cats:
                findings.append(f"Reported abuse types: {', '.join(cats[:3])}")
        elif conf > 0:
            findings.append(f"AbuseIPDB: low confidence {conf}% ({reports} reports)")

    sh = sources.get("shodan", {})
    if not sh.get("error"):
        ports = sh.get("ports", [])
        vulns = sh.get("vulns", [])
        suspicious = {p: SUSPICIOUS_PORTS[p] for p in ports if p in SUSPICIOUS_PORTS}
        if suspicious:
            sources_flagged += 1
            for port, desc in suspicious.items():
                findings.append(f"Port {port} open — {desc}")
        if vulns:
            sources_flagged += 1
            findings.append(f"Known vulnerabilities: {', '.join(list(vulns)[:3])}")
        if ports:
            findings.append(f"Open ports: {', '.join(map(str, ports[:8]))}")

    av = sources.get("alienvault", {})
    if not av.get("error"):
        sources_total += 1
        pulses = av.get("pulse_info", {}).get("count", 0)
        if pulses > 0:
            sources_flagged += 1
            findings.append(f"Referenced in {pulses} AlienVault OTX threat intelligence pulses")

    uh = sources.get("urlhaus", {})
    if not uh.get("error"):
        sources_total += 1
        if uh.get("query_status") == "ok":
            sources_flagged += 1
            count = len(uh.get("urls", []))
            findings.append(f"Found in URLhaus: {count} malicious URLs associated")
        else:
            findings.append("Not found in URLhaus malicious URL database")

    mb = sources.get("malwarebazaar", {})
    if not mb.get("error"):
        sources_total += 1
        if mb.get("query_status") == "ok":
            sources_flagged += 1
            data = mb.get("data", [{}])[0]
            findings.append(
                f"Confirmed malware in MalwareBazaar: "
                f"{data.get('signature', 'Unknown')} ({data.get('file_type', '')})"
            )

    tf = sources.get("threatfox", {})
    if not tf.get("error"):
        sources_total += 1
        if tf.get("query_status") == "ok":
            sources_flagged += 1
            data = tf.get("data", [{}])
            if data:
                findings.append(
                    f"ThreatFox: associated with "
                    f"{data[0].get('malware', 'malware')} — {data[0].get('threat_type', '')}"
                )

    vt = sources.get("virustotal", {})
    if not vt.get("error") and vt.get("error") != "no_api_key":
        sources_total += 1
        stats = vt.get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        if malicious > 0:
            sources_flagged += 1
            findings.append(f"VirusTotal: {malicious} security engines flag as malicious")

    gn_class = gn.get("classification", "")
    ab_cats = []
    for r in ab.get("reports", []):
        ab_cats.extend(r.get("categories", []))
    sh_ports = sh.get("ports", [])
    has_c2_port = any(p in SUSPICIOUS_PORTS for p in sh_ports)

    if mb.get("query_status") == "ok":
        mb_sig = mb.get("data", [{}])[0].get("signature", "")
        category = f"Malware Sample — {mb_sig}" if mb_sig else "Malware Sample"
    elif tf.get("query_status") == "ok":
        tf_data = tf.get("data", [{}])
        category = (
            tf_data[0].get("threat_type", "Malware Infrastructure").replace("_", " ").title()
            if tf_data else "Malware Infrastructure"
        )
    elif gn_class == "malicious" and has_c2_port:
        category = "Command & Control Server"
    elif gn_class == "malicious":
        category = "Malicious Host"
    elif 18 in ab_cats or 22 in ab_cats:
        category = "Brute Force Attacker"
    elif 4 in ab_cats:
        category = "DDoS Attack Source"
    elif 7 in ab_cats:
        category = "Phishing Infrastructure"
    elif gn.get("noise") and gn_class != "malicious":
        category = "Internet Scanner"
    elif uh.get("query_status") == "ok":
        category = "Malware Distribution"
    elif gn_class == "benign":
        category = "Legitimate Infrastructure"
    elif score == 0:
        category = "No Threat Detected"
    else:
        category = "Suspicious Host"

    if level == "critical":
        actions = [
            "Block at perimeter firewall immediately",
            "Search SIEM for any internal hosts that communicated with this IOC",
            "Escalate to incident response team",
            "Preserve logs for forensic investigation",
            "Check endpoint detection for related alerts",
        ]
    elif level == "high":
        actions = [
            "Block at perimeter firewall",
            "Search SIEM logs for connections to this IOC",
            "Check email gateway for messages referencing this IOC",
            "Monitor for related indicators",
        ]
    elif level == "medium":
        actions = [
            "Add to watchlist for monitoring",
            "Search logs for any connections",
            "Investigate context before blocking",
            "Cross-reference with other intelligence sources",
        ]
    elif level == "low":
        actions = [
            "Monitor passively",
            "No immediate action required",
            "Re-evaluate if additional reports emerge",
        ]
    else:
        actions = [
            "No action required",
            "IOC appears clean across all sources",
            "Continue routine monitoring",
        ]

    if ioc_type == "ip" and level in ("critical", "high"):
        actions.append("Search email headers for this IP address")
    if ioc_type in ("hash_md5", "hash_sha1", "hash_sha256") and level in ("critical", "high"):
        actions.append("Scan all endpoints for this file hash")
        actions.append("Check quarantine logs on email gateway")
    if ioc_type == "domain" and level in ("critical", "high"):
        actions.append("Block at DNS level across all resolvers")
        actions.append("Search proxy logs for requests to this domain")

    if sources_total > 0:
        ratio = sources_flagged / sources_total
        if ratio >= 0.6 or sources_flagged >= 3:
            confidence = "HIGH"
        elif ratio >= 0.3 or sources_flagged >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

    if score == 0:
        confidence = "HIGH"

    if level == "critical":
        summary = (
            f"This {ioc_type.upper()} is confirmed malicious by multiple independent sources "
            f"and poses an immediate threat."
        )
    elif level == "high":
        summary = (
            f"This {ioc_type.upper()} is flagged as malicious with high confidence. "
            f"Blocking is recommended."
        )
    elif level == "medium":
        summary = (
            f"This {ioc_type.upper()} shows suspicious characteristics. Further investigation "
            f"recommended before taking action."
        )
    elif level == "low":
        summary = (
            f"This {ioc_type.upper()} has minimal threat indicators. Low priority — monitor passively."
        )
    else:
        summary = (
            f"No threat indicators found for this {ioc_type.upper()} across all checked sources."
        )

    return {
        "verdict": level.upper() if level != "clean" else "CLEAN",
        "category": category,
        "summary": summary,
        "key_findings": findings[:6],
        "recommended_actions": actions[:5],
        "confidence": confidence,
        "sources_flagged": sources_flagged,
        "sources_total": sources_total,
        "threat_actor": None,
        "mitre_tactics": [],
        "generated_by": "rule_engine",
    }


async def groq_analysis(
    ioc_type: str, value: str, score: int, level: str, sources: dict, rule_result: dict
) -> dict:
    if not settings.GROQ_API_KEY:
        return rule_result

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        model = settings.GROQ_MODEL

        source_summary = []

        gn = sources.get("greynoise", {})
        if not gn.get("error"):
            source_summary.append(
                f"GreyNoise: classification={gn.get('classification','unknown')}, "
                f"noise={gn.get('noise',False)}, riot={gn.get('riot',False)}"
            )

        ab = sources.get("abuseipdb", {})
        if not ab.get("error"):
            source_summary.append(
                f"AbuseIPDB: confidence={ab.get('abuse_confidence_score',0)}%, "
                f"reports={ab.get('total_reports',0)}, "
                f"users={ab.get('num_distinct_users',0)}, "
                f"isp={ab.get('isp','unknown')}"
            )

        sh = sources.get("shodan", {})
        if not sh.get("error"):
            source_summary.append(
                f"Shodan: ports={sh.get('ports',[])}, "
                f"vulns={sh.get('vulns',[])}, tags={sh.get('tags',[])}"
            )

        ip = sources.get("ipinfo", {})
        if not ip.get("error"):
            source_summary.append(
                f"IPInfo: country={ip.get('country')}, "
                f"org={ip.get('org')}, city={ip.get('city')}"
            )

        av = sources.get("alienvault", {})
        if not av.get("error"):
            pulses = av.get("pulse_info", {}).get("count", 0)
            source_summary.append(
                f"AlienVault OTX: pulse_count={pulses}, reputation={av.get('reputation',0)}"
            )

        uh = sources.get("urlhaus", {})
        if not uh.get("error"):
            source_summary.append(
                f"URLhaus: status={uh.get('query_status')}, url_count={len(uh.get('urls',[]))}"
            )

        mb = sources.get("malwarebazaar", {})
        if not mb.get("error"):
            mb_data = mb.get("data", [{}])
            if mb_data and mb.get("query_status") == "ok":
                source_summary.append(
                    f"MalwareBazaar: signature={mb_data[0].get('signature')}, "
                    f"file_type={mb_data[0].get('file_type')}"
                )
            else:
                source_summary.append("MalwareBazaar: not found")

        tf = sources.get("threatfox", {})
        if not tf.get("error"):
            if tf.get("query_status") == "ok":
                tf_data = tf.get("data", [{}])
                source_summary.append(
                    f"ThreatFox: malware={tf_data[0].get('malware') if tf_data else 'unknown'}, "
                    f"threat_type={tf_data[0].get('threat_type') if tf_data else 'unknown'}"
                )
            else:
                source_summary.append("ThreatFox: not found")

        vt = sources.get("virustotal", {})
        if not vt.get("error") and vt.get("error") != "no_api_key":
            stats = vt.get("last_analysis_stats", {})
            source_summary.append(
                f"VirusTotal: malicious={stats.get('malicious',0)}, "
                f"suspicious={stats.get('suspicious',0)}, clean={stats.get('harmless',0)}"
            )

        xon = sources.get("xposedornot", {})
        if not xon.get("error"):
            breach_count = xon.get("breach_count", 0)
            if breach_count > 0:
                breaches = xon.get("breaches", [])
                names = [b.get("name", "") for b in breaches[:5] if b.get("name")]
                all_data: list = []
                for b in breaches:
                    all_data.extend(b.get("data_classes", []))
                unique_data = list(dict.fromkeys(all_data))[:6]
                source_summary.append(
                    f"XposedOrNot: email found in {breach_count} data breaches. "
                    f"Breach sources: {', '.join(names) if names else 'unknown'}. "
                    f"Exposed data types: {', '.join(unique_data) if unique_data else 'unknown'}"
                )
            else:
                exposed_emails = xon.get("exposed_emails", 0)
                if exposed_emails > 0:
                    source_summary.append(
                        f"XposedOrNot: domain has {exposed_emails} exposed emails across "
                        f"{xon.get('breach_count', 0)} breaches"
                    )
                else:
                    source_summary.append("XposedOrNot: no breach exposure found")

        lc = sources.get("leakcheck", {})
        if not lc.get("error"):
            if lc.get("found"):
                leak_sources = lc.get("sources", [])
                fields = lc.get("fields", [])
                source_summary.append(
                    f"LeakCheck: credentials found in {lc.get('leak_count', 0)} leak databases. "
                    f"Sources: {', '.join(leak_sources[:5]) if leak_sources else 'unknown'}. "
                    f"Leaked fields: {', '.join(fields) if fields else 'unknown'}"
                )
            else:
                source_summary.append("LeakCheck: no credential leaks found")

        cve_data = sources.get("circl_cve", {})
        if not cve_data.get("error") and cve_data.get("cve_id"):
            source_summary.append(
                f"CIRCL CVE: {cve_data.get('cve_id')} — "
                f"CVSS {cve_data.get('cvss_score', 'N/A')} "
                f"({cve_data.get('severity', 'UNKNOWN')}). "
                f"Summary: {cve_data.get('summary', '')[:200]}. "
                f"Exploit available: {cve_data.get('exploit_available', False)}. "
                f"Affected: {', '.join(cve_data.get('vulnerable_products', [])[:3])}"
            )

        ioc_context = ""
        if ioc_type == "cve":
            ioc_context = """
CVE CONTEXT — focus your analysis on:
- How severe is this vulnerability (CVSS score and vector)
- What systems/software are affected and exposure breadth
- Is there a known exploit available in the wild
- What is the attack vector (network/local/physical) and complexity
- What immediate action should the SOC take (patch, mitigate, monitor)
- Patch urgency level and recommended timeline
"""
        elif ioc_type == "email":
            ioc_context = """
EMAIL IOC CONTEXT — focus your analysis on:
- How many breaches this email was found in and what data was exposed
- Whether credentials (passwords, tokens) are likely circulating
- Risk to the organisation if this is a corporate email address
- Whether the email domain shows signs of targeting
"""
        elif ioc_type == "domain" and (xon.get("breach_count", 0) > 0 or xon.get("exposed_emails", 0) > 0):
            ioc_context = """
DOMAIN BREACH CONTEXT — this domain has exposed user data. Consider:
- Scale of credential exposure and breach history
- Risk of credential stuffing attacks against this domain's users
- Whether the domain itself may be a target or already compromised
"""

        prompt = f"""You are a senior cybersecurity threat intelligence analyst. Analyse this IOC and provide a concise, actionable intelligence assessment.

IOC VALUE: {value}
IOC TYPE: {ioc_type}
RISK SCORE: {score}/100
RISK LEVEL: {level.upper()}
{ioc_context}

SOURCE INTELLIGENCE:
{chr(10).join(f'- {s}' for s in source_summary)}

Respond with this EXACT JSON (no other text):
{{
  "verdict": "MALICIOUS|SUSPICIOUS|CLEAN|INCONCLUSIVE",
  "category": "specific threat category in 3-5 words",
  "summary": "2-3 sentence analyst summary of what this IOC is and why it matters",
  "key_findings": ["finding 1", "finding 2", "finding 3", "finding 4", "finding 5"],
  "recommended_actions": ["action 1", "action 2", "action 3", "action 4", "action 5"],
  "confidence": "HIGH|MEDIUM|LOW",
  "sources_flagged": {rule_result.get('sources_flagged', 0)},
  "sources_total": {rule_result.get('sources_total', 0)},
  "threat_actor": "known threat actor name or null",
  "mitre_tactics": ["tactic1", "tactic2"]
}}

Rules: be direct and specific, reference actual source data, never fabricate data not in the sources."""

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity threat intelligence analyst. Always respond with valid JSON only. No markdown, no explanation.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        result["generated_by"] = "groq_ai"
        result["model"] = model
        return result

    except json.JSONDecodeError:
        return rule_result
    except Exception:
        return rule_result


async def analyse_ioc(ioc_type: str, value: str, score: int, level: str, sources: dict) -> dict:
    rule_result = rule_based_analysis(ioc_type, value, score, level, sources)
    return await groq_analysis(ioc_type, value, score, level, sources, rule_result)
