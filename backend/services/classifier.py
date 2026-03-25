"""Scenario classifier — rule-based first, LLM fallback, safety filter.

Classification-first architecture: classify the user's problem into a known
scenario BEFORE touching RAG or LLM.  This eliminates hallucinations for
common legal queries.

Supports: English, romanized Hindi, and Sarvam-translated English (natural verb forms).
"""

from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass

from backend.utils.stemmer import stem_text

logger = logging.getLogger("chakravyuha")


# ── Classification result ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClassifyResult:
    """Immutable result from classify()."""
    scenario: str
    confidence: float
    method: str = "rules"  # "rules", "rules_stemmed", "llm"


# ── Scenario definitions ─────────────────────────────────────────────────────
# Each tuple: (scenario_id, list-of-keyword-sets)
# A keyword-set matches when ALL words in it appear in the (stemmed) text.
# First match wins, so order matters (more specific first).

SCENARIO_RULES: list[tuple[str, list[list[str]]]] = [
    # ── Documents / License ──────────────────────────────────────────────
    ("lost_license", [
        ["license", "lose"],           # lost/losing → lose
        ["license", "miss"],           # missing → miss
        ["driving", "license", "lose"],
        ["dl", "lose"],
        ["without", "license"],        # "caught without a license"
        ["no", "license"],
        ["license", "catch"],          # "caught without license"
        ["license", "expire"],
        ["license", "kho"],            # Hindi: license kho gaya
        ["license", "gum"],            # Hindi: license gum ho gaya
    ]),
    ("lost_documents", [
        ["documents", "lose"],
        ["passport", "lose"],
        ["aadhar", "lose"],
        ["aadhaar", "lose"],
        ["pan", "card", "lose"],
        ["documents", "steal"],
        ["id", "lose"],
        ["id", "miss"],
        ["dastavez", "kho"],           # Hindi
        ["kagaz", "kho"],              # Hindi
    ]),

    # ── Traffic / Challan ────────────────────────────────────────────────
    ("traffic_fine", [
        ["challan"],
        ["traffic", "fine"],
        ["e-challan"],
        ["traffic", "police"],
        ["over", "speeding"],
        ["speeding", "ticket"],
        ["signal", "jump"],
        ["red", "light"],
        ["drunk", "driving"],
        ["dui"],
        ["traffic", "violation"],
    ]),
    ("accident", [
        ["accident"],
        ["hit", "run"],
        ["hit-and-run"],
        ["road", "accident"],
        ["vehicle", "accident"],
        ["car", "crash"],
        ["vehicle", "crash"],
    ]),

    # ── Domestic / Family ────────────────────────────────────────────────
    ("domestic_violence", [
        ["domestic", "violence"],
        ["domestic", "abuse"],
        ["husband", "beat"],           # beat/beating/beaten all stem to "beat"
        ["husband", "hit"],
        ["husband", "abuse"],
        ["husband", "throw"],          # threw/thrown → throw
        ["husband", "kick"],
        ["husband", "slap"],
        ["husband", "punch"],
        ["husband", "threaten"],
        ["husband", "harass"],
        ["husband", "torture"],
        ["wife", "beat"],
        ["wife", "abuse"],
        ["beat", "house"],             # "beat me and threw out of house"
        ["violence", "home"],
        ["violence", "house"],
        ["beat", "throw", "house"],    # "beat and threw out of the house"
        ["throw", "out", "house"],     # "threw me out of the house"
        ["kick", "out", "house"],      # "kicked out of the house"
        ["abuse", "home"],
        ["torture", "home"],
        ["pati", "maarta"],            # Hindi romanized: husband beats
        ["ghar", "hinsa"],             # Hindi romanized: domestic violence
        ["maar", "peet"],              # Hindi romanized: beating
        ["maara"],                     # Hindi romanized: hit
        ["peet"],                      # Hindi romanized: beat
        # Hindi Devanagari script
        ["\u092a\u0924\u093f", "\u092e\u093e\u0930\u0924\u093e"],     # पति मारता (husband beats)
        ["\u092a\u0924\u093f", "\u092e\u093e\u0930"],                  # पति मार (husband hits)
        ["\u0918\u0930\u0947\u0932\u0942", "\u0939\u093f\u0902\u0938\u093e"],  # घरेलू हिंसा (domestic violence)
        ["\u092e\u093e\u0930\u092a\u0940\u091f"],                      # मारपीट (beating)
        ["\u092e\u093e\u0930\u0924\u093e"],                            # मारता (beats)
        ["\u092a\u0940\u091f\u0924\u093e"],                            # पीटता (beats)
        ["\u092a\u0924\u093f", "\u092a\u0940\u091f"],                  # पति पीट (husband beats)
        ["\u0938\u0938\u0941\u0930\u093e\u0932"],                      # ससुराल (in-laws place)
        ["\u0926\u0939\u0947\u091c"],                                  # दहेज (dowry — also triggers domestic)
        ["\u092a\u0924\u093f", "\u0924\u0949\u0930\u094d\u091a\u0930"],# पति तॉर्चर (husband torture)
        # Tamil Devanagari-equivalent phrases
        ["\u0b95\u0ba3\u0bb5\u0ba9\u0bcd", "\u0b85\u0b9f\u0bbf"],     # கணவன் அடி (husband beats)
        ["\u0b95\u0bc1\u0b9f\u0bc1\u0bae\u0bcd\u0baa", "\u0bb5\u0ba9\u0bcd\u0bae\u0bc1\u0bb1\u0bc8"],  # குடும்ப வன்முறை (domestic violence)
    ]),
    ("dowry", [
        ["dowry"],
        ["dowry", "harass"],
        ["dowry", "demand"],
        ["dahej"],
        ["dahej", "maang"],            # Hindi
    ]),
    ("divorce", [
        ["divorce"],
        ["separation"],
        ["mutual", "consent"],
        ["alimony"],
        ["maintenance"],
        ["want", "divorce"],
        ["need", "divorce"],
    ]),
    ("child_custody", [
        ["child", "custody"],
        ["custody", "battle"],
        ["guardianship"],
        ["custody", "child"],
    ]),

    # ── Criminal ─────────────────────────────────────────────────────────
    ("theft", [
        ["theft"],
        ["steal"],                     # stolen/stole/stealing → steal
        ["rob"],                       # robbed/robbing → rob
        ["robbery"],
        ["burglary"],
        ["pickpocket"],
        ["snatch"],                    # snatching/snatched → snatch
        ["phone", "steal"],
        ["mobile", "steal"],
        ["wallet", "steal"],
        ["bag", "steal"],
        ["phone", "snatch"],
        ["chori"],                     # Hindi: theft
        ["loot"],                      # Hindi: robbery
    ]),
    ("assault", [
        ["assault"],
        ["attack"],                    # attacked/attacking → attack
        ["beaten"],                    # kept for direct match before stemming
        ["physical", "harm"],
        ["hit", "me"],
        ["beat", "me"],
        ["punch"],                     # punched → punch
        ["slap"],                      # slapped → slap
        ["hurt", "me"],
        ["injure"],
    ]),
    ("cheating_fraud", [
        ["cheat"],                     # cheating/cheated → cheat
        ["fraud"],
        ["scam"],
        ["online", "fraud"],
        ["upi", "fraud"],
        ["cyber", "fraud"],
        ["money", "cheat"],
        ["deceive"],
        ["swindle"],
    ]),
    ("cyber_crime", [
        ["cyber", "crime"],
        ["hacking"],
        ["hack"],
        ["data", "leak"],
        ["identity", "theft"],
        ["online", "harass"],
        ["cyber", "bully"],
        ["morphed", "photos"],
        ["online", "threat"],
    ]),
    ("defamation", [
        ["defamation"],
        ["defame"],                    # defaming/defamed → defame
        ["slander"],
        ["libel"],
        ["false", "accusation"],
        ["false", "allegation"],
        ["reputation", "damage"],
    ]),
    ("murder_threat", [
        ["murder", "threat"],
        ["death", "threat"],
        ["threaten", "kill"],          # threatening → threaten
        ["life", "danger"],
        ["threat", "life"],
        ["kill", "threat"],
    ]),
    ("kidnapping", [
        ["kidnap"],                    # kidnapping/kidnapped → kidnap
        ["abduction"],
        ["abduct"],
        ["miss", "child"],             # missing → miss
        ["miss", "person"],
    ]),
    ("sexual_harassment", [
        ["sexual", "harass"],          # harassment → harass
        ["molest"],                    # molestation/molested → molest
        ["eve", "teasing"],
        ["stalk"],                     # stalking/stalked → stalk
        ["posh"],
        ["workplace", "harass"],
        ["inappropriate", "touch"],
    ]),
    ("rape", [
        ["rape"],
        ["sexual", "assault"],
        ["sexually", "assault"],
    ]),

    # ── Property / Civil ─────────────────────────────────────────────────
    # tenant_landlord BEFORE property_dispute (more specific first)
    ("tenant_landlord", [
        ["tenant"],
        ["landlord"],
        ["rent", "dispute"],
        ["eviction"],
        ["evict"],                     # evicted → evict
        ["security", "deposit"],
        ["house", "owner"],
        ["owner", "kick"],             # kicked → kick
        ["owner", "throw"],            # threw → throw
        ["throw", "out", "house"],     # "threw out of the house"
        ["kick", "out", "home"],
        ["throw", "out", "home"],
        ["evict", "house"],
        ["evict", "home"],
        # English: catch translated Indic text about housing
        ["house", "vacate"],
        ["house", "force"],
        ["house", "leave"],
        ["house", "reduce"],           # "reduced from house" (lossy translation)
        ["house", "without", "inform"],
        ["home", "vacate"],
        ["home", "force"],
        ["rent", "reduce"],
        ["rent", "increase"],
        ["rent", "pay"],
        ["force", "vacate"],
        ["force", "leave", "house"],
        ["force", "leave", "home"],
        ["illegal", "evict"],
        ["without", "notice", "vacate"],
        ["without", "notice", "evict"],
        ["vacate", "house"],
        ["vacate", "home"],
        ["room", "vacate"],
        ["room", "evict"],
        # Hindi romanized
        ["makaan", "malik"],           # landlord
        ["kiraya"],                    # rent
        ["nikala", "ghar"],            # evicted from house
        # Hindi Devanagari script — comprehensive
        ["\u0915\u093f\u0930\u093e\u092f\u093e"],                     # किराया (rent)
        ["\u0915\u093f\u0930\u093e\u092f\u0947\u0926\u093e\u0930"],   # किरायेदार (tenant)
        ["\u0915\u093f\u0930\u093e\u092f\u0947\u0926\u093e\u0930", "\u0915\u092c\u094d\u091c\u093e"],  # किरायेदार कब्जा (tenant occupied)
        ["\u092e\u0915\u093e\u0928"],                                  # मकान (house)
        ["\u092e\u0915\u093e\u0928", "\u092e\u093e\u0932\u093f\u0915"], # मकान मालिक (landlord)
        ["\u0918\u0930", "\u0916\u093e\u0932\u0940"],                  # घर खाली (vacate house)
        ["\u0918\u0930", "\u0928\u093f\u0915\u093e\u0932\u093e"],      # घर निकाला (evicted from house)
        ["\u0918\u0930", "\u0928\u093f\u0915\u093e\u0932"],            # घर निकाल (evict from house)
        ["\u0918\u0930", "\u091b\u094b\u0921\u093c"],                  # घर छोड़ (leave house)
        ["\u0918\u0930", "\u091b\u0940\u0928"],                        # घर छीन (snatch house)
        ["\u0918\u0930", "\u091c\u092c\u0930\u0926\u0938\u094d\u0924\u0940"],  # घर जबरदस्ती (house forcefully)
        ["\u0918\u0930", "\u0938\u0947", "\u0928\u093f\u0915\u093e\u0932"],    # घर से निकाल (evict from house)
        ["\u092e\u0915\u093e\u0928", "\u0935\u093f\u0935\u093e\u0926"],# मकान विवाद (house dispute)
        ["\u0938\u093f\u0915\u094d\u092f\u094b\u0930\u093f\u091f\u0940", "\u0921\u093f\u092a\u0949\u091c\u093f\u091f"],  # सिक्योरिटी डिपॉजिट
        ["\u091c\u092e\u093e\u0928\u0924", "\u0930\u093e\u0936\u093f"],# जमानत राशि (security deposit)
        ["\u0915\u093f\u0930\u093e\u092f\u093e", "\u092c\u0922\u093c\u093e"],  # किराया बढ़ा (rent increased)
        ["\u0915\u093f\u0930\u093e\u092f\u093e", "\u0915\u092e"],      # किराया कम (rent reduced)
        ["\u092e\u0915\u093e\u0928", "\u092e\u093e\u0932\u093f\u0915", "\u092a\u0930\u0947\u0936\u093e\u0928"],  # मकान मालिक परेशान (landlord harassing)
        # Tamil native keywords (catches BEFORE translation)
        ["\u0bb5\u0bc0\u0b9f\u0bc1"],                                  # வீடு (house)
        ["\u0bb5\u0bbe\u0b9f\u0b95\u0bc8"],                           # வாடகை (rent)
        ["\u0bb5\u0bc0\u0b9f\u0bcd\u0b9f"],                           # வீட்ட (house colloquial)
        ["\u0bb5\u0bc6\u0bb3\u0bbf\u0baf\u0bc7\u0bb1\u0bcd\u0bb1"],   # வெளியேற்ற (eviction)
        ["\u0b95\u0bc1\u0b9f\u0bbf\u0baf\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa\u0bc1"], # குடியிருப்பு (residence)
        ["\u0bb5\u0bc0\u0b9f\u0bcd\u0b9f\u0bc1", "\u0bb5\u0bbf\u0b9f\u0bcd\u0b9f\u0bc1"], # வீட்டு விட்டு (from house)
    ]),
    ("property_dispute", [
        ["property", "dispute"],
        ["land", "dispute"],
        ["land", "grab"],
        ["encroachment"],
        ["illegal", "possession"],
        ["property", "fraud"],
        ["property", "grab"],
        # Tamil native keywords
        ["\u0b9a\u0bca\u0ba4\u0bcd\u0ba4\u0bc1"],                     # சொத்து (property)
        ["\u0ba8\u0bbf\u0bb2\u0bae\u0bcd"],                           # நிலம் (land)
        ["\u0b86\u0b95\u0bcd\u0b95\u0bbf\u0bb0\u0bae\u0bbf\u0baa\u0bcd\u0baa\u0bc1"],  # ஆக்கிரமிப்பு (encroachment)
        # Hindi native keywords
        ["\u091c\u092e\u0940\u0928", "\u0935\u093f\u0935\u093e\u0926"],  # जमीन विवाद (land dispute)
        ["\u0915\u092c\u094d\u091c\u093e"],                            # कब्जा (possession)
    ]),
    ("inheritance", [
        ["inheritance"],
        ["will", "dispute"],
        ["succession"],
        ["ancestral", "property"],
        ["property", "inherit"],
    ]),

    # ── Consumer / Employment ────────────────────────────────────────────
    ("consumer_complaint", [
        ["consumer", "complaint"],
        ["defective", "product"],
        ["refund"],
        ["warranty"],
        ["overcharged"],
        ["consumer", "rights"],
        ["consumer", "forum"],
        ["faulty", "product"],
    ]),
    ("employment_issue", [
        ["wrongful", "termination"],
        ["salary", "not", "paid"],
        ["wages", "due"],
        ["pf", "not", "paid"],
        ["unfair", "dismissal"],
        ["fire", "job"],               # fired → fire
        ["fire", "work"],
        ["employer", "fire"],          # "employer fired me"
        ["fire", "without", "reason"],
        ["fire", "me"],
        ["lose", "job"],               # lost → lose
        ["remove", "job"],             # removed → remove
        ["remove", "work"],
        ["stop", "working"],           # stopped → stop (will add to stems)
        ["terminate"],                 # terminated → terminate
        ["employer", "not", "paying"],
        ["naukri", "nikala"],          # Hindi romanized
        ["tankhwah", "nahi"],          # Hindi romanized
        # Hindi Devanagari script
        ["\u0928\u094c\u0915\u0930\u0940", "\u0928\u093f\u0915\u093e\u0932"],  # नौकरी निकाल (fired from job)
        ["\u0928\u094c\u0915\u0930\u0940", "\u0938\u0947", "\u0928\u093f\u0915\u093e\u0932"],  # नौकरी से निकाल (fired from job)
        ["\u0924\u0928\u0916\u094d\u0935\u093e\u0939"],               # तनख्वाह (salary)
        ["\u0924\u0928\u0916\u094d\u0935\u093e\u0939", "\u0928\u0939\u0940\u0902"],  # तनख्वाह नहीं (salary not paid)
        ["\u0935\u0947\u0924\u0928", "\u0928\u0939\u0940\u0902"],      # वेतन नहीं (wages not paid)
        ["\u0935\u0947\u0924\u0928"],                                  # वेतन (salary/wages)
        ["\u0928\u094c\u0915\u0930\u0940"],                            # नौकरी (job — single keyword for job context)
        ["\u092e\u093e\u0932\u093f\u0915", "\u0928\u0939\u0940\u0902", "\u0926\u0947"],  # मालिक नहीं दे (employer not paying)
        ["\u092a\u0940\u090f\u092b"],                                  # पीएफ (PF)
        ["\u0915\u0902\u092a\u0928\u0940", "\u0928\u093f\u0915\u093e\u0932"],  # कंपनी निकाल (company fired)
        # Tamil native keywords for employment
        ["\u0b9a\u0bae\u0bcd\u0baa\u0bb3\u0bae\u0bcd"],               # சம்பளம் (salary)
        ["\u0bb5\u0bc7\u0bb2\u0bc8"],                                  # வேலை (job/work)
        ["\u0bb5\u0bc7\u0bb2\u0bc8", "\u0ba8\u0bc0\u0b95\u0bcd\u0b95"],  # வேலை நீக்க (fired from job)
    ]),
    ("rti", [
        ["rti"],
        ["right", "to", "information"],
        ["information", "act"],
    ]),

    # ── Procedures ───────────────────────────────────────────────────────
    ("file_fir", [
        ["file", "fir"],
        ["fir", "register"],
        ["fir", "lodge"],
        ["police", "complaint"],
        ["police", "report"],
        ["zero", "fir"],
        ["how", "fir"],
        ["lodge", "complaint"],
        ["fir", "darj"],               # Hindi
        ["thana"],                     # Hindi
    ]),
    ("bail", [
        ["bail"],
        ["anticipatory", "bail"],
        ["bail", "process"],
        ["get", "bail"],
        ["apply", "bail"],
    ]),
    ("legal_aid", [
        ["legal", "aid"],
        ["free", "lawyer"],
        ["nalsa"],
        ["legal", "services"],
        ["pro", "bono"],
        ["free", "legal"],
        ["cannot", "afford", "lawyer"],
    ]),
    ("fundamental_rights", [
        ["fundamental", "rights"],
        ["article", "14"],
        ["article", "19"],
        ["article", "21"],
        ["right", "to", "equality"],
        ["right", "to", "freedom"],
        ["right", "to", "life"],
        ["constitutional", "rights"],
    ]),
    ("noise_complaint", [
        ["noise", "complaint"],
        ["loud", "music"],
        ["noise", "pollution"],
    ]),
]


