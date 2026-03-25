"""Shared stemmer — normalizes verb forms for legal text matching.

Used by both the scenario classifier and the keyword search service
to avoid duplicate stem dictionaries.
"""

from __future__ import annotations

# Maps inflected forms to a base form so "beat/beating/beaten" all match.
STEM_MAP: dict[str, str] = {
    # ── Violence ─────────────────────────────────────────────────────
    "beating": "beat", "beaten": "beat", "beats": "beat",
    "hitting": "hit", "hits": "hit",
    "kicked": "kick", "kicking": "kick", "kicks": "kick",
    "slapping": "slap", "slapped": "slap", "slaps": "slap",
    "punching": "punch", "punched": "punch", "punches": "punch",
    "attacking": "attack", "attacked": "attack", "attacks": "attack",
    # ── Threats / Harassment ─────────────────────────────────────────
    "threatening": "threaten", "threatened": "threaten", "threatens": "threaten",
    "harassing": "harass", "harassed": "harass", "harasses": "harass",
    "stalking": "stalk", "stalked": "stalk",
    "molesting": "molest", "molested": "molest",
    "defaming": "defame", "defamed": "defame",
    # ── Theft / Robbery ──────────────────────────────────────────────
    "stealing": "steal", "stolen": "steal", "stole": "steal", "steals": "steal",
    "snatching": "snatch", "snatched": "snatch",
    "robbing": "rob", "robbed": "rob",
    "looting": "loot", "looted": "loot",
    # ── Property / Actions ───────────────────────────────────────────
    "throwing": "throw", "threw": "throw", "thrown": "throw", "throws": "throw",
    "evicting": "evict", "evicted": "evict", "evicts": "evict",
    "cheating": "cheat", "cheated": "cheat", "cheats": "cheat",
    # ── Property / Housing ──────────────────────────────────────────
    "vacated": "vacate", "vacating": "vacate", "vacates": "vacate",
    "reduced": "reduce", "reducing": "reduce", "reduces": "reduce",
    "forced": "force", "forcing": "force", "forces": "force",
    "informed": "inform", "informing": "inform", "informs": "inform",
    "occupied": "occupy", "occupying": "occupy",
    "rented": "rent", "renting": "rent", "rents": "rent",
    "leased": "lease", "leasing": "lease",
    # ── Employment ───────────────────────────────────────────────────
    "firing": "fire", "fired": "fire", "fires": "fire",
    "removing": "remove", "removed": "remove", "removes": "remove",
    "terminating": "terminate", "terminated": "terminate",
    "stopped": "stop", "stopping": "stop",
    "refused": "refuse", "refusing": "refuse",
    "denied": "deny", "denying": "deny",
    # ── Serious crimes ───────────────────────────────────────────────
    "murdering": "murder", "murdered": "murder",
    "kidnapping": "kidnap", "kidnapped": "kidnap",
    "abusing": "abuse", "abused": "abuse",
    # ── Family / Misc ────────────────────────────────────────────────
    "divorcing": "divorce", "divorced": "divorce",
    "losing": "lose", "lost": "lose",
    "missing": "miss",
    "caught": "catch",
    # ── Additional stems from legal_service keyword search ───────────
    "killed": "kill", "killing": "kill", "kills": "kill",
    "raping": "rape", "raped": "rape",
    "forged": "forgery", "forging": "forgery",
    "assaulted": "assault", "assaulting": "assault",
}

# Conceptual synonym map (maps common objects to legal concepts)
# Used by keyword search for broader matching
SYNONYM_MAP: dict[str, str] = {
    "phone": "theft",
    "mobile": "theft",
    "wallet": "theft",
    "money": "cheat",
    "fraud": "cheat",
}


def stem_text(text: str) -> str:
    """Apply simple stemming to normalize verb forms in text."""
    words = text.split()
    stemmed = [STEM_MAP.get(w, w) for w in words]
    return " ".join(stemmed)


def stem_word(word: str) -> str:
    """Stem a single word. Returns original if no stem found."""
    return STEM_MAP.get(word, word)
