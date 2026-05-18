import type { NoteViz } from '../api/schemas'

export type PlaybackNote = {
  eventId: string
  pitch: number | null
  noteName: string | null
  startQ: number
  durationQ: number
  endQ: number
  velocity: number
}

const pitchClassNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

export function playbackNotesFromViz(notes: NoteViz[]): PlaybackNote[] {
  return notes
    .map((note) => ({
      eventId: note.event_id,
      pitch: note.pitch,
      noteName: note.pitch === null ? null : midiToNoteName(note.pitch),
      startQ: note.start_q.value,
      durationQ: note.duration_q.value,
      endQ: note.end_q.value,
      velocity: normalizeVelocity(note.velocity),
    }))
    .sort((left, right) => left.startQ - right.startQ || left.eventId.localeCompare(right.eventId))
}

export function activeEventIdsAt(notes: PlaybackNote[], positionQ: number): string[] {
  return notes
    .filter((note) => positionQ >= note.startQ && positionQ < note.endQ)
    .map((note) => note.eventId)
}

export function durationQ(notes: PlaybackNote[]): number {
  return Math.max(0, ...notes.map((note) => note.endQ))
}

export function quarterSeconds(tempoMultiplier: number): number {
  return 0.5 / Math.max(0.25, tempoMultiplier)
}

export function midiToNoteName(midiPitch: number): string {
  const pitchClass = pitchClassNames[mod(midiPitch, 12)]
  const octave = Math.floor(midiPitch / 12) - 1
  return `${pitchClass}${octave}`
}

function normalizeVelocity(velocity: number | null): number {
  if (velocity === null) {
    return 0.75
  }
  return Math.min(1, Math.max(0.1, velocity / 127))
}

function mod(value: number, divisor: number): number {
  return ((value % divisor) + divisor) % divisor
}
