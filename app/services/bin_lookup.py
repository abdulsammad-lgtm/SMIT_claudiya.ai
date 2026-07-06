import httpx
from typing import Optional


BIN_API_PRIMARY = "https://api.binslookup.com/v2/{bin}"
BIN_API_FALLBACK = "https://lookup.binlist.net/{bin}"
BIN_LOOKUP_TIMEOUT = 2.0


async def lookup_bin(card_bin: str) -> Optional[dict]:
    result = await _try_bin_api(BIN_API_PRIMARY.format(bin=card_bin))
    if result:
        return result
    result = await _try_bin_api(BIN_API_FALLBACK.format(bin=card_bin))
    if result:
        return result
    return None


async def _try_bin_api(url: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=BIN_LOOKUP_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            data = response.json()
            return _normalize_bin_response(data)
    except (httpx.TimeoutException, httpx.RequestError, ValueError):
        return None


def _normalize_bin_response(data: dict) -> dict:
    if "country" in data and "card_type" in data:
        return {
            "country_code": data.get("country", {}).get("code", ""),
            "card_type": data.get("card_type", ""),
            "card_brand": data.get("scheme", ""),
            "issuing_bank": data.get("bank", {}).get("name", ""),
        }
    if "country" in data and "type" in data:
        return {
            "country_code": data.get("country", {}).get("alpha2", ""),
            "card_type": data.get("type", ""),
            "card_brand": data.get("scheme", ""),
            "issuing_bank": data.get("bank", {}).get("name", ""),
        }
    return {
        "country_code": data.get("country_code", data.get("country", "")),
        "card_type": data.get("card_type", data.get("type", "")),
        "card_brand": data.get("card_brand", data.get("scheme", "")),
        "issuing_bank": data.get("issuing_bank", data.get("bank", "")),
    }
