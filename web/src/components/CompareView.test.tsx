// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, RunSummary } from '../api/schemas'
import { CompareView } from './CompareView'

describe('CompareView', () => {
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

  it('compares score, musicality, rewrite lineage, and exports', async () => {
    const onClear = vi.fn()
    render(
      <MantineProvider>
        <CompareView
          runSummary={runSummary()}
          candidates={[
            candidate('strict_0001', 92, 75, {}),
            candidate('strict_0001_polish_001', 88, 83, {
              parent_candidate_id: 'strict_0001',
              edited_bars: [1, 2],
              rewrite_voice: 'follower',
            }),
          ]}
          onClear={onClear}
        />
      </MantineProvider>,
    )

    expect(screen.getByText('A/B Compare')).toBeTruthy()
    expect(screen.getByText('92.0')).toBeTruthy()
    expect(screen.getByText('83.0')).toBeTruthy()
    expect(screen.getByText('Parent strict_0001')).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: 'Clear' }))

    expect(onClear).toHaveBeenCalledOnce()
  })
})

function runSummary(): RunSummary {
  return {
    run_id: 'run-1',
    input_name: 'theme.musicxml',
    created_at: '2026-05-20T00:00:00Z',
    config_summary: {},
    artifacts: {},
    candidates: [],
  }
}

function candidate(
  candidateId: string,
  score: number,
  musicality: number,
  metadata: Record<string, unknown>,
): CandidateViz {
  return {
    candidate_id: candidateId,
    rank: 1,
    title: candidateId,
    transform: {
      engine: 'strict',
      strict_canon: !candidateId.includes('polish'),
      label: 'transposition',
      delay_q: { text: '1', value: 1 },
      interval: -12,
      transform_mode: 'transposition',
      inversion_axis: null,
      rhythm_scale: '1',
    },
    score: { total: score, by_category: {}, by_rule: {}, bonuses: {} },
    musicality: {
      total: musicality,
      metrics: [],
      raw_values: {},
      normalized_values: {},
      weights: {},
    },
    notes: [],
    violations: [],
    repair_actions: [],
    artifacts: { musicxml: `experiments/experiment-0001/candidates/${candidateId}.musicxml` },
    metadata,
  }
}
