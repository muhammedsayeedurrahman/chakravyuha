"""In-memory case tracker with session persistence."""

import uuid
from datetime import datetime


class CaseTracker:
    """Track legal cases per user session (in-memory, no DB needed for hackathon)."""

    def __init__(self):
        self._cases: dict[str, dict] = {}

    def create_case(self, user_id: str, issue: str, sections: list[str]) -> dict:
        """Create a new case entry.

        Args:
            user_id: Session or user identifier.
            issue: Description of the legal issue.
            sections: List of relevant BNS/IPC section IDs.

        Returns:
            Created case dict with case_id.
        """
        case_id = str(uuid.uuid4())[:8].upper()
        case = {
            "case_id": case_id,
            "user_id": user_id,
            "issue": issue,
            "sections": list(sections),
            "status": "open",
            "notes": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._cases[case_id] = case
        return dict(case)

    def update_case(self, case_id: str, status: str | None = None, note: str | None = None) -> dict | None:
        """Update case status or add a note.

        Args:
            case_id: Case identifier.
            status: New status (open, in_progress, resolved, escalated).
            note: Note to add to the case.

        Returns:
            Updated case dict or None if not found.
        """
        case = self._cases.get(case_id)
        if case is None:
            return None

        if status:
            case["status"] = status
        if note:
            case["notes"].append({
                "text": note,
                "timestamp": datetime.now().isoformat(),
            })
        case["updated_at"] = datetime.now().isoformat()
        return dict(case)

    def get_case(self, case_id: str) -> dict | None:
        """Get case details by ID."""
        case = self._cases.get(case_id)
        return dict(case) if case else None

    def list_cases(self, user_id: str) -> list[dict]:
        """List all cases for a user."""
        return [
            dict(c) for c in self._cases.values()
            if c["user_id"] == user_id
        ]

    def get_stats(self) -> dict:
        """Get summary statistics."""
        cases = list(self._cases.values())
        return {
            "total": len(cases),
            "open": sum(1 for c in cases if c["status"] == "open"),
            "in_progress": sum(1 for c in cases if c["status"] == "in_progress"),
            "resolved": sum(1 for c in cases if c["status"] == "resolved"),
            "escalated": sum(1 for c in cases if c["status"] == "escalated"),
        }