ALLOWED_SCENARIOS: frozenset[str] = frozenset(
    scenario_id for scenario_id, _ in SCENARIO_RULES
)


def validate_scenario(scenario: str) -> str:
    """Return scenario if it's in the allowed set, otherwise 'unknown'."""
    return scenario if scenario in ALLOWED_SCENARIOS else "unknown"


def classify(text: str) -> ClassifyResult:
    """Classify user input into a known legal scenario.

    Applies simple stemming to normalize verb forms before matching.
    Returns ClassifyResult with scenario, confidence, and method.
    """
    if not text or not text.strip():
        return ClassifyResult(scenario="empty", confidence=0.0)

    lower = text.lower().strip()
    # Normalize whitespace
    lower = re.sub(r"\s+", " ", lower)

    # Apply stemming to normalize verb forms
    stemmed = stem_text(lower)

    for scenario_id, keyword_sets in SCENARIO_RULES:
        for kw_set in keyword_sets:
            # Check original text first (exact match = higher confidence)
            if all(kw in lower for kw in kw_set):
                logger.info("Classified '%s' -> %s (exact, matched: %s)", text[:50], scenario_id, kw_set)
                return ClassifyResult(
                    scenario=validate_scenario(scenario_id),
                    confidence=0.95,
                    method="rules",
                )
            # Check stemmed text (stemmed match = slightly lower confidence)
            if all(kw in stemmed for kw in kw_set):
                logger.info("Classified '%s' -> %s (stemmed, matched: %s)", text[:50], scenario_id, kw_set)
                return ClassifyResult(
                    scenario=validate_scenario(scenario_id),
                    confidence=0.85,
                    method="rules_stemmed",
                )

    logger.info("Classified '%s' -> unknown", text[:50])
    return ClassifyResult(scenario="unknown", confidence=0.0)


