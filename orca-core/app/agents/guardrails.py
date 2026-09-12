"""Input guardrails: keep small talk and off-topic messages away from the marine agents."""

import re

# Word-boundary stems for everything ORCA's agents can answer about.
_MARINE = re.compile(
    r"\b(?:"
    r"sea|ocean|marine|maritime|boats?\b|vessel|ships?\b|trawl|fish|catch|nets?\b|harbou?r|ports?\b|jetty|"
    r"coast|shore|beach|go out|set out|head out|go today|go tomorrow|can i go|should i go|venture|trips?\b|"
    r"sail|anchor|waves?\b|tides?\b|swell|currents?\b|wind\b|winds\b|windy|gust|storm|rain\b|rainfall|"
    r"raining|rainy|weather|cyclone|depression|lightning|thunder|fog|visib|forecast|temperature|sst\b|"
    r"chlorophyll|plankton|safe|danger|hazard|risk|alert|warning|advisor|pfz|zones?\b|border|boundary|"
    r"eez|imbl|bans?\b|closed season|sanctuar|protected|restrict|geofenc|rules?\b|legal|licen[cs]e|"
    r"permit|prohibit|regulation|life ?jacket|route|navigat|paths?\b|roads?\b|passage|way to\b|reach|hilsa|pomfret|mackerel|sardine|tuna|prawn|"
    r"shrimp|crab|squid|lobster|reports?\b|summary|brief\b|chart|graph|trend|decline|climate|warming|"
    r"over the years|data\b|sources?\b|accura|reliab|how do you know|satellite"
    r")",
    re.I,
)

_GREETING = re.compile(
    r"\b(?:hi+|hello|hey|namaste|namaskar|good (?:morning|afternoon|evening|night)|how are you|"
    r"how do you do|how(?:'s| is) it going|what'?s up|who are you|what are you|what can you do|"
    r"what do you do|your name|introduce yourself)\b",
    re.I,
)

_THANKS = re.compile(r"\b(?:thanks?|thank you|thankyou|bye|goodbye|see you|ok(?:ay)?)\b", re.I)

REPLIES = {
    "greeting": (
        "I'm ORCA, your marine assistant, and I'm ready to help. Ask me whether it is safe to go "
        "to sea, where the fishing zones are, or about the weather, tides, cyclones, maritime "
        "borders and fishing rules."
    ),
    "thanks": (
        "You're welcome. Stay safe at sea, and ask me any time about the weather, fishing zones "
        "or safety."
    ),
    "off_topic": (
        "I can only help with the sea and fishing: sea safety, weather and tides, fishing zones, "
        "cyclone alerts, maritime borders and fishing rules. Please ask me about one of those."
    ),
}


ESTIMATE_CAVEAT = (
    "Note: this fishing zone is ORCA's own estimate from satellite data, not an official INCOIS advisory."
)


def triage(english: str) -> str:
    """'marine', 'greeting', 'thanks' or 'off_topic' for a message in English."""
    if _MARINE.search(english):
        return "marine"
    if _GREETING.search(english):
        return "greeting"
    if _THANKS.search(english):
        return "thanks"
    return "off_topic"
