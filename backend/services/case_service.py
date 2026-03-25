"""Case tracker service — in-memory CRUD with timeline."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from backend.models.schemas import CaseRecord, TimelineEvent

logger = logging.getLogger("chakravyuha")


class CaseService:
    """In-memory case tracking with timeline events."""

    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = {}

    def create_case(
        self,
        title: str,
        description: str,
        sections: list[str] | None = None,
        severity: str = "LOW",
    ) -> CaseRecord:
        """Create a new tracked case."""
        now = datetime.now(timezone.utc).isoformat()
        case_id = f"CK-{uuid.uuid4().hex[:8].upper()}"

        case = CaseRecord(
            case_id=case_id,
            title=title,
            description=description,
            sections=sections or [],
            severity=severity,
            status="open",
            timeline=[
                TimelineEvent(
                    timestamp=now,
                    event="Case Created",
                    details=f"Case '{title}' opened with severity {severity}",
                )
            ],
            created_at=now,
            updated_at=now,
        )
        self._cases[case_id] = case
        logger.info("Case created: %s — %s", case_id, title)
        return case

    def get_case(self, case_id: str) -> CaseRecord | None:
        """Retrieve a case by ID."""
        return self._cases.get(case_id)

    def list_cases(self) -> list[CaseRecord]:
        """List all tracked cases, newest first."""
        cases = list(self._cases.values())
        cases.sort(key=lambda c: c.created_at, reverse=True)
        return cases

    def update_case(
        self,
        case_id: str,
        status: str | None = None,
        event: str | None = None,
        details: str = "",
    ) -> CaseRecord | None:
        """Update a case status and/or add timeline event."""
        case = self._cases.get(case_id)
        if case is None:
            return None

        now = datetime.now(timezone.utc).isoformat()

        if status:
            case.status = status

        if event:
            case.timeline.append(
                TimelineEvent(timestamp=now, event=event, details=details)
            )

        case.updated_at = now
        logger.info("Case updated: %s — status=%s, event=%s", case_id, status, event)
        return case

    def delete_case(self, case_id: str) -> bool:
        """Delete a case by ID."""
        if case_id in self._cases:
            del self._cases[case_id]
            logger.info("Case deleted: %s", case_id)
            return True
        return False


# Singleton
_case_service: CaseService | None = None


def get_case_service() -> CaseService:
    """Get or create the CaseService singleton."""
    global _case_service
    if _case_service is None:
        _case_service = CaseService()
    return _case_service
