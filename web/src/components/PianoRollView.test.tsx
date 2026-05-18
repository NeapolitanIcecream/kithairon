// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, NoteViz } from '../api/schemas'
import { PianoRollView } from './PianoRollView'

describe('PianoRollView', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    vi.stubGlobal(
      'ResizeObserver',
      class ResizeObserver {
        observe() {
          return undefined
        }
        unobserve() {
          return undefined
        }
        disconnect() {
          return undefined
        }
      },
    )
  })

  it('selects notes by visualization event id', async () => {
    const onSelectEvent = vi.fn()
    render(
      <MantineProvider>
        <PianoRollView
          candidate={candidate()}
          selectedEventIds={[]}
          modifiedEventIds={[]}
          onSelectEvent={onSelectEvent}
        />
      </MantineProvider>,
    )

    await userEvent.click(screen.getByLabelText('Select follower:n0001'))

    expect(onSelectEvent).toHaveBeenCalledWith('follower:n0001')
  })
})

function candidate(): CandidateViz {
  return {
    candidate_id: 'strict_0001',
    rank: 1,
    title: 'Candidate 1',
    transform: {
      engine: 'strict',
      strict_canon: true,
      label: 'transposition',
      delay_q: { text: '1', value: 1 },
      interval: 7,
      transform_mode: 'transposition',
      inversion_axis: null,
      rhythm_scale: '1',
    },
    score: {
      total: 92,
      by_category: {},
      by_rule: {},
      bonuses: {},
    },
    notes: [
      note('leader:n0001', 'leader', 60, 0, 1),
      note('follower:n0001', 'follower', 67, 1, 2),
    ],
    violations: [],
    repair_actions: [],
    artifacts: {},
    metadata: {},
  }
}

function note(
  eventId: string,
  voiceId: string,
  pitch: number,
  start: number,
  end: number,
): NoteViz {
  const role = voiceId === 'leader' ? 'leader' : 'follower'
  return {
    event_id: eventId,
    ir_event_id: eventId.split(':')[1],
    voice_id: voiceId,
    role,
    pitch,
    pitch_name: pitch === 60 ? 'C4' : 'G4',
    start_q: { text: String(start), value: start },
    duration_q: { text: String(end - start), value: end - start },
    end_q: { text: String(end), value: end },
    bar: 1,
    beat: { text: String(start + 1), value: start + 1 },
    velocity: null,
    source_event_id: null,
    transform_origin: role === 'leader' ? 'input' : 'strict_transform',
    repair_action_id: null,
    score_element_id: null,
  }
}
