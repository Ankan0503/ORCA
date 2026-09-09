"""Marine and fishing vocabulary, pinned per language.

Generic translation mangles exactly the words that matter most to a fisherman:
species names, gear, and local place names. "Hilsa" becomes "a kind of fish";
"Potential Fishing Zone" becomes word salad. So the terms are pinned here and
injected into the prompt, which keeps the wording consistent and makes the
answer sound like it was written by someone who fishes.

SEED DATA — NEEDS A NATIVE SPEAKER'S REVIEW. These entries were drafted for
structure, not authority. Every row should be checked (and the missing
languages filled in) by someone who speaks the language and knows the local
fishing vocabulary before this is demonstrated or relied on.
"""

# term -> {language code: preferred wording}
GLOSSARY: dict[str, dict[str, str]] = {
    "Potential Fishing Zone": {
        "en": "Potential Fishing Zone (PFZ)",
        "hi": "संभावित मत्स्य क्षेत्र (PFZ)",
        "bn": "সম্ভাব্য মাছ ধরার এলাকা (PFZ)",
        "ta": "சாத்தியமான மீன்பிடி மண்டலம் (PFZ)",
        "te": "సంభావ్య చేపల వేట ప్రాంతం (PFZ)",
        "ml": "സാധ്യതയുള്ള മത്സ്യബന്ധന മേഖല (PFZ)",
    },
    "Hilsa": {
        "en": "Hilsa",
        "hi": "हिल्सा",
        "bn": "ইলিশ",
        "ta": "உள்ளம்",
        "te": "పులస",
        "ml": "ഹിൽസ",
    },
    "Indian Mackerel": {
        "en": "Indian Mackerel",
        "hi": "बांगड़ा",
        "bn": "বাংড়া",
        "ta": "அயிலை",
        "te": "కనగర్త",
        "ml": "അയല",
    },
    "wave height": {
        "en": "wave height",
        "hi": "लहर की ऊँचाई",
        "bn": "ঢেউয়ের উচ্চতা",
        "ta": "அலை உயரம்",
        "te": "అల ఎత్తు",
        "ml": "തിരമാലയുടെ ഉയരം",
    },
    "wind speed": {
        "en": "wind speed",
        "hi": "हवा की गति",
        "bn": "বাতাসের গতি",
        "ta": "காற்றின் வேகம்",
        "te": "గాలి వేగం",
        "ml": "കാറ്റിന്റെ വേഗത",
    },
    "Exclusive Economic Zone": {
        "en": "Exclusive Economic Zone (EEZ)",
        "hi": "अनन्य आर्थिक क्षेत्र (EEZ)",
        "bn": "একচেটিয়া অর্থনৈতিক অঞ্চল (EEZ)",
        "ta": "பிரத்யேக பொருளாதார மண்டலம் (EEZ)",
        "te": "ప్రత్యేక ఆర్థిక మండలం (EEZ)",
        "ml": "പ്രത്യേക സാമ്പത്തിക മേഖല (EEZ)",
    },
    "harbour": {
        "en": "harbour",
        "hi": "बंदरगाह",
        "bn": "বন্দর",
        "ta": "துறைமுகம்",
        "te": "ఓడరేవు",
        "ml": "തുറമുഖം",
    },
    "cyclone": {
        "en": "cyclone",
        "hi": "चक्रवात",
        "bn": "ঘূর্ণিঝড়",
        "ta": "புயல்",
        "te": "తుఫాను",
        "ml": "ചുഴലിക്കാറ്റ്",
    },
}

# Place names are transliterated inconsistently by generic MT, so they are
# pinned rather than translated.
PLACE_NAMES: dict[str, dict[str, str]] = {
    "Digha": {"en": "Digha", "bn": "দীঘা", "hi": "दीघा"},
    "Bay of Bengal": {
        "en": "Bay of Bengal",
        "bn": "বঙ্গোপসাগর",
        "hi": "बंगाल की खाड़ी",
        "ta": "வங்காள விரிகுடா",
        "te": "బంగాళాఖాతం",
        "ml": "ബംഗാൾ ഉൾക്കടൽ",
    },
}


def glossary_for(language: str) -> str:
    """Render the pinned wording for one language as prompt text.

    Returns an empty string for English, where no pinning is needed.
    """
    if language == "en":
        return ""

    lines: list[str] = []
    for source in (GLOSSARY, PLACE_NAMES):
        for term, translations in source.items():
            preferred = translations.get(language)
            if preferred:
                lines.append(f'- "{term}" -> "{preferred}"')

    if not lines:
        return ""

    return (
        "Use exactly these words for the following terms; do not paraphrase "
        "them:\n" + "\n".join(lines)
    )
