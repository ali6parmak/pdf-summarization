import time
from typing import Optional

from ollama import Client

from configuration import LLM_HOST, LLM_MODEL, LLM_TEMPERATURE

_client: Optional[Client] = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(host=LLM_HOST) if LLM_HOST else Client()
    return _client


def ask_llm(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = LLM_TEMPERATURE,
    max_retries: int = 2,
) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_error: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        try:
            response = _get_client().chat(
                model=LLM_MODEL,
                messages=messages,
                options={"temperature": temperature},
            )
            return response["message"]["content"].strip()
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                raise

    raise RuntimeError(f"ask_llm failed after retries: {last_error}")
