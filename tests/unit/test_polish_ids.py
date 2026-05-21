from __future__ import annotations

import json
from pathlib import Path

import pytest

from kithairon.errors import PolishError
from kithairon.polish.ids import allocate_polish_request_token, derived_candidate_id


def test_polish_ids_are_filename_safe_and_include_request_token() -> None:
    candidate_id = derived_candidate_id("strict_0001", "r001", 2)

    assert candidate_id == "strict_0001__polish__r001__002"
    assert "/" not in candidate_id
    assert " " not in candidate_id


def test_polish_id_allocator_advances_past_existing_persisted_children(tmp_path: Path) -> None:
    _write_index(
        tmp_path,
        {
            "strict_0001": {},
            "strict_0001__polish__r001__001": {},
            "strict_0001__polish__r002__001": {},
            "other_parent__polish__r001__001": {},
        },
    )

    assert allocate_polish_request_token(tmp_path, parent_id="strict_0001") == "r003"
    assert allocate_polish_request_token(tmp_path, parent_id="other_parent") == "r002"


def test_polish_id_allocator_rejects_unsafe_parent_or_token() -> None:
    with pytest.raises(PolishError, match="Candidate id fragment is not safe"):
        derived_candidate_id("../strict", "r001", 1)
    with pytest.raises(PolishError, match="Candidate id fragment is not safe"):
        derived_candidate_id("strict_0001", "bad token", 1)


def test_polish_id_allocator_reports_unreadable_artifact_index(tmp_path: Path) -> None:
    (tmp_path / "artifact_index.json").write_text("{", encoding="utf-8")

    with pytest.raises(PolishError) as exc_info:
        allocate_polish_request_token(tmp_path, parent_id="strict_0001")

    assert exc_info.value.diagnostic.code == "polish_request_token_allocation_failed"
    assert exc_info.value.diagnostic.details["path"] == str(tmp_path / "artifact_index.json")


def _write_index(tmp_path: Path, candidates: dict[str, object]) -> None:
    (tmp_path / "artifact_index.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "root": str(tmp_path),
                "run_artifacts": {},
                "candidates": candidates,
            }
        ),
        encoding="utf-8",
    )
