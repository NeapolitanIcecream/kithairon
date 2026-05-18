import { useMemo, useState } from 'react'
import { Alert, Box, Button, Group, ScrollArea, Slider, Stack, Text } from '@mantine/core'
import type { CandidateViz } from '../api/schemas'
import { buildPianoRollLayout, type PianoRollNoteBox } from '../viz/pianoRollLayout'

type PianoRollViewProps = {
  candidate: CandidateViz | null
  selectedEventId: string | null
  onSelectEvent: (eventId: string) => void
}

const width = 900
const laneHeight = 78

export function PianoRollView({
  candidate,
  selectedEventId,
  onSelectEvent,
}: PianoRollViewProps) {
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState(0)
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null)
  const totalDuration = useMemo(
    () => Math.max(1, ...(candidate?.notes ?? []).map((note) => note.end_q.value)),
    [candidate],
  )
  const visibleDuration = Math.max(0.5, totalDuration / zoom)
  const maxPan = Math.max(0, totalDuration - visibleDuration)
  const visibleStart = Math.min(pan, maxPan)
  const layout = useMemo(
    () =>
      buildPianoRollLayout(candidate?.notes ?? [], {
        width,
        laneHeight,
        visibleStart,
        visibleDuration,
      }),
    [candidate, visibleDuration, visibleStart],
  )

  if (candidate === null) {
    return (
      <Alert color="gray" variant="light" title="No piano roll">
        No candidate selected.
      </Alert>
    )
  }

  const hoveredNote = layout.notes.find((note) => note.eventId === hoveredEventId) ?? null

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="center">
        <Group gap="xs">
          <Button
            size="xs"
            variant="light"
            disabled={zoom <= 1}
            onClick={() => setZoom((current) => Math.max(1, current - 0.5))}
          >
            Zoom -
          </Button>
          <Text size="sm" c="dimmed">
            {zoom.toFixed(1)}x
          </Text>
          <Button
            size="xs"
            variant="light"
            disabled={zoom >= 6}
            onClick={() => setZoom((current) => Math.min(6, current + 0.5))}
          >
            Zoom +
          </Button>
        </Group>
        <Box className="piano-roll-pan">
          <Slider
            min={0}
            max={maxPan}
            step={0.25}
            value={visibleStart}
            disabled={maxPan <= 0}
            label={(value) => value.toFixed(2)}
            onChange={setPan}
          />
        </Box>
      </Group>

      <ScrollArea type="auto" offsetScrollbars>
        <svg
          className="piano-roll-svg"
          width={layout.width}
          height={layout.height}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="img"
          aria-label={`${candidate.title} piano roll`}
        >
          <rect className="piano-roll-background" width={layout.width} height={layout.height} />
          {layout.gridLines.map((line) => (
            <g key={line.id}>
              <line
                className={`piano-roll-grid ${line.kind === 'bar' ? 'bar-line' : 'beat-line'}`}
                x1={line.x}
                x2={line.x}
                y1={0}
                y2={layout.height - 24}
              />
              {line.kind === 'bar' ? (
                <text className="piano-roll-grid-label" x={line.x + 4} y={14}>
                  {line.label}
                </text>
              ) : null}
            </g>
          ))}
          {layout.lanes.map((lane) => (
            <g key={lane.voiceId}>
              <rect
                className="piano-roll-lane"
                x={0}
                y={lane.y}
                width={layout.width}
                height={lane.height}
              />
              <text className="piano-roll-lane-label" x={12} y={lane.y + 22}>
                {lane.voiceId}
              </text>
            </g>
          ))}
          {layout.notes.map((note) => (
            <PianoRollNote
              key={note.eventId}
              note={note}
              selected={note.eventId === selectedEventId}
              hovered={note.eventId === hoveredEventId}
              onSelectEvent={onSelectEvent}
              onHover={setHoveredEventId}
            />
          ))}
        </svg>
      </ScrollArea>
      <Text size="sm" c="dimmed">
        {hoveredNote === null
          ? `${layout.notes.length} events`
          : `${hoveredNote.eventId} ${hoveredNote.pitchName ?? 'rest'}`}
      </Text>
    </Stack>
  )
}

function PianoRollNote({
  note,
  selected,
  hovered,
  onSelectEvent,
  onHover,
}: {
  note: PianoRollNoteBox
  selected: boolean
  hovered: boolean
  onSelectEvent: (eventId: string) => void
  onHover: (eventId: string | null) => void
}) {
  const className = [
    'piano-roll-note',
    note.voiceId === 'leader' ? 'leader-note' : 'follower-note',
    note.isRest ? 'rest-note' : '',
    selected ? 'selected-note' : '',
    hovered ? 'hovered-note' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={`Select ${note.eventId}`}
      onClick={() => onSelectEvent(note.eventId)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          onSelectEvent(note.eventId)
        }
      }}
      onMouseEnter={() => onHover(note.eventId)}
      onMouseLeave={() => onHover(null)}
    >
      <rect
        className={className}
        x={note.x}
        y={note.y}
        width={note.width}
        height={note.height}
        rx={note.isRest ? 1 : 3}
      />
      <title>
        {note.eventId} {note.pitchName ?? 'rest'}
      </title>
    </g>
  )
}
