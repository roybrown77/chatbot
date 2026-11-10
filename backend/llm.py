import os

import httpx

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


async def chat_completion(system: str, user: str) -> str:
    """Call Ollama's chat API (free, local)."""
    url = f"{OLLAMA_BASE.rstrip('/')}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    message = data.get("message") or {}
    return (message.get("content") or "").strip()


async def health_check() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_BASE.rstrip('/')}/api/tags")
            if r.status_code != 200:
                return False, f"Ollama returned {r.status_code}"
            models = [m.get("name", "") for m in r.json().get("models", [])]
            if not any(OLLAMA_MODEL.split(":")[0] in m for m in models):
                return (
                    False,
                    f"Model '{OLLAMA_MODEL}' not found. Run: ollama pull {OLLAMA_MODEL.split(':')[0]}",
                )
            return True, "ok"
    except httpx.RequestError as e:
        return False, f"Cannot reach Ollama at {OLLAMA_BASE}: {e}"
