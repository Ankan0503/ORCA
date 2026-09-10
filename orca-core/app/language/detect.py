"""Language identification for user queries.

Two very different cases, handled differently:

1. Native script ("আজ সমুদ্র কেমন?") — the Unicode block *is* the answer. This is
   deterministic, instant and free, so it never goes near a model.
2. Romanised or code-mixed ("aaj samudra kaisa hai", "machh kothay pabo") — the
   characters are all Latin, so script tells us nothing. Frequency-based
   detectors are notoriously bad here; they see Latin and guess English. This
   case is deferred to the LLM, which judges it semantically.

Voice input skips both: Sarvam's speech-to-text returns the detected
`language_code` itself when asked with `language_code="unknown"`.
"""

from dataclasses import dataclass

# Languages the ORCA frontend ships translations for.
# The languages ORCA speaks, mapped to Sarvam's BCP-47 codes.
#
# This list must cover every language the app's own selector offers, and for a
# long time it did not: the selector offered nine and this held six. The three
# missing ones — Marathi, Gujarati and Odia — fell through `to_sarvam_code`'s
# default and were handed to Sarvam as "en-IN", so a Marathi user's answer was
# translated from English into English and spoken back in English. Nothing
# errored; the request succeeded and returned the input unchanged, which is why
# it survived so long.
#
# Odia is "od-IN" at Sarvam while the app uses the ISO code "or". That mismatch
# is exactly the kind of thing a default swallows, so it is written out here.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "or": "od-IN",
}

# Unicode ranges that identify a script unambiguously.
_SCRIPT_RANGES: list[tuple[str, int, int]] = [
    ("bn", 0x0980, 0x09FF),  # Bengali
    ("hi", 0x0900, 0x097F),  # Devanagari
    ("ta", 0x0B80, 0x0BFF),  # Tamil
    ("te", 0x0C00, 0x0C7F),  # Telugu
    ("ml", 0x0D00, 0x0D7F),  # Malayalam
    ("gu", 0x0A80, 0x0AFF),  # Gujarati
    ("or", 0x0B00, 0x0B7F),  # Odia
]

# Marathi is deliberately absent from the ranges above. It is written in
# Devanagari, the same script as Hindi, so no script test can separate them —
# a range for it would only ever mislabel Hindi. Marathi is identified by the
# user's own selection, which is the reliable signal, and the detector saying
# "Hindi" for Marathi script is a limit worth stating rather than papering over.


@dataclass
class LanguageGuess:
    """Result of identification, carrying *how* we decided so it can be shown."""

    code: str
    confidence: float
    method: str
    needs_llm: bool = False


def to_sarvam_code(code: str) -> str:
    """Map a short UI code ('bn') to Sarvam's BCP-47 style code ('bn-IN')."""
    return SUPPORTED_LANGUAGES.get(code, "en-IN")


def detect_by_script(text: str) -> LanguageGuess | None:
    """Identify a language from its script. Returns None for Latin-only text."""
    counts: dict[str, int] = {}

    for char in text:
        code_point = ord(char)
        for lang, start, end in _SCRIPT_RANGES:
            if start <= code_point <= end:
                counts[lang] = counts.get(lang, 0) + 1
                break

    if not counts:
        return None

    total_indic = sum(counts.values())
    best = max(counts, key=lambda k: counts[k])

    return LanguageGuess(
        code=best,
        confidence=counts[best] / total_indic,
        method="unicode-script",
    )


def detect_language(text: str, ui_language: str | None = None) -> LanguageGuess:
    """Best-effort identification without calling a model.

    The UI's language selector is a strong prior — if the user picked Bengali
    and typed in Latin script, Bengali is a far better guess than English. When
    even that is missing, the caller is told to ask the LLM.
    """
    by_script = detect_by_script(text)
    if by_script is not None:
        return by_script

    if ui_language in SUPPORTED_LANGUAGES and ui_language != "en":
        # Latin characters, but the user's chosen language is Indic — most
        # likely romanised input (Banglish / Hinglish) rather than English.
        return LanguageGuess(
            code=ui_language,
            confidence=0.5,
            method="ui-selection-prior",
            needs_llm=True,
        )

    return LanguageGuess(
        code=ui_language or "en",
        confidence=0.4,
        method="default-fallback",
        needs_llm=True,
    )
