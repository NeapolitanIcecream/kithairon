import { scaleLinear } from 'd3-scale'
import type { NoteViz } from '../api/schemas'

export type PianoRollLayoutOptions = {
  width: number
  laneHeight: number
  visibleStart: number
  visibleDuration: number
}

export type PianoRollLane = {
  voiceId: string
  y: number
  height: number
}

export type PianoRollNoteBox = {
  eventId: string
  irEventId: string
  voiceId: string
  pitch: number | null
  pitchName: string | null
  start: number
  end: number
  x: number
  y: number
  width: number
  height: number
  isRest: boolean
}

export type PianoRollGridLine = {
  id: string
  x: number
  value: number
  kind: 'bar' | 'beat'
  label: string
}

export type PianoRollLayout = {
  width: number
  height: number
  totalDuration: number
  visibleStart: number
  visibleEnd: number
  lanes: PianoRollLane[]
  notes: PianoRollNoteBox[]
  gridLines: PianoRollGridLine[]
}

const margin = {
  top: 24,
  right: 18,
  bottom: 30,
  left: 64,
}

export function buildPianoRollLayout(
  notes: NoteViz[],
  options: PianoRollLayoutOptions,
): PianoRollLayout {
  const voiceIds = unique(notes.map((note) => note.voice_id))
  const laneCount = Math.max(1, voiceIds.length)
  const height = margin.top + margin.bottom + laneCount * options.laneHeight
  const totalDuration = Math.max(1, ...notes.map((note) => note.end_q.value))
  const visibleDuration = Math.max(0.25, options.visibleDuration)
  const visibleStart = clamp(options.visibleStart, 0, Math.max(0, totalDuration - visibleDuration))
  const visibleEnd = visibleStart + visibleDuration
  const xScale = scaleLinear()
    .domain([visibleStart, visibleEnd])
    .range([margin.left, options.width - margin.right])

  const pitches = notes
    .map((note) => note.pitch)
    .filter((pitch): pitch is number => pitch !== null)
  const minPitch = pitches.length === 0 ? 60 : Math.min(...pitches) - 1
  const maxPitch = pitches.length === 0 ? 72 : Math.max(...pitches) + 1

  const lanes = voiceIds.map((voiceId, index) => ({
    voiceId,
    y: margin.top + index * options.laneHeight,
    height: options.laneHeight,
  }))
  const laneByVoice = new Map(lanes.map((lane) => [lane.voiceId, lane]))

  return {
    width: options.width,
    height,
    totalDuration,
    visibleStart,
    visibleEnd,
    lanes,
    notes: notes.map((note) =>
      noteBox({
        note,
        lane: laneByVoice.get(note.voice_id) ?? lanes[0],
        minPitch,
        maxPitch,
        xScale,
      }),
    ),
    gridLines: gridLines(notes, xScale, visibleStart, visibleEnd),
  }
}

function noteBox({
  note,
  lane,
  minPitch,
  maxPitch,
  xScale,
}: {
  note: NoteViz
  lane: PianoRollLane
  minPitch: number
  maxPitch: number
  xScale: (value: number) => number
}): PianoRollNoteBox {
  const start = note.start_q.value
  const end = note.end_q.value
  const x = xScale(start)
  const width = Math.max(4, xScale(end) - x)
  const isRest = note.pitch === null
  const lanePadding = 10
  const pitchScale = scaleLinear()
    .domain([minPitch, maxPitch])
    .range([lane.y + lane.height - lanePadding, lane.y + lanePadding])
    .clamp(true)
  const noteHeight = isRest ? 4 : 12
  const y =
    note.pitch === null
      ? lane.y + lane.height / 2 - noteHeight / 2
      : pitchScale(note.pitch) - noteHeight / 2

  return {
    eventId: note.event_id,
    irEventId: note.ir_event_id,
    voiceId: note.voice_id,
    pitch: note.pitch,
    pitchName: note.pitch_name,
    start,
    end,
    x,
    y,
    width,
    height: noteHeight,
    isRest,
  }
}

function gridLines(
  notes: NoteViz[],
  xScale: (value: number) => number,
  visibleStart: number,
  visibleEnd: number,
): PianoRollGridLine[] {
  const lines: PianoRollGridLine[] = []
  const firstBeat = Math.ceil(visibleStart)
  const lastBeat = Math.floor(visibleEnd)
  for (let beat = firstBeat; beat <= lastBeat; beat += 1) {
    lines.push({
      id: `beat:${beat}`,
      x: xScale(beat),
      value: beat,
      kind: 'beat',
      label: String(beat),
    })
  }

  const barStarts = new Map<number, number>()
  for (const note of notes) {
    if (note.bar === null || note.beat === null || note.beat.value !== 1) {
      continue
    }
    const current = barStarts.get(note.bar)
    if (current === undefined || note.start_q.value < current) {
      barStarts.set(note.bar, note.start_q.value)
    }
  }
  for (const [bar, start] of barStarts) {
    if (start < visibleStart || start > visibleEnd) {
      continue
    }
    lines.push({
      id: `bar:${bar}`,
      x: xScale(start),
      value: start,
      kind: 'bar',
      label: `Bar ${bar}`,
    })
  }

  return lines.sort((left, right) => left.value - right.value || lineOrder(left.kind, right.kind))
}

function lineOrder(left: PianoRollGridLine['kind'], right: PianoRollGridLine['kind']): number {
  if (left === right) {
    return 0
  }
  return left === 'bar' ? -1 : 1
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values))
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
