// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, RepairAction } from '../api/schemas'
import { StrictRelaxedDiff } from './StrictRelaxedDiff'

describe('StrictRelaxedDiff', () => {
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
  })

  it('selects repair actions for relaxed candidates', async () => {
    const onSelectAction = vi.fn()
    render(
      <MantineProvider>
        <StrictRelaxedDiff
          candidate={candidate()}
          selectedActionId={null}
          onSelectAction={onSelectAction}
        />
      </MantineProvider>,
    )

    await userEvent.click(screen.getByText('octave_shift: 55 -> 67'))

    expect(onSelectAction).toHaveBeenCalledWith(
      expect.objectContaining({
        action_id: 'repair_0001:repair:n0001',
        original_event_id: 'follower:n0001',
      }),
    )
  })
})

function candidate(): CandidateViz {
  return {
    candidate_id: 'repair_0001',
    rank: 2,
    title: 'Candidate 2',
    transform: {
      engine: 'repair',
      strict_canon: false,
      label: 'transposition',
      delay_q: { text: '1', value: 1 },
      interval: 7,
      transform_mode: 'transposition',
      inversion_axis: null,
      rhythm_scale: '1',
    },
    score: {
      total: 84,
      by_category: {},
      by_rule: {},
      bonuses: {},
    },
    notes: [],
    violations: [],
    repair_actions: [action()],
    artifacts: {},
    metadata: {},
  }
}

function action(): RepairAction {
  return {
    action_id: 'repair_0001:repair:n0001',
    kind: 'octave_displacement',
    original_event_id: 'follower:n0001',
    new_event_id: 'follower:n0001',
    message: 'octave_shift: 55 -> 67',
    start_q: { text: '1', value: 1 },
    bar: 1,
    beat: { text: '2', value: 2 },
  }
}
