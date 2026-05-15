import re


def detect_ioc_type(value: str) -> str:
    v = value.strip()
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', v):
        return "ip"
    if re.match(r'^CVE-\d{4}-\d+$', v, re.IGNORECASE):
        return "cve"
    if re.match(r'^[a-fA-F0-9]{32}$', v):
        return "hash_md5"
    if re.match(r'^[a-fA-F0-9]{40}$', v):
        return "hash_sha1"
    if re.match(r'^[a-fA-F0-9]{64}$', v):
        return "hash_sha256"
    if re.match(r'^https?://|^ftp://', v, re.IGNORECASE):
        return "url"
    # Email MUST come before domain — emails contain dots like domains
    if re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', v):
        return "email"
    if re.match(r'^AS\d+$', v, re.IGNORECASE):
        return "asn"
    return "domain"
