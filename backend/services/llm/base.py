"""Base LLM provider interface — all providers implement this."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.config import SUPPORTED_LANGUAGES


# System prompt grounding the LLM as a legal information assistant
LEGAL_SYSTEM_PROMPT = """You are Lexaro, an AI legal information assistant for India.

PERSONALITY:
- You are warm, empathetic, and conversational — like a knowledgeable friend explaining the law.
- NEVER dump raw templates, bullet lists of sections, or wall-of-text legal jargon.
- Respond in a natural chatbot style: short paragraphs, plain language, as if talking to someone.

GROUNDING (CRITICAL — anti-hallucination):
- You may ONLY reference section numbers and laws provided in the context below.
- If a section is NOT in the context, do NOT mention it. Say "I don't have information on that."
- NEVER invent, guess, or hallucinate section numbers, punishments, or legal provisions.
- If unsure, say so honestly rather than fabricating an answer.

RESPONSE FORMAT:
1. Start with a brief, empathetic acknowledgment of what the user asked.
2. Explain the most relevant section(s) in 2-3 short paragraphs using simple language.
3. Mention key facts: punishment, whether it's bailable/non-bailable, cognizable/non-cognizable.
4. If appropriate, briefly mention possible defences or next steps.
5. End with a short reminder to consult a lawyer for their specific case.
6. Keep the TOTAL response under 250 words. Be concise.

LANGUAGE:
- If the user's language is not English, respond in that language.
- Always keep section numbers and legal terms (like "BNS", "IPC") in English.

ABSOLUTE RULES:
- NEVER advise the user to break the law or evade justice.
- NEVER provide specific legal advice — only information.
- NEVER fabricate section numbers or laws not in the provided context.
"""


def format_sections_context(sections: list[dict]) -> str:
    """Format retrieved sections into a context block for the LLM prompt."""
    if not sections:
        return "No relevant legal sections found."

    lines = []
    for s in sections:
        law_label = "BNS 2023" if s.get("law") == "BNS" else "IPC 1860"
        bail = "Bailable" if s.get("bailable") else "Non-bailable"
        cog = "Cognizable" if s.get("cognizable") else "Non-cognizable"
        lines.append(
            f"- {s['section_id']} ({law_label}): {s['title']}\n"
            f"  Description: {s['description']}\n"
            f"  Punishment: {s.get('punishment', 'Not specified')}\n"
            f"  Status: {cog}, {bail}\n"
            f"  Relevance score: {s.get('score', 0):.0%}"
        )
    return "\n".join(lines)


def get_language_instruction(language: str) -> str:
    """Return a language instruction for the LLM based on the user's language."""
    lang_name = SUPPORTED_LANGUAGES.get(language, "English")
    if language == "en-IN" or language.startswith("en"):
        return "Respond in English."
    return f"Respond in {lang_name} ({language}). Keep legal terms and section numbers in English."


def build_messages(query: str, sections: list[dict], language: str) -> list[dict]:
    """Build the chat messages array for any LLM provider."""
    context = format_sections_context(sections)
    lang_instruction = get_language_instruction(language)
    return [
        {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User's question: {query}\n\n"
                f"CONTEXT — these are the ONLY sections you may reference:\n{context}\n\n"
                f"{lang_instruction}\n\n"
                "Reply conversationally in 2-3 short paragraphs. "
                "Do NOT dump a template or raw list. "
                "Only cite sections from the context above — never invent any."
            ),
        },
    ]


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'gemini', 'ollama')."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is ready to serve requests."""

    @abstractmethod
    def generate(self, query: str, sections: list[dict], language: str = "en-IN") -> str | None:
        """Generate a legal response. Returns None on failure."""
