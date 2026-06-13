"""LLM generation service with Groq-primary / Gemini-fallback strategy.

Purpose
-------
Provides ``GeminiClient`` as the unified LLM interface for compliance answer
generation. Groq is the primary provider (fast, low-latency). When Groq fails
due to a rate-limit or any error, the client automatically retries via Gemini
so the system stays available.

Architecture Integration
------------------------
* Phase 5 (baseline): ``BaselineRAGPipeline`` calls ``GeminiClient`` directly.
  The primary/fallback swap is transparent — the pipeline sees one interface.
* Phase 9+ (agents): LangGraph nodes call this client for all generation tasks.
  The fallback strategy applies automatically.

Fallback chain
--------------
1. Try Groq ``chat.completions.create`` (primary — fast, free tier).
2. On any exception → log the error, retry via Gemini if configured.
3. If Gemini also fails → raise the Gemini exception.
4. ``GeminiClient.active_model`` always reflects the provider that answered.

Rate-limit retry
----------------
Groq RateLimitErrors are retried with exponential backoff before the fallback
is triggered. Delays: 2 s → 4 s (max 2 retries, total wait ≤ 6 s).
This is intentionally short so the frontend does not time out.

Embedding note
--------------
Groq does not offer embedding models. ``EmbeddingsService`` (embeddings.py)
continues to use Gemini exclusively.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING, Callable, TypeVar

_T = TypeVar("_T")

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.rag import RetrievedChunk

if TYPE_CHECKING:
    import redis as redis_lib

logger = logging.getLogger(__name__)

# ── Shared prompts ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT: str = """You are an authoritative ADGM (Abu Dhabi Global Market) compliance assistant.
You serve compliance officers, legal teams, and business owners operating in the ADGM financial free zone.

RULES — follow these strictly:
1. Base your answer ONLY on the regulatory context provided below. Do not use any outside knowledge.
2. If the provided context does not contain enough information to answer the question, respond with:
   "The provided regulatory context does not contain sufficient information to answer this question. Please consult an ADGM-accredited compliance professional."
3. Cite every regulatory claim using this exact format: [Source: <document title>, <rule/article reference>]
4. Use precise regulatory language. Never paraphrase a rule loosely.
5. If the question spans multiple regulations, address each one in order.
6. Structure multi-part answers with numbered lists or clear headings.
7. Never speculate, infer, or advise beyond what the regulations explicitly state.
8. Never fabricate regulation names, article numbers, or compliance dates."""

_USER_TEMPLATE: str = """\
=== REGULATORY CONTEXT ===
{context}
=== END CONTEXT ===

Question: {question}

Provide a precise, citation-backed answer using only the regulatory context above."""


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a numbered context block with citation headers."""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        header_parts: list[str] = []
        if chunk.source_title:
            header_parts.append(f"Source: {chunk.source_title}")
        if chunk.rule_reference:
            header_parts.append(f"Ref: {chunk.rule_reference}")
        if chunk.heading:
            header_parts.append(f"Section: {chunk.heading}")
        header = " | ".join(header_parts) if header_parts else f"Chunk {i}"
        parts.append(f"[{i}] {header}\n{chunk.text.strip()}")
    return "\n\n".join(parts)


# ── Groq retry helper ──────────────────────────────────────────────────────────

def _groq_with_retry(fn: Callable[[], _T], max_retries: int = 2, base_delay: float = 2.0) -> _T:
    """Call fn(), retrying on Groq RateLimitError with exponential backoff.

    Delays: 2 s → 4 s (max 2 retries, total wait ≤ 6 s).
    Kept short so the fallback to Gemini triggers quickly on sustained rate limits.
    """
    from groq import RateLimitError

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except RateLimitError as exc:
            if attempt == max_retries:
                logger.error(
                    "Groq rate limit exceeded after %d retries — handing off to Gemini fallback.",
                    max_retries,
                )
                raise
            wait = base_delay * (2 ** attempt)
            logger.warning(
                "Groq rate limited — waiting %.0fs before retry %d/%d.",
                wait, attempt + 1, max_retries,
            )
            time.sleep(wait)

    raise RuntimeError("unreachable")  # type: ignore[return-value]


# ── Groq client (primary) ──────────────────────────────────────────────────────