# ── LLM Fallback Classifier ──────────────────────────────────────────────────

_LLM_CLASSIFY_PROMPT = (
    "You are a strict classifier for Indian legal issues.\n"
    "Classify the user's legal issue into EXACTLY ONE category:\n\n"
    + "\n".join(f"- {sid}" for sid in sorted(ALLOWED_SCENARIOS))
    + "\n- unknown\n\n"
    "DISAMBIGUATION RULES (VERY IMPORTANT):\n"
    "- If about house, rent, eviction, landlord, tenant, room, vacate, "
    "staying, living place → tenant_landlord\n"
    "- If about land, property ownership, encroachment, boundary → property_dispute\n"
    "- If about job, salary, employer, workplace firing, wages → employment_issue\n"
    "- If about beating, violence AT HOME by family → domestic_violence\n"
    "- 'reduced' near house/rent → tenant_landlord (NOT employment)\n"
    "- 'reduced' near salary/wages → employment_issue\n"
    "- Understand CONTEXT, not just individual keywords.\n"
    "- Works for Hindi, Tamil, Telugu, Bengali, any Indian language.\n"
    "- If unsure → unknown\n\n"
    "Return JSON only: {{\"scenario\": \"<id>\"}}\n\n"
    "{query_block}\n\n"
    "JSON:"
)


