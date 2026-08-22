"""Deterministic, explainable eligibility checks for government schemes.

The engine evaluates declarative rules from ``data/government_schemes.json``.
It deliberately does not use an LLM, calculate an eligibility percentage, or
claim to make the administering authority's final decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import json
from numbers import Real
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR


LIKELY_ELIGIBLE = "Likely eligible"
POSSIBLY_ELIGIBLE = "Possibly eligible"
NOT_ENOUGH_INFORMATION = "Not enough information"
LIKELY_NOT_ELIGIBLE = "Likely not eligible"


class SchemeEligibilityError(ValueError):
    """Base error for scheme dataset or eligibility evaluation problems."""


class SchemeNotFoundError(SchemeEligibilityError, LookupError):
    """Raised when a requested scheme identifier is not in the dataset."""


class SchemeDatasetError(SchemeEligibilityError):
    """Raised when an injected or on-disk scheme dataset is malformed."""


class RuleEvaluationError(SchemeEligibilityError):
    """Raised internally when a supplied value cannot be evaluated safely."""


class SchemeEligibilityEngine:
    """Evaluate sourced scheme rules and explain every conclusion.

    Args:
        dataset: Optional injected dataset. It may be a mapping containing a
            ``schemes`` list, or a sequence of scheme mappings. This is useful
            for tests and for callers that load records from another trusted
            source.
        dataset_path: Optional path to a JSON dataset. It is mutually exclusive
            with ``dataset``. When neither is provided the repository dataset is
            loaded from ``DATA_DIR / 'government_schemes.json'``.
    """

    SUPPORTED_OPERATORS = frozenset(
        {
            "eq",
            "neq",
            "in",
            "not_in",
            "gt",
            "gte",
            "lt",
            "lte",
            "between_inclusive",
            "contains",
            "not_contains",
        }
    )
    SUPPORTED_EFFECTS = frozenset({"require", "disqualify"})

    def __init__(
        self,
        dataset: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
        dataset_path: str | Path | None = None,
    ) -> None:
        if dataset is not None and dataset_path is not None:
            raise SchemeDatasetError("Provide either dataset or dataset_path, not both")

        if dataset is None:
            path = Path(dataset_path) if dataset_path else DATA_DIR / "government_schemes.json"
            loaded = self._load_json(path)
        else:
            loaded = deepcopy(dataset)

        self._metadata, schemes = self._normalise_dataset(loaded)
        self._validate_dataset(schemes)
        self._schemes = tuple(deepcopy(schemes))
        self._by_id = {self._normalise_text(scheme["id"]): scheme for scheme in self._schemes}

    @staticmethod
    def _load_json(path: Path) -> Any:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError as exc:
            raise SchemeDatasetError(f"Scheme dataset not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise SchemeDatasetError(f"Invalid scheme dataset JSON at {path}: {exc}") from exc
        except OSError as exc:
            raise SchemeDatasetError(f"Could not read scheme dataset at {path}: {exc}") from exc

    @staticmethod
    def _normalise_dataset(dataset: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if isinstance(dataset, Mapping):
            metadata = dataset.get("metadata", {})
            schemes = dataset.get("schemes")
            if schemes is None:
                raise SchemeDatasetError("Dataset mapping must contain a 'schemes' list")
        elif isinstance(dataset, Sequence) and not isinstance(dataset, (str, bytes, bytearray)):
            metadata = {}
            schemes = dataset
        else:
            raise SchemeDatasetError("Dataset must be a mapping or a sequence of scheme records")

        if not isinstance(metadata, Mapping):
            raise SchemeDatasetError("Dataset 'metadata' must be an object")
        if not isinstance(schemes, Sequence) or isinstance(schemes, (str, bytes, bytearray)):
            raise SchemeDatasetError("Dataset 'schemes' must be a list")

        records: list[dict[str, Any]] = []
        for scheme in schemes:
            if not isinstance(scheme, Mapping):
                raise SchemeDatasetError("Every scheme record must be an object")
            records.append(dict(scheme))
        return dict(metadata), records

    def _validate_dataset(self, schemes: list[dict[str, Any]]) -> None:
        seen_ids: set[str] = set()
        for index, scheme in enumerate(schemes):
            scheme_id = scheme.get("id")
            name = scheme.get("name")
            rules = scheme.get("eligibility_rules")
            if not isinstance(scheme_id, str) or not scheme_id.strip():
                raise SchemeDatasetError(f"Scheme at index {index} has no valid id")
            if not isinstance(name, str) or not name.strip():
                raise SchemeDatasetError(f"Scheme '{scheme_id}' has no valid name")

            normalised_id = self._normalise_text(scheme_id)
            if normalised_id in seen_ids:
                raise SchemeDatasetError(f"Duplicate scheme id: {scheme_id}")
            seen_ids.add(normalised_id)

            if not isinstance(rules, Sequence) or isinstance(rules, (str, bytes, bytearray)):
                raise SchemeDatasetError(f"Scheme '{scheme_id}' must contain eligibility_rules")

            seen_rule_ids: set[str] = set()
            for rule_index, rule in enumerate(rules):
                if not isinstance(rule, Mapping):
                    raise SchemeDatasetError(
                        f"Rule {rule_index} in scheme '{scheme_id}' must be an object"
                    )
                rule_id = rule.get("id")
                field = rule.get("field")
                operator = rule.get("operator")
                effect = rule.get("effect", "require")
                if not isinstance(rule_id, str) or not rule_id.strip():
                    raise SchemeDatasetError(
                        f"Rule {rule_index} in scheme '{scheme_id}' has no valid id"
                    )
                if rule_id in seen_rule_ids:
                    raise SchemeDatasetError(
                        f"Duplicate rule id '{rule_id}' in scheme '{scheme_id}'"
                    )
                seen_rule_ids.add(rule_id)
                if not isinstance(field, str) or not field.strip():
                    raise SchemeDatasetError(f"Rule '{rule_id}' has no valid field")
                if operator not in self.SUPPORTED_OPERATORS:
                    raise SchemeDatasetError(
                        f"Rule '{rule_id}' uses unsupported operator '{operator}'"
                    )
                if effect not in self.SUPPORTED_EFFECTS:
                    raise SchemeDatasetError(
                        f"Rule '{rule_id}' uses unsupported effect '{effect}'"
                    )
                if "value" not in rule:
                    raise SchemeDatasetError(f"Rule '{rule_id}' has no comparison value")

    @property
    def metadata(self) -> dict[str, Any]:
        """Return a defensive copy of dataset-level provenance metadata."""

        return deepcopy(self._metadata)

    def list_schemes(self) -> list[dict[str, Any]]:
        """Return all scheme records without exposing mutable internal state."""

        return deepcopy(list(self._schemes))

    def get_scheme(self, scheme_id: str) -> dict[str, Any]:
        """Return a scheme by id, short name, or alias.

        Raises:
            SchemeNotFoundError: If no scheme matches the supplied identifier.
        """

        return deepcopy(self._resolve_scheme(scheme_id))

    def search_schemes(self, query: str) -> list[dict[str, Any]]:
        """Case-insensitively search sourced scheme text.

        An empty query returns all records, which keeps list/search behaviour
        predictable for an API layer.
        """

        needle = self._normalise_text(query)
        if not needle:
            return self.list_schemes()

        matches: list[dict[str, Any]] = []
        for scheme in self._schemes:
            haystack = " ".join(
                str(value)
                for value in (
                    scheme.get("id", ""),
                    scheme.get("name", ""),
                    scheme.get("short_name", ""),
                    scheme.get("description", ""),
                    scheme.get("benefit_summary", ""),
                    scheme.get("target_group", ""),
                    " ".join(str(alias) for alias in scheme.get("aliases", [])),
                )
            )
            if needle in self._normalise_text(haystack):
                matches.append(deepcopy(scheme))
        return matches

    def check_eligibility(
        self,
        scheme_id: str,
        profile: Mapping[str, Any],
        *,
        max_questions: int | None = 3,
    ) -> dict[str, Any]:
        """Evaluate one scheme against the supplied profile.

        Missing or unusable values are reported as unknown conditions. Known
        answers are never converted into a percentage or opaque score.
        """

        if not isinstance(profile, Mapping):
            raise TypeError("profile must be a mapping of field names to values")
        if max_questions is not None and (
            isinstance(max_questions, bool) or not isinstance(max_questions, int) or max_questions < 0
        ):
            raise ValueError("max_questions must be a non-negative integer or None")

        scheme = self._resolve_scheme(scheme_id)
        matched: list[dict[str, Any]] = []
        unknown: list[dict[str, Any]] = []
        disqualifiers: list[dict[str, Any]] = []
        warnings: list[str] = []

        for rule in scheme.get("eligibility_rules", []):
            field = rule["field"]
            value = profile.get(field)
            source_url = rule.get("source_url") or scheme.get("source_url")
            common = {
                "rule_id": rule["id"],
                "field": field,
                "description": rule.get("description", ""),
                "source_url": source_url,
            }

            if self._is_missing(value):
                unknown.append(
                    {
                        **common,
                        "reason": "missing",
                        "explanation": rule.get(
                            "unknown_message", f"A value for '{field}' is required."
                        ),
                        "question": rule.get("question", f"Please provide {field}."),
                        "priority": self._priority(rule),
                    }
                )
                continue

            try:
                condition_matches = self._evaluate_operator(
                    rule["operator"], value, rule["value"]
                )
            except RuleEvaluationError as exc:
                warning = f"Rule '{rule['id']}' could not evaluate field '{field}': {exc}"
                warnings.append(warning)
                unknown.append(
                    {
                        **common,
                        "reason": "invalid_value",
                        "explanation": (
                            rule.get("unknown_message", f"A valid value for '{field}' is required.")
                            + " The supplied value could not be interpreted for this rule."
                        ),
                        "question": rule.get("question", f"Please provide {field}."),
                        "priority": self._priority(rule),
                    }
                )
                continue

            effect = rule.get("effect", "require")
            passes = condition_matches if effect == "require" else not condition_matches
            if passes:
                matched.append(
                    {
                        **common,
                        "explanation": rule.get(
                            "pass_message", "The supplied answer meets this condition."
                        ),
                    }
                )
            else:
                disqualifiers.append(
                    {
                        **common,
                        "explanation": rule.get(
                            "fail_message", "The supplied answer conflicts with this condition."
                        ),
                    }
                )

        status = self._status_for(matched, unknown, disqualifiers)
        why = self._build_why(status, matched, unknown, disqualifiers)
        next_questions = self._targeted_questions(unknown, max_questions)

        return {
            "scheme_id": scheme["id"],
            "scheme_name": scheme["name"],
            "short_name": scheme.get("short_name", ""),
            "status": status,
            "matched_conditions": matched,
            "unknown_conditions": [self._without_priority(item) for item in unknown],
            "potential_disqualifiers": disqualifiers,
            "why": why,
            "next_questions": next_questions,
            "required_documents": deepcopy(scheme.get("required_documents", [])),
            "application_process": deepcopy(scheme.get("application_process", [])),
            "official_portal_url": scheme.get("official_portal_url"),
            "helpline": scheme.get("helpline"),
            "contact_guidance": scheme.get("contact_guidance"),
            "jurisdiction": deepcopy(scheme.get("jurisdiction", {})),
            "source": scheme.get("source"),
            "source_url": scheme.get("source_url"),
            "source_type": scheme.get("source_type"),
            "effective_date": scheme.get("effective_date"),
            "last_verified": scheme.get("last_verified"),
            "record_status": scheme.get("status"),
            "verification_note": scheme.get("verification_note"),
            "evaluation_warnings": warnings,
            "disclaimer": (
                "This is a deterministic preliminary check based only on the answers provided "
                "and the cited scheme record. The administering authority verifies documents "
                "and makes the final eligibility decision."
            ),
        }

    def check_all(
        self,
        profile: Mapping[str, Any],
        *,
        max_questions: int | None = 3,
    ) -> list[dict[str, Any]]:
        """Evaluate all available schemes against one profile."""

        return [
            self.check_eligibility(scheme["id"], profile, max_questions=max_questions)
            for scheme in self._schemes
        ]

    def get_next_questions(
        self,
        scheme_id: str,
        profile: Mapping[str, Any],
        *,
        limit: int | None = 3,
    ) -> list[dict[str, Any]]:
        """Return only the highest-priority unanswered questions."""

        return self.check_eligibility(
            scheme_id, profile, max_questions=limit
        )["next_questions"]

    # A compact alias is convenient for orchestration layers.
    check = check_eligibility

    def _resolve_scheme(self, identifier: str) -> dict[str, Any]:
        if not isinstance(identifier, str) or not identifier.strip():
            raise SchemeNotFoundError("Scheme id must be a non-empty string")

        normalised = self._normalise_text(identifier)
        direct = self._by_id.get(normalised)
        if direct is not None:
            return direct

        for scheme in self._schemes:
            candidate_names = [scheme.get("short_name", ""), *scheme.get("aliases", [])]
            if any(self._normalise_text(candidate) == normalised for candidate in candidate_names):
                return scheme
        raise SchemeNotFoundError(f"Unknown scheme: {identifier}")

    @classmethod
    def _evaluate_operator(cls, operator: str, actual: Any, expected: Any) -> bool:
        if operator == "eq":
            return cls._equal(actual, expected)
        if operator == "neq":
            return not cls._equal(actual, expected)
        if operator in {"in", "not_in"}:
            if not isinstance(expected, Sequence) or isinstance(expected, (str, bytes, bytearray)):
                raise RuleEvaluationError(f"operator '{operator}' requires a list comparison value")
            result = any(cls._equal(actual, candidate) for candidate in expected)
            return result if operator == "in" else not result
        if operator in {"gt", "gte", "lt", "lte"}:
            actual_number = cls._number(actual, "profile value")
            expected_number = cls._number(expected, "rule value")
            if operator == "gt":
                return actual_number > expected_number
            if operator == "gte":
                return actual_number >= expected_number
            if operator == "lt":
                return actual_number < expected_number
            return actual_number <= expected_number
        if operator == "between_inclusive":
            if (
                not isinstance(expected, Sequence)
                or isinstance(expected, (str, bytes, bytearray))
                or len(expected) != 2
            ):
                raise RuleEvaluationError(
                    "operator 'between_inclusive' requires a two-item comparison list"
                )
            actual_number = cls._number(actual, "profile value")
            minimum = cls._number(expected[0], "lower rule boundary")
            maximum = cls._number(expected[1], "upper rule boundary")
            if minimum > maximum:
                raise RuleEvaluationError("lower rule boundary is greater than upper boundary")
            return minimum <= actual_number <= maximum
        if operator in {"contains", "not_contains"}:
            if isinstance(actual, str):
                result = cls._normalise_text(expected) in cls._normalise_text(actual)
            elif isinstance(actual, Sequence) and not isinstance(actual, (bytes, bytearray)):
                result = any(cls._equal(item, expected) for item in actual)
            else:
                raise RuleEvaluationError(
                    f"operator '{operator}' requires a string or list profile value"
                )
            return result if operator == "contains" else not result
        raise RuleEvaluationError(f"unsupported operator '{operator}'")

    @staticmethod
    def _equal(left: Any, right: Any) -> bool:
        if isinstance(left, str) and isinstance(right, str):
            return left.strip().casefold() == right.strip().casefold()
        return left == right

    @staticmethod
    def _number(value: Any, label: str) -> Real:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise RuleEvaluationError(f"{label} must be numeric")
        return value

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())

    @staticmethod
    def _normalise_text(value: Any) -> str:
        return str(value).strip().casefold()

    @staticmethod
    def _priority(rule: Mapping[str, Any]) -> int:
        priority = rule.get("priority", 1000)
        if isinstance(priority, bool) or not isinstance(priority, int):
            return 1000
        return priority

    @staticmethod
    def _status_for(
        matched: list[dict[str, Any]],
        unknown: list[dict[str, Any]],
        disqualifiers: list[dict[str, Any]],
    ) -> str:
        if disqualifiers:
            return LIKELY_NOT_ELIGIBLE
        if unknown:
            return POSSIBLY_ELIGIBLE if matched else NOT_ENOUGH_INFORMATION
        return LIKELY_ELIGIBLE

    @staticmethod
    def _build_why(
        status: str,
        matched: list[dict[str, Any]],
        unknown: list[dict[str, Any]],
        disqualifiers: list[dict[str, Any]],
    ) -> str:
        if status == LIKELY_NOT_ELIGIBLE:
            return (
                f"{len(disqualifiers)} provided answer(s) conflict with an eligibility or "
                "exclusion rule. Review the listed potential disqualifiers and verify them "
                "with the administering authority."
            )
        if status == NOT_ENOUGH_INFORMATION:
            return (
                f"No rule could be confirmed from the supplied profile; {len(unknown)} "
                "condition(s) still need an answer."
            )
        if status == POSSIBLY_ELIGIBLE:
            return (
                f"{len(matched)} known condition(s) are satisfied, but {len(unknown)} "
                "condition(s) remain unanswered. No known answer currently disqualifies you."
            )
        return (
            f"All {len(matched)} encoded eligibility and exclusion conditions are satisfied "
            "by the supplied answers. Documents and official records still require verification."
        )

    @staticmethod
    def _without_priority(item: Mapping[str, Any]) -> dict[str, Any]:
        return {key: deepcopy(value) for key, value in item.items() if key != "priority"}

    @classmethod
    def _targeted_questions(
        cls,
        unknown: list[dict[str, Any]],
        max_questions: int | None,
    ) -> list[dict[str, Any]]:
        if max_questions == 0:
            return []
        ordered = sorted(unknown, key=lambda item: (item["priority"], item["rule_id"]))
        questions: list[dict[str, Any]] = []
        seen_fields: set[str] = set()
        for item in ordered:
            if item["field"] in seen_fields:
                continue
            seen_fields.add(item["field"])
            questions.append(
                {
                    "rule_id": item["rule_id"],
                    "field": item["field"],
                    "question": item["question"],
                    "reason": item["reason"],
                }
            )
            if max_questions is not None and len(questions) >= max_questions:
                break
        return questions


__all__ = [
    "LIKELY_ELIGIBLE",
    "POSSIBLY_ELIGIBLE",
    "NOT_ENOUGH_INFORMATION",
    "LIKELY_NOT_ELIGIBLE",
    "SchemeEligibilityEngine",
    "SchemeEligibilityError",
    "SchemeNotFoundError",
    "SchemeDatasetError",
]
