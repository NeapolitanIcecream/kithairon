"""Music21 score construction and candidate export helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from music21 import meter, note, stream, tempo

from kithairon.ir import CanonCandidate, Melody, NoteEvent, Voice


@dataclass(frozen=True)
class CandidateExportPaths:
    musicxml: Path
    midi: Path


def candidate_to_score(candidate: CanonCandidate) -> Any:
    score: Any = stream.Score(id=candidate.id)
    for voice in candidate.voices:
        score.insert(0, _voice_to_part(voice))
    return score


def write_candidate_exports(
    candidate: CanonCandidate,
    output_dir: Path,
    *,
    stem: str,
) -> CandidateExportPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    score = candidate_to_score(candidate)
    musicxml_path = output_dir / f"{stem}.musicxml"
    midi_path = output_dir / f"{stem}.mid"
    score.write("musicxml", fp=str(musicxml_path))
    score.write("midi", fp=str(midi_path))
    return CandidateExportPaths(musicxml=musicxml_path, midi=midi_path)


def _voice_to_part(voice: Voice) -> Any:
    part: Any = stream.Part(id=voice.name)
    part.partName = voice.name
    _insert_melody_metadata(part, voice.melody)
    for event in voice.melody.events:
        part.insert(float(event.start), _event_to_music21(event))
    return part


def _insert_melody_metadata(part: Any, melody: Melody) -> None:
    part.insert(0, meter.TimeSignature(melody.time_signature))
    if melody.tempo_bpm is not None:
        part.insert(0, tempo.MetronomeMark(number=melody.tempo_bpm))


def _event_to_music21(event: NoteEvent) -> Any:
    quarter_length = float(event.duration)
    if event.pitch is None:
        return note.Rest(quarterLength=quarter_length)

    built_note: Any = note.Note(quarterLength=quarter_length)
    built_note.pitch.midi = event.pitch
    built_note.volume.velocity = event.velocity
    return built_note