async def llm_classify(text: str, original_text: str | None = None) -> ClassifyResult:
    """Use LLM to classify when rule-based returns unknown.

    Args:
        text: English text (possibly translated) for classification.
        original_text: Original non-English text (if different from text).
            Providing both helps the LLM disambiguate.

    Uses the existing provider chain. Returns ClassifyResult with method='llm'.
    Timeout: 5s max (2s per provider), falls back to unknown on any error.
    """
    import asyncio
    from backend.config import LLM_ENABLED

    if not LLM_ENABLED:
        return ClassifyResult(scenario="unknown", confidence=0.0)

    try:
        from backend.services.llm.router import get_llm_service
        llm = get_llm_service()
        if not llm.is_available:
            logger.warning("LLM classify: no providers available")
            return ClassifyResult(scenario="unknown", confidence=0.0)

        # Build query block with both original + translated text if available
        if original_text and original_text != text:
            query_block = f"Original text: {original_text[:300]}\nTranslated to English: {text[:300]}"
        else:
            query_block = f"Text: {text[:500]}"

        prompt = _LLM_CLASSIFY_PROMPT.replace("{query_block}", query_block)

        # Run LLM call with 5s total timeout (2s per provider inside)
        result = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None, lambda: _try_llm_providers(llm, prompt)
            ),
            timeout=5.0,
        )

        if result:
            scenario = validate_scenario(result)
            if scenario != "unknown":
                logger.info("LLM classified '%s' -> %s", text[:50], scenario)
                return ClassifyResult(scenario=scenario, confidence=0.75, method="llm")

    except asyncio.TimeoutError:
        logger.warning("LLM classify timed out (5s) for: '%s'", text[:50])
    except Exception as e:
        logger.warning("LLM classify failed: %s", e)

    return ClassifyResult(scenario="unknown", confidence=0.0)


