"""LLM generation service with Gemini-primary / Groq-fallback strategy.

Purpose
-------
Provides ``GeminiClient`` as the primary LLM for compliance answer generation.
When Gemini fails for any reason (quota exhausted, rate limit, API error),
the client automatically retries the same request using ``GroqClient`` so the
system stays available even when the Gemini free tier is exhausted.

Architecture Integration
------------------------
* Phase 5 (baseline): ``BaselineRAGPipeline`` calls ``GeminiClient`` directly.
  Groq fallback is transparent — the pipeline sees a single client interface.
* Phase 9+ (agents): LangGraph nodes will call this client for specialised
  tasks (classification, violation detection, recommendation generation).
  The fallback strategy applies to all of them automatically.

Fallback chain
--------------
1. Try Gemini ``generate_content`` (primary).
2. On any exception → log the error, instantiate ``GroqClient`` lazily, retry.
3. If Groq also fails → raise the Groq exception.
4. ``GeminiClient.active_model`` always reflects the provider that answered.

Embedding note
--------------
Groq does not offer embedding models. The fallback is generation-only.
``EmbeddingsService`` (embeddings.py) continues to use Gemini exclusively.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.rag import RetrievedChunk

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
    """Format retrieved chunks into a numbered context block with citation headers.

    Shared between both Gemini and Groq so both providers see identical context.
    """
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


# ── Groq client ────────────────────────────────────────────────────────────────

class GroqClient:
    """Groq LLM client used as fallback when Gemini is unavailable.

    Uses the OpenAI-compatible Groq Chat Completions API. The same system
    prompt and context format as ``GeminiClient`` are applied so answer
    quality is consistent across providers.

    Parameters
    ----------
    settings:
        Application settings. Reads ``groq_api_key`` and ``groq_model``.
    """

    def __init__(self, settings: Settings) -> None:
        if settings.groq_api_key is None:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file to enable the Groq fallback."
            )
        from groq import Groq  # lazy import — only needed when fallback is triggered

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


# ── Gemini client (primary) ────────────────────────────────────────────────────

class GeminiClient:
    """Primary Gemini LLM client with automatic Groq fallback.

    On any Gemini failure (quota, rate limit, network error), the request is
    transparently retried via ``GroqClient``. The ``active_model`` property
    always reflects which provider answered the last request.

    Parameters
    ----------
    settings:
        Application settings. Reads ``gemini_*`` and ``groq_*`` fields.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        resolved = settings or get_settings()
        if resolved.gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")

        self._client = genai.Client(api_key=resolved.gemini_api_key.get_secret_value())
        self._gemini_model = resolved.gemini_model
        self._generation_config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2048,
            top_p=0.95,
            system_instruction=_SYSTEM_PROMPT,
        )

        # Build Groq fallback if key is present — failure here is non-fatal
        self._fallback: GroqClient | None = None
        if resolved.groq_api_key is not None:
            try:
                self._fallback = GroqClient(settings=resolved)
            except Exception as exc:
                logger.warning("Groq fallback could not be initialised: %s", exc)

        # Tracks the provider that answered the most recent request
        self._active_model: str = self._gemini_model
        logger.info(
            "GeminiClient ready — primary=%s  fallback=%s",
            self._gemini_model,
            self._fallback.model_name if self._fallback else "none",
        )

    @property
    def model_name(self) -> str:
        """Primary Gemini model identifier (regardless of which provider answered)."""
        return self._gemini_model

    @property
    def active_model(self) -> str:
        """The provider/model that answered the last ``generate_compliance_answer`` call.

        Returns ``"gemini/<model>"`` or ``"groq/<model>"`` so callers can
        surface which backend was used in the API response.
        """
        return self._active_model

    def generate_compliance_answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Generate a cited compliance answer, falling back to Groq on failure.

        Steps
        -----
        1. Try Gemini ``generate_content``.
        2. On any exception: if Groq fallback is configured, log and retry.
        3. If Groq also fails, raise its exception.
        4. Always update ``self._active_model`` to reflect which provider answered.
        """
        context = _format_context(chunks)
        prompt = _USER_TEMPLATE.format(context=context, question=question)

        # ── Primary: Gemini ────────────────────────────────────────────────────
        try:
            logger.debug("Generating answer via Gemini (model=%s).", self._gemini_model)
            response = self._client.models.generate_content(
                model=self._gemini_model,
                contents=prompt,
                config=self._generation_config,
            )
            answer = self._extract_text(response)
            self._active_model = f"gemini/{self._gemini_model}"
            return answer

        except Exception as gemini_exc:
            logger.warning(
                "Gemini generation failed (%s: %s).",
                type(gemini_exc).__name__,
                str(gemini_exc)[:200],
            )

            # ── Fallback: Groq ─────────────────────────────────────────────────
            if self._fallback is None:
                logger.error(
                    "Gemini failed and no Groq fallback is configured. "
                    "Set GROQ_API_KEY in .env to enable fallback."
                )
                raise

            logger.info(
                "Retrying with Groq fallback (model=%s).", self._fallback.model_name
            )
            try:
                answer = self._fallback.generate_compliance_answer(question, chunks)
                self._active_model = f"groq/{self._fallback.model_name}"
                return answer
            except Exception as groq_exc:
                logger.error(
                    "Groq fallback also failed: %s. Both providers exhausted.",
                    groq_exc,
                )
                raise groq_exc from gemini_exc

    # ── Static helpers ─────────────────────────────────────────────────────────

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
