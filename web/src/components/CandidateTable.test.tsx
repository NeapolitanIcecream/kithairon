// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz } from '../api/schemas'
import { CandidateTable } from './CandidateTable'

describe('CandidateTable', () => {
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

  it('selects a candidate by its stable candidate id', async () => {
    const onSelectCandidate = vi.fn()
    render(
      <MantineProvider>
        <CandidateTable
          candidates={[candidate('strict_0001'), candidate('repair_0002')]}
          selectedCandidateId="strict_0001"
          onSelectCandidate={onSelectCandidate}
        />
      </MantineProvider>,
    )

    await userEvent.click(screen.getByLabelText('Select Candidate 2'))

    expect(onSelectCandidate).toHaveBeenCalledWith('repair_0002')
    expect(screen.getAllByText('70.0')[0]).toBeTruthy()
  })
})

function candidate(candidateId: string): CandidateViz {
  const rank = candidateId.endsWith('0001') ? 1 : 2
  return {
    candidate_id: candidateId,
    rank,
    title: `Candidate ${rank}`,
    transform: {
      engine: candidateId.startsWith('repair') ? 'repair' : 'strict',
      strict_canon: candidateId.startsWith('strict'),
      label: 'transposition',
      delay_q: { text: '1', value: 1 },
      interval: 7,
      transform_mode: 'transposition',
      inversion_axis: null,
      rhythm_scale: '1',
    },
    score: {
      total: rank === 1 ? 92 : 81,
      by_category: {},
      by_rule: {},
      bonuses: {},
    },
    musicality: {
      total: rank === 1 ? 75 : 70,
      metrics: [],
      raw_values: {},
      normalized_values: {},
      weights: {},
    },
    notes: [],
    violations: [
      {
        violation_id: `${candidateId}:v0001:range`,
        rule_id: 'range',
        severity: 'hard',
        penalty: 5,
        message: 'Follower is outside the allowed range.',
        bar: 1,
        beat: { text: '1', value: 1 },
        start_q: { text: '0', value: 0 },
        end_q: { text: '1', value: 1 },
        voice_ids: ['follower'],
        event_ids: ['follower:n0001'],
        ir_event_ids: ['n0001'],
        related_event_ids: [],
        category: 'range',
      },
    ],
    repair_actions: [],
    artifacts: {},
    metadata: {},
  }
}
