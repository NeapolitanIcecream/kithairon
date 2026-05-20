// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, Experiment, RunSummary } from '../api/schemas'
import { CandidateLabPanel } from './CandidateLabPanel'

describe('CandidateLabPanel', () => {
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

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('persists notes and keep status through the experiment API', async () => {
    const experiment = experimentFixture()
    const updated = {
      ...experiment,
      notes: 'keeper',
      variants: [{ ...experiment.variants[0], status: 'kept' as const }],
    }
    const fetchMock = vi.fn(async (_path: string, _init?: RequestInit) => {
      return new Response(JSON.stringify(updated), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const onExperimentsChange = vi.fn()

    render(
      <MantineProvider>
        <CandidateLabPanel
          runSummary={runSummary()}
          experiments={[experiment]}
          onExperimentsChange={onExperimentsChange}
          onSelectCandidate={vi.fn()}
        />
      </MantineProvider>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Keep' }))

    await waitFor(() => expect(onExperimentsChange).toHaveBeenCalledWith([updated]))
    const call = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(call[0]).toBe('/api/runs/run-1/experiments/experiment-0001')
    expect(JSON.parse(call[1].body as string)).toEqual({
      variant_status: { strict_0001_polish_001: 'kept' },
    })
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

function experimentFixture(): Experiment {
  return {
    experiment_id: 'experiment-0001',
    source_candidate_id: 'strict_0001',
    source_request: { bar_start: 1, bar_end: 1, objective_preset: 'general_polish' },
    created_at: '2026-05-20T00:00:00Z',
    notes: '',
    variants: [
      {
        candidate_id: 'strict_0001_polish_001',
        status: 'undecided',
        candidate: candidateFixture(),
      },
    ],
  }
}

function candidateFixture(): CandidateViz {
  return {
    candidate_id: 'strict_0001_polish_001',
    rank: 1,
    title: 'Candidate 1',
    transform: {
      engine: 'strict',
      strict_canon: false,
      label: 'relaxed canon',
      delay_q: { text: '1', value: 1 },
      interval: -12,
      transform_mode: 'transposition',
      inversion_axis: null,
      rhythm_scale: '1',
    },
    score: { total: 88, by_category: {}, by_rule: {}, bonuses: {} },
    musicality: {
      total: 80,
      metrics: [],
      raw_values: {},
      normalized_values: {},
      weights: {},
    },
    notes: [],
    violations: [],
    repair_actions: [],
    artifacts: {},
    metadata: {},
  }
}
