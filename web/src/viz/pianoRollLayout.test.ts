import { describe, expect, it } from 'vitest'
import type { NoteViz } from '../api/schemas'
import { buildPianoRollLayout } from './pianoRollLayout'

describe('buildPianoRollLayout', () => {
  it('places notes in separate voice lanes and marks rests', () => {
    const layout = buildPianoRollLayout(
      [
        note({ eventId: 'leader:n0001', voiceId: 'leader', pitch: 60, start: 0, end: 1 }),
        note({ eventId: 'follower:n0001', voiceId: 'follower', pitch: null, start: 1, end: 2 }),
      ],
      {
        width: 640,
        laneHeight: 72,
        visibleStart: 0,
        visibleDuration: 4,
      },
    )

    expect(layout.lanes.map((lane) => lane.voiceId)).toEqual(['leader', 'follower'])
    expect(layout.notes[0].y).toBeLessThan(layout.notes[1].y)
    expect(layout.notes[1].isRest).toBe(true)
    expect(layout.notes[0].x).toBe(64)
    expect(layout.notes[0].width).toBeGreaterThan(100)
  })

  it('adds beat and bar grid lines from note timing', () => {
    const layout = buildPianoRollLayout(
      [
        note({ eventId: 'leader:n0001', voiceId: 'leader', pitch: 60, start: 0, end: 1 }),
        note({
          eventId: 'leader:n0002',
          voiceId: 'leader',
          pitch: 62,
          start: 4,
          end: 5,
          bar: 2,
          beat: 1,
        }),
      ],
      {
        width: 640,
        laneHeight: 72,
        visibleStart: 0,
        visibleDuration: 5,
      },
    )

    expect(layout.gridLines.some((line) => line.id === 'beat:1')).toBe(true)
    expect(layout.gridLines.some((line) => line.id === 'bar:1')).toBe(true)
    expect(layout.gridLines.some((line) => line.id === 'bar:2')).toBe(true)
  })
})

function note({
  eventId,
  voiceId,
  pitch,
  start,
  end,
  bar = 1,
  beat = start + 1,
}: {
  eventId: string
  voiceId: string
  pitch: number | null
  start: number
  end: number
  bar?: number
  beat?: number
}): NoteViz {
  return {
    event_id: eventId,
    ir_event_id: eventId.split(':')[1],
    voice_id: voiceId,
    role: voiceId === 'leader' ? 'leader' : 'follower',
    pitch,
    pitch_name: pitch === null ? null : 'C4',
    start_q: { text: String(start), value: start },
    duration_q: { text: String(end - start), value: end - start },
    end_q: { text: String(end), value: end },
    bar,
    beat: { text: String(beat), value: beat },
    velocity: null,
    source_event_id: null,
    transform_origin: voiceId === 'leader' ? 'input' : 'strict_transform',
    repair_action_id: null,
    score_element_id: null,
  }
}
