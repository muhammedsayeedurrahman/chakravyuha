"""Portal registry — central lookup for all supported government portals."""

from __future__ import annotations

from backend.agent.openclaw.models import PortalConfig
from backend.agent.openclaw.portals.cpgrams import CPGRAMS_CONFIG
from backend.agent.openclaw.portals.consumer_helpline import CONSUMER_HELPLINE_CONFIG
from backend.agent.openclaw.portals.ecourts import ECOURTS_CONFIG
from backend.agent.openclaw.portals.mparivahan import MPARIVAHAN_CONFIG


_PORTALS: dict[str, PortalConfig] = {
    CPGRAMS_CONFIG.portal_id: CPGRAMS_CONFIG,
    CONSUMER_HELPLINE_CONFIG.portal_id: CONSUMER_HELPLINE_CONFIG,
    ECOURTS_CONFIG.portal_id: ECOURTS_CONFIG,
    MPARIVAHAN_CONFIG.portal_id: MPARIVAHAN_CONFIG,
}


class PortalRegistry:
    """Central registry for all supported government portals."""

    def get(self, portal_id: str) -> PortalConfig | None:
        """Look up a portal by ID."""
        return _PORTALS.get(portal_id)

    def list_portals(self) -> list[dict[str, str]]:
        """Return summary list of all supported portals."""
        return [
            {
                "id": cfg.portal_id,
                "name": cfg.name,
                "url": cfg.base_url,
                "description": cfg.description,
                "required_fields": list(cfg.required_fields),
            }
            for cfg in _PORTALS.values()
        ]

    def list_ids(self) -> list[str]:
        """Return all portal IDs."""
        return list(_PORTALS.keys())

    def get_required_fields(self, portal_id: str) -> list[str]:
        """Get required user data fields for a portal."""
        cfg = _PORTALS.get(portal_id)
        return list(cfg.required_fields) if cfg else []

    def validate_user_data(self, portal_id: str, user_data: dict) -> list[str]:
        """Return list of missing required fields."""
        cfg = _PORTALS.get(portal_id)
        if cfg is None:
            return [f"Unknown portal: {portal_id}"]
        return [f for f in cfg.required_fields if f not in user_data or not user_data[f]]
