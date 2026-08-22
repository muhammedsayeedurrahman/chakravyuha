"""Regression checks for safety-critical retrieval metadata parsing."""

from backend.legal.rag import LegalRAG


def test_persisted_false_strings_are_not_truthy() -> None:
    assert LegalRAG._metadata_bool("False") is False
    assert LegalRAG._metadata_bool("false") is False
    assert LegalRAG._metadata_bool("0") is False


def test_persisted_true_strings_are_parsed_explicitly() -> None:
    assert LegalRAG._metadata_bool("True") is True
    assert LegalRAG._metadata_bool("1") is True
    assert LegalRAG._metadata_bool(True) is True
