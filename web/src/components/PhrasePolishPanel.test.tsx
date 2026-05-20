// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, RunSummary } from '../api/schemas'
import { PhrasePolishPanel } from './PhrasePolishPanel'

describe('PhrasePolishPanel', () => {
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
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('requests polish variants for the selected candidate and displays them', async () => {
    const selectedCandidate = candidate('strict_0001')
    const variant = {
      ...selectedCandidate,
      candidate_id: 'strict_0001_polish_001',
      rank: 1,
      score: { ...selectedCandidate.score, total: 88 },
      metadata: {
        parent_candidate_id: 'strict_0001',
        edited_bars: [1],
        rewrite_voice: 'follower',
      },
    }
    const fetchMock = vi.fn(async (_path: string, _init?: RequestInit) => {
      return new Response(
        JSON.stringify({
          request: {
            bar_start: 1,
            bar_end: 1,
            lock_voice: 'none',
            rewrite_voice: 'auto',
            max_variants: 6,
            objective_preset: 'general_polish',
            objective_overrides: {},
          },
          summary: {
            parent_candidate_id: 'strict_0001',
            edited_bars: [1],
            lock_voice: 'none',
            rewrite_voice: 'follower',
            objective_preset: 'general_polish',
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
      candidates: [selectedCandidate],
      selectedCandidateId: selectedCandidate.candidate_id,
      selectedCandidate,
      onVariantsReceived,
    })

    await userEvent.click(screen.getByRole('button', { name: 'Polish' }))

    expect(await screen.findByText('strict_0001_polish_001')).toBeTruthy()
    await waitFor(() => expect(onVariantsReceived).toHaveBeenCalledOnce())
    expect(fetchMock).toHaveBeenCalledOnce()
    const calls = fetchMock.mock.calls as Array<[string, RequestInit]>
    expect(calls[0][0]).toBe('/api/runs/run-1/candidates/strict_0001/polish')
    expect(JSON.parse(calls[0][1].body as string)).toMatchObject({
      bar_start: 1,
      bar_end: 1,
      lock_voice: 'none',
      rewrite_voice: 'auto',
      max_variants: 6,
      objective_preset: 'general_polish',
      search_mode: 'local_polish',
    })
  })

  it('requests fixed-upper invention mode with an explicit rewrite voice', async () => {
    const selectedCandidate = candidate('strict_0001')
    const variant = {
      ...selectedCandidate,
      candidate_id: 'strict_0001_polish_001',
      metadata: {
        parent_candidate_id: 'strict_0001',
        search_mode: 'rewrite_selected_voice',
      },
    }
    const fetchMock = vi.fn(async (_path: string, _init?: RequestInit) => {
      return new Response(
        JSON.stringify({
          request: {
            bar_start: 1,
            bar_end: 1,
            lock_voice: 'leader',
            rewrite_voice: 'follower',
            max_variants: 6,
            objective_preset: 'smooth_bass',
            objective_overrides: {},
            search_mode: 'rewrite_selected_voice',
            allow_rhythm_change: false,
          },
          summary: {
            parent_candidate_id: 'strict_0001',
            edited_bars: [1],
            lock_voice: 'leader',
            rewrite_voice: 'follower',
            objective_preset: 'smooth_bass',
            search_mode: 'rewrite_selected_voice',
            allow_rhythm_change: false,
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

    const view = renderPanel({
      runSummary: runSummary(selectedCandidate),
      candidates: [selectedCandidate],
      selectedCandidateId: selectedCandidate.candidate_id,
      selectedCandidate,
      onVariantsReceived: vi.fn(),
    })

    await userEvent.click(within(view.container).getByLabelText('Mode'))
    fireEvent.click(screen.getByText('Rewrite lower under fixed upper'))
    await userEvent.click(screen.getByRole('button', { name: 'Polish' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
    const calls = fetchMock.mock.calls as Array<[string, RequestInit]>
    expect(JSON.parse(calls[0][1].body as string)).toMatchObject({
      lock_voice: 'leader',
      rewrite_voice: 'follower',
      objective_preset: 'smooth_bass',
      search_mode: 'rewrite_selected_voice',
      allow_rhythm_change: false,
    })
  })

  it('requests fixed-lower invention mode with an explicit rewrite voice', async () => {
    const selectedCandidate = candidate('strict_0001')
    const fetchMock = vi.fn(async (_path: string, _init?: RequestInit) => {
      return new Response(
        JSON.stringify({
          request: {
            bar_start: 1,
            bar_end: 1,
            lock_voice: 'follower',
            rewrite_voice: 'leader',
            max_variants: 6,
            objective_preset: 'general_polish',
            objective_overrides: {},
            search_mode: 'rewrite_selected_voice',
            allow_rhythm_change: false,
          },
          summary: {
            parent_candidate_id: 'strict_0001',
            edited_bars: [1],
            lock_voice: 'follower',
            rewrite_voice: 'leader',
            objective_preset: 'general_polish',
            search_mode: 'rewrite_selected_voice',
            allow_rhythm_change: false,
            requested_variants: 6,
            returned_variants: 1,
            changed_notes: 1,
          },
          candidates: [
            {
              ...selectedCandidate,
              candidate_id: 'strict_0001_polish_001',
              metadata: {
                parent_candidate_id: 'strict_0001',
                search_mode: 'rewrite_selected_voice',
              },
            },
          ],
        }),
        {
          headers: { 'content-type': 'application/json' },
          status: 200,
        },
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const view = renderPanel({
      runSummary: runSummary(selectedCandidate),
      candidates: [selectedCandidate],
      selectedCandidateId: selectedCandidate.candidate_id,
      selectedCandidate,
      onVariantsReceived: vi.fn(),
    })

    await userEvent.click(within(view.container).getByLabelText('Mode'))
    fireEvent.click(screen.getByText('Rewrite upper above fixed lower'))
    await userEvent.click(screen.getByRole('button', { name: 'Polish' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
    const calls = fetchMock.mock.calls as Array<[string, RequestInit]>
    expect(JSON.parse(calls[0][1].body as string)).toMatchObject({
      lock_voice: 'follower',
      rewrite_voice: 'leader',
      objective_preset: 'general_polish',
      search_mode: 'rewrite_selected_voice',
      allow_rhythm_change: false,
    })
  })
})

function renderPanel({
  runSummary,
  candidates,
  selectedCandidateId,
  selectedCandidate,
  onVariantsReceived,
}: {
  runSummary: RunSummary
  candidates: CandidateViz[]
  selectedCandidateId: string
  selectedCandidate: CandidateViz
  onVariantsReceived: (variants: CandidateViz[]) => void
}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <PhrasePolishPanel
          runSummary={runSummary}
          candidates={candidates}
          selectedCandidateId={selectedCandidateId}
          selectedCandidate={selectedCandidate}
          onSelectCandidate={vi.fn()}
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
