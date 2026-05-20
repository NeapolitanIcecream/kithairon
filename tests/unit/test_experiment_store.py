from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from kithairon.experiments.store import create_experiment, list_experiments, patch_experiment
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.polish.models import PolishRequest
from kithairon.visualization.materialize import materialize_candidate
from kithairon.visualization.models import ExperimentPatchDTO


def test_experiment_store_persists_variants_notes_and_relative_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    (run_dir / "artifact_index.json").write_text(
        json.dumps(
            {"run_id": "run-1", "root": str(run_dir), "run_artifacts": {}, "candidates": {}}
        ),
        encoding="utf-8",
    )
    candidate = materialize_candidate(_candidate("strict_0001_polish_001"))
    request = PolishRequest(bar_start=1, bar_end=1, lock_voice="leader")

    experiment = create_experiment(
        run_dir,
        source_candidate_id="strict_0001",
        source_request=request.model_dump(mode="json"),
        candidates=[candidate],
    )
    patched = patch_experiment(
        run_dir,
        experiment.experiment_id,
        ExperimentPatchDTO(
            notes="keep the smoother lower line",
            variant_status={candidate.candidate_id: "kept"},
        ),
    )

    reopened = list_experiments(run_dir)
    artifact_index = json.loads((run_dir / "artifact_index.json").read_text(encoding="utf-8"))
    stored_artifacts = reopened[0].variants[0].candidate.artifacts

    assert patched.variants[0].status == "kept"
    assert reopened[0].notes == "keep the smoother lower line"
    assert (run_dir / "experiments" / experiment.experiment_id / "notes.md").read_text() == (
        "keep the smoother lower line"
    )
    assert set(stored_artifacts) == {"musicxml", "midi"}
    assert all(not Path(path).is_absolute() for path in stored_artifacts.values())
    assert artifact_index["candidates"][candidate.candidate_id]["musicxml"] == stored_artifacts[
        "musicxml"
    ]


def _candidate(candidate_id: str) -> CanonCandidate:
    leader = Voice(
        name="leader",
        role="leader",
        melody=Melody(
            events=(
                NoteEvent(id="n1", pitch=60, start=Fraction(0), duration=Fraction(1)),
                NoteEvent(id="n2", pitch=62, start=Fraction(1), duration=Fraction(1)),
            ),
            time_signature="4/4",
        ),
    )
    follower = Voice(
        name="follower",
        role="follower",
        melody=Melody(
            events=(
                NoteEvent(id="n1", pitch=48, start=Fraction(1), duration=Fraction(1)),
                NoteEvent(id="n2", pitch=50, start=Fraction(2), duration=Fraction(1)),
            ),
            time_signature="4/4",
        ),
    )
    return CanonCandidate(
        id=candidate_id,
        voices=(leader, follower),
        transform_spec=TransformSpec(delay=Fraction(1), interval=-12),
        engine="strict",
        strict_canon=False,
        score=88.0,
        violations=(),
    )