class GroqClient:
    """Groq LLM client — primary provider for fast, low-latency generation.

    Uses the OpenAI-compatible Groq Chat Completions API with the same system
    prompt and context format so answer quality is consistent across providers.

    Parameters
    ----------
    settings:
        Application settings. Reads ``groq_api_key`` and ``groq_model``.
    """

    def __init__(self, settings: Settings) -> None:
        if settings.groq_api_key is None:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        from groq import Groq

        self._client = Groq(api_key=settings.groq_api_key.get_secret_value())
        self._model_name = settings.groq_model
        logger.info("GroqClient ready — model=%s", self._model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_compliance_answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Generate a cited compliance answer using Groq."""
        context = _format_context(chunks)
        prompt = _USER_TEMPLATE.format(context=context, question=question)

        logger.info("Generating answer via Groq (model=%s).", self._model_name)

        def _call() -> str:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""

        return _groq_with_retry(_call)

    def generate_text(self, prompt: str) -> str:
        """Raw single-turn generation without the compliance system instruction.

        Used by the re-ranker and other utility tasks (classification,
        structured extraction) that only need a short, deterministic response.
        """
        def _call() -> str:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""

        return _groq_with_retry(_call)


# ── Gemini fallback ────────────────────────────────────────────────────────────

class _GeminiFallback:
    """Internal Gemini client used only when Groq is unavailable.

    Instantiated lazily during ``GeminiClient.__init__`` if GEMINI_API_KEY is
    present. All Google SDK imports are kept inside this class so the service
    starts successfully even when the google-genai package is absent.
    """

    def __init__(self, settings: Settings) -> None:
        from google import genai
        from google.genai import types

        self._genai = genai
        self._types = types
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())  # type: ignore[union-attr]
        self._model = settings.gemini_model
        self._gen_config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2048,
            top_p=0.95,
            system_instruction=_SYSTEM_PROMPT,
        )
        logger.info("Gemini fallback ready — model=%s", self._model)

    @property
    def model_name(self) -> str:
        return self._model

    def generate_compliance_answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Generate a cited compliance answer using Gemini."""
        context = _format_context(chunks)
        prompt = _USER_TEMPLATE.format(context=context, question=question)
        logger.info("Generating answer via Gemini fallback (model=%s).", self._model)
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._gen_config,
        )
        return self._extract_text(response)

    def generate_text(self, prompt: str) -> str:
        """Raw single-turn generation without the compliance system instruction."""
        config = self._types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=2048,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return self._extract_text(response)

    @staticmethod
    def _extract_text(response: object) -> str:
        """Safely extract text from a Gemini response, handling blocked output."""
        try:
            text = response.text  # type: ignore[union-attr]
            if text:
                return text
        except (ValueError, AttributeError):
            pass
        logger.warning("Gemini returned an empty or blocked response.")
        return (
            "The model was unable to generate a response for this query. "
            "This may be due to content restrictions. Please rephrase your question."
        )


# ── Unified LLM client — Groq primary / Gemini fallback ───────────────────────

