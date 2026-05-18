// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz } from '../api/schemas'
import type { ScoreRenderer } from '../music/scoreRenderer'
import { ScoreView } from './ScoreView'

describe('ScoreView', () => {
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

  it('loads candidate MusicXML and renders SVG through the score renderer', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response('<score-partwise />', {
          headers: { 'content-type': 'application/vnd.recordare.musicxml+xml' },
          status: 200,
        })
      }),
    )
    const renderer: ScoreRenderer = {
      renderMusicXml: vi.fn(async () => ({
        svg: '<svg data-testid="rendered-score"><g /></svg>',
        page: 1,
        pageCount: 1,
      })),
    }

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MantineProvider>
          <ScoreView runId="run-1" candidate={candidate()} renderer={renderer} />
        </MantineProvider>
      </QueryClientProvider>,
    )

    expect(await screen.findByTestId('rendered-score')).toBeTruthy()
    expect(renderer.renderMusicXml).toHaveBeenCalledWith('<score-partwise />', {
      page: 1,
      scale: 40,
    })
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
    notes: [],
    violations: [],
    repair_actions: [],
    artifacts: { musicxml: '/api/runs/run-1/candidates/strict_0001/musicxml' },
    metadata: {},
  }
}
