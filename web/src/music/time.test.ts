import { describe, expect, it } from 'vitest'
import type { NoteViz } from '../api/schemas'
import {
  activeEventIdsAt,
  durationQ,
  midiToNoteName,
  playbackNotesFromViz,
  quarterSeconds,
} from './time'

describe('playback time helpers', () => {
  it('converts MIDI pitch to Tone note names', () => {
    expect(midiToNoteName(60)).toBe('C4')
    expect(midiToNoteName(67)).toBe('G4')
  })

  it('creates playback notes and finds active event ids at a position', () => {
    const notes = playbackNotesFromViz([
      note('leader:n0001', 60, 0, 1),
      note('follower:n0001', 67, 0.5, 1.5),
      note('follower:n0002', null, 2, 3),
    ])

    expect(activeEventIdsAt(notes, 0.75)).toEqual(['leader:n0001', 'follower:n0001'])
    expect(activeEventIdsAt(notes, 2.5)).toEqual(['follower:n0002'])
    expect(durationQ(notes)).toBe(3)
    expect(quarterSeconds(2)).toBe(0.25)
  })
})

function note(eventId: string, pitch: number | null, start: number, end: number): NoteViz {
  return {
    event_id: eventId,
    ir_event_id: eventId.split(':')[1],
    voice_id: eventId.split(':')[0],
    role: eventId.startsWith('leader') ? 'leader' : 'follower',
    pitch,
    pitch_name: pitch === null ? null : midiToNoteName(pitch),
    start_q: { text: String(start), value: start },
    duration_q: { text: String(end - start), value: end - start },
    end_q: { text: String(end), value: end },
    bar: 1,
    beat: { text: String(start + 1), value: start + 1 },
    velocity: null,
    source_event_id: null,
    transform_origin: eventId.startsWith('leader') ? 'input' : 'strict_transform',
    repair_action_id: null,
    score_element_id: null,
  }
}
