// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, RunSummary } from '../api/schemas'
import { FeedbackPanel } from './FeedbackPanel'

describe('FeedbackPanel', () => {
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

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('translates feedback and runs the selected suggested action', async () => {
    const selectedCandidate = candidate('strict_0001')
    const variant = {
      ...selectedCandidate,
      candidate_id: 'strict_0001_polish_001',
      score: { ...selectedCandidate.score, total: 89 },
      metadata: { parent_candidate_id: 'strict_0001' },
    }
    const fetchMock = vi.fn(async (...args: [string, RequestInit?]) => {
      const [path] = args
      if (path.endsWith('/feedback/translate')) {
        return new Response(
          JSON.stringify({
            input_text: 'cadence weak',
            candidate_id: 'strict_0001',
            intents: ['cadence_weak'],
            target: { bar_start: 3, bar_end: 4 },
            actions: [
              {
                action_id: 'feedback-action-01',
                label: 'Strengthen cadence',
                reason: 'Mapped feedback intent cadence_weak.',
                request: {
                  bar_start: 3,
                  bar_end: 4,
                  lock_voice: 'none',
                  rewrite_voice: 'auto',
                  max_variants: 6,
                  objective_preset: 'strengthen_cadence',
                  objective_overrides: { cadence_motion_reward: 2.5 },
                },
              },
            ],
            explanation: 'Recognized feedback intents: cadence_weak',
          }),
          {
            headers: { 'content-type': 'application/json' },
            status: 200,
          },
        )
      }
      return new Response(
        JSON.stringify({
          request: {
            bar_start: 3,
            bar_end: 4,
            lock_voice: 'none',
            rewrite_voice: 'auto',
            max_variants: 6,
            objective_preset: 'strengthen_cadence',
            objective_overrides: { cadence_motion_reward: 2.5 },
          },
          summary: {
            parent_candidate_id: 'strict_0001',
            edited_bars: [3, 4],
            lock_voice: 'none',
            rewrite_voice: 'follower',
            objective_preset: 'strengthen_cadence',
            requested_variants: 6,
            returned_variants: 1,
            changed_notes: 1,
          },
          candidates: [variant],
        }),
        {
          headers: { 'content-type': 'application/json' },
          status: 200,
        },
      )
    })
    vi.stubGlobal('fetch', fetchMock)
    const onVariantsReceived = vi.fn()

    renderPanel({
      runSummary: runSummary(selectedCandidate),
      selectedCandidate,
      onVariantsReceived,
    })

    await userEvent.type(screen.getByLabelText('Feedback'), 'cadence weak')
    await userEvent.click(screen.getByRole('button', { name: 'Translate feedback' }))

    expect(await screen.findByText('Strengthen cadence')).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Run action' }))

    await waitFor(() => expect(onVariantsReceived).toHaveBeenCalledOnce())
    expect(fetchMock).toHaveBeenCalledTimes(2)
    const translateCall = fetchMock.mock.calls[0] as [string, RequestInit]
    const polishCall = fetchMock.mock.calls[1] as [string, RequestInit]
    expect(JSON.parse(translateCall[1].body as string)).toMatchObject({
      text: 'cadence weak',
      candidate_id: 'strict_0001',
    })
    expect(JSON.parse(polishCall[1].body as string)).toMatchObject({
      bar_start: 3,
      bar_end: 4,
      objective_preset: 'strengthen_cadence',
    })
  })
})

function renderPanel({
  runSummary,
  selectedCandidate,
  onVariantsReceived,
}: {
  runSummary: RunSummary
  selectedCandidate: CandidateViz
  onVariantsReceived: (variants: CandidateViz[]) => void
}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <FeedbackPanel
          runSummary={runSummary}
          selectedCandidate={selectedCandidate}
          onVariantsReceived={onVariantsReceived}
        />
      </MantineProvider>
    </QueryClientProvider>,
  )
}

function runSummary(selectedCandidate: CandidateViz): RunSummary {
  return {
    run_id: 'run-1',
    input_name: 'theme.musicxml',
    created_at: '2026-05-18T00:00:00Z',
    config_summary: {},
    artifacts: {},
    candidates: [selectedCandidate],
  }
}

function candidate(candidateId: string): CandidateViz {
  return {
    candidate_id: candidateId,
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
    notes: [],
    violations: [],
    repair_actions: [],
    artifacts: {},
    metadata: {},
  }
}
