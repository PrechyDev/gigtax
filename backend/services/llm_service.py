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
        self.structured_client = instructor.from_litellm(completion)

    def _execute_with_fallbacks(self, func, primary_model, *args, **kwargs):
        """
        Executes an LLM function, catching rate limits and looping through fallbacks.
        """
        try:
            return func(model=primary_model, *args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg:
                fallbacks = ["gemini/gemini-3.6-flash", "gemini/gemini-2.5-flash", "gemini/gemini-3.5-flash-lite"]
                for fb in fallbacks:
                    logger.warning(f"Rate limit hit on {primary_model}. Trying fallback {fb}.")
                    try:
                        return func(model=fb, *args, **kwargs)
                    except Exception as fallback_e:
                        fb_error_msg = str(fallback_e).lower()
                        if "429" in fb_error_msg or "rate limit" in fb_error_msg or "resourceexhausted" in fb_error_msg:
                            continue
                        logger.error(f"LLM generation failed on fallback {fb}: {fallback_e}")
                        raise fallback_e
                logger.error("All fallback models exhausted due to rate limits.")
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

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Standard text completion for generic conversational or RAG tasks.
        """
        target_model = model or self.default_text_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
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
        makes many calls back-to-back, so a rate limit (429) gets retried with
        exponential backoff rather than aborting the whole ingestion run.
        """
        for attempt in range(max_retries):
            try:
                response = embedding(model=EMBEDDING_MODEL, input=[text])
                return response.data[0]["embedding"]
            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = any(s in error_msg for s in ("429", "rate limit", "resourceexhausted", "quota"))
                if is_rate_limit and attempt < max_retries - 1:
                    wait_seconds = 2 ** attempt * 5  # 5s, 10s, 20s, 40s, ...
                    logger.warning(f"Embedding rate-limited, retrying in {wait_seconds}s (attempt {attempt + 1}/{max_retries}).")
                    time.sleep(wait_seconds)
                    continue
                logger.error(f"Embedding generation failed: {e}")
                raise


# Singleton instance to be imported across the application
llm_service = LLMService()
