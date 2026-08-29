import urllib.parse

import aiohttp

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class QuotaError(Exception):
    """Raised when a key/model combo is rate-limited or out of credit."""


class ProviderError(Exception):
    """Raised on any other API failure."""


async def chat_completion(model_id: str, api_key: str, messages: list) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/",  # OpenRouter asks apps to identify themselves
        "X-Title": "MultiModelAggregatorBot",
    }
    payload = {"model": model_id, "messages": messages}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            OPENROUTER_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=90)
        ) as resp:
            try:
                data = await resp.json()
            except Exception:
                text = await resp.text()
                raise ProviderError(f"Non-JSON response ({resp.status}): {text[:300]}")

            if resp.status == 429:
                raise QuotaError(str(data))
            err = data.get("error") if isinstance(data, dict) else None
            if err and err.get("code") in (429, "insufficient_quota", "rate_limit_exceeded"):
                raise QuotaError(str(err))
            if resp.status >= 400:
                raise ProviderError(f"{resp.status}: {data}")

            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise ProviderError(f"Unexpected response shape: {data}")


async def generate_image_url(prompt: str) -> str:
    """Pollinations.ai - free, no API key, no account required."""
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}"
