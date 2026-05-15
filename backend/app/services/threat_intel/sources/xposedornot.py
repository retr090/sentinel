import httpx

_HEADERS = {"User-Agent": "SENTINEL-OSINT/1.0"}


async def lookup(ioc_type: str, value: str) -> dict:
    if ioc_type == "email":
        return await check_email(value)
    elif ioc_type == "domain":
        return await check_domain(value)
    return {"error": "unsupported ioc type"}


async def check_email(email: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(
                f"https://api.xposedornot.com/v1/check-email/{email}",
                headers={**_HEADERS, "Accept": "application/json"},
            )
            if r.status_code == 404:
                return {"exposed": False, "breach_count": 0, "breaches": [], "paste_count": 0, "message": "No breaches found"}
            if r.status_code == 400:
                return {"error": "invalid_email"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            try:
                data = r.json()
            except Exception:
                return {"error": "invalid_json"}

            # Format 1: authenticated API — {"ExposedBreaches": {"breaches_details": [...], ...}, "BreachMetrics": {...}}
            if "ExposedBreaches" in data:
                exposed = data["ExposedBreaches"]
                breaches_list = exposed.get("breaches_details", [])
                breach_info = []
                for b in breaches_list:
                    breach_info.append({
                        "name": b.get("breach", ""),
                        "date": b.get("xposed_date", ""),
                        "records": b.get("xposed_records", 0),
                        "data_classes": [
                            d.strip() for d in b.get("xposed_data", "").split(";") if d.strip()
                        ],
                    })
                metrics = data.get("BreachMetrics", {})
                paste_count = 0
                if metrics:
                    pastes = metrics.get("pastes", [])
                    if pastes and isinstance(pastes, list):
                        paste_count = pastes[0].get("cnt", 0) if pastes else 0
                breach_count = len(breach_info)
                return {
                    "exposed": breach_count > 0,
                    "breach_count": breach_count,
                    "breaches": breach_info[:10],
                    "paste_count": paste_count,
                }

            # Format 2: public API — {"breaches": [["Name1","Name2",...]], "status": "success"}
            if "breaches" in data:
                raw = data["breaches"]
                if raw and isinstance(raw[0], list):
                    # nested list format
                    breach_names = raw[0]
                elif raw and isinstance(raw[0], str):
                    # flat list format
                    breach_names = raw
                elif raw and isinstance(raw[0], dict):
                    # list-of-dicts format
                    return {
                        "exposed": len(raw) > 0,
                        "breach_count": len(raw),
                        "breaches": raw[:10],
                        "paste_count": 0,
                    }
                else:
                    breach_names = []
                breach_count = len(breach_names)
                breach_info = [{"name": n, "date": "", "records": 0, "data_classes": []} for n in breach_names]
                return {
                    "exposed": breach_count > 0,
                    "breach_count": breach_count,
                    "breaches": breach_info[:10],
                    "paste_count": 0,
                }

            # Format 3: single breach key
            if "breach" in data:
                return {
                    "exposed": True,
                    "breach_count": 1,
                    "breaches": [data["breach"]],
                    "paste_count": 0,
                }

            return {"exposed": False, "breach_count": 0, "breaches": [], "paste_count": 0, "raw": data}

    except httpx.TimeoutException:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


async def check_domain(domain: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.xposedornot.com/v1/domain-breaches/{domain}",
                headers=_HEADERS,
            )
            if r.status_code == 404:
                return {"exposed": False, "breach_count": 0, "exposed_emails": 0}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            data = r.json()
            return {
                "exposed": True,
                "breach_count": data.get("breaches_count", 0),
                "exposed_emails": data.get("exposed_emails", 0),
                "breaches": data.get("breaches", [])[:10],
                "first_breach": data.get("first_breach"),
                "latest_breach": data.get("latest_breach"),
            }
    except Exception as e:
        return {"error": str(e)}