_PROVIDER_TIMEOUT = 2.0  # seconds per provider


def _try_llm_providers(llm, prompt: str) -> str | None:
    """Try each LLM provider to get a scenario classification.

    Each provider gets 2s max before moving to the next.
    """
    for provider in llm._providers:
        try:
            raw = _call_provider_with_timeout(provider, prompt, _PROVIDER_TIMEOUT)
            if not raw:
                continue
            raw = raw.strip()
            # Try JSON parse
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "scenario" in parsed:
                    return parsed["scenario"].strip().lower()
            except json.JSONDecodeError:
                pass
            # Fallback: raw text might be just the scenario ID
            candidate = raw.strip().strip('"').lower()
            if candidate in ALLOWED_SCENARIOS:
                return candidate
        except Exception as e:
            logger.debug("Provider %s failed: %s", type(provider).__name__, e)
            continue
    return None


def _call_provider_with_timeout(provider, prompt: str, timeout: float) -> str | None:
    """Call a single provider with a per-provider timeout using a thread."""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(provider.generate, prompt, [], "en-IN")
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logger.debug("Provider %s timed out after %.1fs", type(provider).__name__, timeout)
            return None


# ── Startup check: warn if LLM is enabled but no providers are configured ─────

def _check_llm_providers() -> None:
    """Log a warning at import time if LLM is enabled but no providers work."""
    try:
        from backend.config import LLM_ENABLED
        if not LLM_ENABLED:
            return
        from backend.services.llm.router import get_llm_service
        llm = get_llm_service()
        if not llm.is_available:
            logger.warning(
                "LLM_ENABLED=true but no LLM providers are configured or available. "
                "The semantic classifier will not work. Configure at least one of: "
                "GEMINI_API_KEY, OPENROUTER_API_KEY, MISTRAL_API_KEY, or run Ollama locally."
            )
    except Exception:
        pass  # Don't crash on import — this is just a diagnostic


_check_llm_providers()


# ── Safety Filter ─────────────────────────────────────────────────────────────

# Scenario IDs where terrorism/war-related sections are legitimately relevant
_TERRORISM_RELEVANT_SCENARIOS: frozenset[str] = frozenset({
    "murder_threat",
})

# Keywords that should NOT appear in responses for non-terrorism queries
_BANNED_RESPONSE_KEYWORDS: list[str] = [
    "waging war",
    "ipc 121",
    "bns 147",
    "sedition",
    "ipc 124a",
]


def safety_check(response_text: str, scenario: str) -> bool:
    """Check if a response is safe for the given scenario.

    Returns True if safe, False if the response contains dangerous
    misclassifications (e.g., terrorism sections for a lost license query).
    """
    if scenario in _TERRORISM_RELEVANT_SCENARIOS:
        return True

    response_lower = response_text.lower()
    for keyword in _BANNED_RESPONSE_KEYWORDS:
        if keyword in response_lower:
            logger.warning(
                "Safety filter triggered: '%s' found in response for scenario=%s",
                keyword, scenario,
            )
            return False

    return True
