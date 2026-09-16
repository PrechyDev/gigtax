import base64
import logging
import time
import instructor
from litellm import completion, embedding
from pydantic import BaseModel
from typing import Type, Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)

# gemini-embedding-001 is the only Gemini embedding model currently available via the
# Gemini API (text-embedding-004 has been retired) — verified with a real call before
# wiring this up. 3072 dimensions is its default output_dimensionality.
EMBEDDING_MODEL = "gemini/gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072

# Every LLM call gets this ceiling so a hung request fails fast (and can be retried/
# failed-over) instead of tying up a worker thread indefinitely.
REQUEST_TIMEOUT_SECONDS = 30

# Substrings that mean "transient, worth retrying/failing over" — deliberately broad.
# Found in production: a plain 429 is the easy case, but Gemini also fails with
# `503 UNAVAILABLE "high demand"` and bare connection drops
# (`RemoteProtocolError: Server disconnected without sending a response`) that don't
# mention 429/quota anywhere — those used to fall straight through with zero retries.
TRANSIENT_ERROR_SUBSTRINGS = (
    "429", "rate limit", "resourceexhausted", "quota",
    "503", "unavailable", "overloaded", "high demand",
    "server disconnected", "timeout", "timed out", "connection",
)


def _is_transient_error(error: Exception) -> bool:
    error_msg = str(error).lower()
    return any(s in error_msg for s in TRANSIENT_ERROR_SUBSTRINGS)


class LLMService:
    """
    Centralized service for all LLM interactions (Text, Vision, Structured Output, RAG).
    Handles standard settings, error logging, and client wrapping.
    """

    def __init__(self):
        # We can add global settings for litellm here (retries, timeouts, fallbacks)
        self.default_text_model = settings.CATEGORIZATION_MODEL
        self.default_vision_model = "gemini/gemini-3.5-flash"

        # Initialize the Instructor-patched client for structured outputs
        self.structured_client = instructor.from_litellm(completion, mode=instructor.Mode.JSON)

    def _execute_with_fallbacks(self, func, primary_model, *args, **kwargs):
        """
        Executes an LLM function, catching transient failures and looping through
        fallback models — a rate limit is the obvious case, but Gemini overload
        (503) and bare connection drops are just as real and must trigger the same
        cascade (see TRANSIENT_ERROR_SUBSTRINGS).
        """
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
        try:
            return func(model=primary_model, *args, **kwargs)
        except Exception as e:
            if _is_transient_error(e):
                fallbacks = ["gemini/gemini-3.6-flash", "gemini/gemini-2.5-flash", "gemini/gemini-3.5-flash-lite"]
                for fb in fallbacks:
                    logger.warning(f"Transient failure on {primary_model} ({e}). Trying fallback {fb}.")
                    try:
                        return func(model=fb, *args, **kwargs)
                    except Exception as fallback_e:
                        if _is_transient_error(fallback_e):
                            continue
                        logger.error(f"LLM generation failed on fallback {fb}: {fallback_e}")
                        raise fallback_e
                logger.error("All fallback models exhausted due to transient failures.")
                raise e
            logger.error(f"LLM generation failed: {e}")
            raise e

    def generate_structured_output(self, prompt: str, response_model: Type[BaseModel], system_prompt: Optional[str] = None, model: Optional[str] = None) -> Any:
        """
        Forces the LLM to return data matching a specific Pydantic schema.
        Used heavily for Categorization and data extraction.
        """
        target_model = model or self.default_text_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self._execute_with_fallbacks(
            self.structured_client.chat.completions.create,
            target_model,
            response_model=response_model,
            messages=messages
        )

    def generate_vision_text(self, prompt: str, file_bytes: bytes, mime_type: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Multimodal generation for reading scanned documents or images.
        """
        target_model = model or self.default_vision_model
        base64_file = base64.b64encode(file_bytes).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_file}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": data_url}
                }
            ]
        })

        response = self._execute_with_fallbacks(
            completion,
            target_model,
            messages=messages
        )
        return response.choices[0].message.content

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[list[dict]] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Standard text completion for generic conversational or RAG tasks.

        `history` is prior turns as [{"role": "user"/"assistant", "content": "..."}],
        oldest first — this is Gemini's actual multi-turn mechanism (there's no
        server-side conversation memory; its own "chat session" abstraction just
        resends prior turns like this on every call), so passing it straight through
        is the "built-in" way rather than something built alongside it.
        """
        target_model = model or self.default_text_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        response = self._execute_with_fallbacks(
            completion,
            target_model,
            messages=messages
        )
        return response.choices[0].message.content

    def generate_embedding(self, text: str, max_retries: int = 5) -> list[float]:
        """Embeds a single string (a query, or one knowledge-base chunk) for RAG
        retrieval. No fallback *model* here — there's only one Gemini embedding model
        available, unlike the chat/vision models above — but bulk document ingestion
        makes many calls back-to-back, so a transient failure (rate limit, 503
        overload, a bare dropped connection) gets retried with exponential backoff
        rather than aborting the whole ingestion run or a single interactive query.
        """
        for attempt in range(max_retries):
            try:
                response = embedding(model=EMBEDDING_MODEL, input=[text], timeout=REQUEST_TIMEOUT_SECONDS)
                return response.data[0]["embedding"]
            except Exception as e:
                if _is_transient_error(e) and attempt < max_retries - 1:
                    wait_seconds = 2 ** attempt * 5  # 5s, 10s, 20s, 40s, ...
                    logger.warning(f"Embedding call failed transiently ({e}), retrying in {wait_seconds}s (attempt {attempt + 1}/{max_retries}).")
                    time.sleep(wait_seconds)
                    continue
                logger.error(f"Embedding generation failed: {e}")
                raise


# Singleton instance to be imported across the application
llm_service = LLMService()