class GeminiClient:
    """Unified LLM client: Groq is the primary provider, Gemini is the fallback.

    The class retains the name ``GeminiClient`` for backward compatibility with
    all existing callers (agents, RAG pipeline, re-ranker). Internally, every
    generation request tries Groq first; Gemini is only invoked when Groq is
    unavailable.

    Parameters
    ----------
    settings:
        Application settings. ``groq_api_key`` is required; ``gemini_api_key``
        is optional and enables the fallback.
    redis_client:
        Optional Redis connection for ``generate_text`` response caching
        (Phase 16).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        redis_client: "redis_lib.Redis | None" = None,
    ) -> None:
        resolved = settings or get_settings()

        # ── Primary: Groq (required) ───────────────────────────────────────────
        if resolved.groq_api_key is None:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file to enable the primary LLM."
            )
        self._primary = GroqClient(settings=resolved)

        # ── Fallback: Gemini (optional) ────────────────────────────────────────
        self._fallback: _GeminiFallback | None = None
        if resolved.gemini_api_key is not None:
            try:
                self._fallback = _GeminiFallback(resolved)
            except Exception as exc:
                logger.warning("Gemini fallback could not be initialised: %s", exc)

        # Phase 16: Redis for generate_text caching (HyDE, CRAG, Self-RAG, re-ranker)
        self._redis = redis_client
        self._gentext_ttl = 60 * 60  # 1 hour

        self._active_model: str = f"groq/{self._primary.model_name}"
        logger.info(
            "LLMClient ready — primary=groq/%s  fallback=%s  cache=%s",
            self._primary.model_name,
            f"gemini/{self._fallback.model_name}" if self._fallback else "none",
            "redis" if self._redis else "none",
        )

    @property
    def model_name(self) -> str:
        """Primary Groq model identifier."""
        return self._primary.model_name

    @property
    def active_model(self) -> str:
        """The provider/model that answered the last generation call.

        Returns ``"groq/<model>"`` or ``"gemini/<model>"`` so callers can
        surface which backend was used in the API response.
        """
        return self._active_model

    def generate_compliance_answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Generate a cited compliance answer via Groq, falling back to Gemini.

        Steps
        -----
        1. Try Groq (with up to 2 rate-limit retries, max 6 s wait).
        2. On any exception: if Gemini fallback is configured, log and retry.
        3. If Gemini also fails, raise its exception.
        4. Always update ``self._active_model`` to reflect which provider answered.
        """
        # ── Primary: Groq ──────────────────────────────────────────────────────
        try:
            answer = self._primary.generate_compliance_answer(question, chunks)
            self._active_model = f"groq/{self._primary.model_name}"
            return answer

        except Exception as groq_exc:
            logger.warning(
                "Groq generation failed (%s: %s).",
                type(groq_exc).__name__,
                str(groq_exc)[:200],
            )

            # ── Fallback: Gemini ───────────────────────────────────────────────
            if self._fallback is None:
                logger.error(
                    "Groq failed and no Gemini fallback is configured. "
                    "Set GEMINI_API_KEY in .env to enable the fallback."
                )
                raise

            logger.info(
                "Retrying with Gemini fallback (model=%s).", self._fallback.model_name
            )
            try:
                answer = self._fallback.generate_compliance_answer(question, chunks)
                self._active_model = f"gemini/{self._fallback.model_name}"
                return answer
            except Exception as gemini_exc:
                logger.error(
                    "Gemini fallback also failed: %s. Both providers exhausted.",
                    gemini_exc,
                )
                raise gemini_exc from groq_exc

    def generate_text(self, prompt: str) -> str:
        """Raw single-turn generation without the compliance system instruction.

        Used by the re-ranker and other utility tasks (classification,
        structured extraction) that need a short, deterministic response.
        Falls back to Gemini on Groq failure.

        Phase 16: results are cached in Redis by SHA-256(prompt) with a 1-hour TTL.
        Cache is provider-agnostic — a Groq answer is equally cacheable.
        """
        cache_key = self._gentext_cache_key(prompt)

        # ── Cache hit ──────────────────────────────────────────────────────────
        if self._redis is not None:
            try:
                cached = self._redis.get(cache_key)
                if cached:
                    logger.debug("generate_text cache HIT  key=%.20s…", cache_key)
                    return json.loads(cached)
            except Exception as exc:
                logger.debug("generate_text cache get failed: %s", exc)

        # ── LLM call ───────────────────────────────────────────────────────────
        result: str
        try:
            result = self._primary.generate_text(prompt)
            self._active_model = f"groq/{self._primary.model_name}"
        except Exception as exc:
            logger.warning(
                "Groq generate_text failed (%s: %s), trying Gemini.",
                type(exc).__name__,
                str(exc)[:120],
            )
            if self._fallback is None:
                raise
            result = self._fallback.generate_text(prompt)
            self._active_model = f"gemini/{self._fallback.model_name}"

        # ── Cache store ────────────────────────────────────────────────────────
        if self._redis is not None and result:
            try:
                self._redis.set(cache_key, json.dumps(result), ex=self._gentext_ttl)
                logger.debug(
                    "generate_text cache SET  key=%.20s…  ttl=%ds", cache_key, self._gentext_ttl
                )
            except Exception as exc:
                logger.debug("generate_text cache set failed: %s", exc)

        return result

    def _gentext_cache_key(self, prompt: str) -> str:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:24]
        return f"gentext:{digest}"

    @staticmethod
    def _extract_text(response: object) -> str:
        """Kept for backward compatibility. Delegates to Gemini response extraction."""
        try:
            text = response.text  # type: ignore[union-attr]
            if text:
                return text
        except (ValueError, AttributeError):
            pass
        logger.warning("Model returned an empty or blocked response.")
        return (
            "The model was unable to generate a response for this query. "
            "This may be due to content restrictions. Please rephrase your question."
        )
