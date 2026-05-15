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
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.xposedornot.com/v1/check-email/{email}",
                headers=_HEADERS,
            )
            if r.status_code == 404:
                return {"exposed": False, "breach_count": 0, "breaches": [], "message": "No breaches found"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            data = r.json()
            exposed = data.get("ExposedBreaches", {})
            breaches_list = exposed.get("breaches_details", [])
            breach_count = len(breaches_list)

            breach_info = []
            for b in breaches_list:
                breach_info.append({
                    "name": b.get("breach", ""),
                    "date": b.get("xposed_date", ""),
                    "records": b.get("xposed_records", 0),
                    "data_classes": b.get("xposed_data", "").split(";") if b.get("xposed_data") else [],
                })

            paste_count = 0
            metrics = data.get("BreachMetrics", {})
            if metrics:
                pastes = metrics.get("pastes", [])
                if pastes and isinstance(pastes[0], dict):
                    paste_count = pastes[0].get("cnt", 0)

            return {
                "exposed": breach_count > 0,
                "breach_count": breach_count,
                "breaches": breach_info[:10],
                "paste_count": paste_count,
            }
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
