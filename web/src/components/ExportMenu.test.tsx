// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, RunSummary } from '../api/schemas'
import { ExportMenu } from './ExportMenu'

describe('ExportMenu', () => {
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

  it('renders score exports and exposes download links after render succeeds', async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          candidate_id: 'strict_0001',
          artifacts: { pdf: 'renders/strict_0001/strict_0001.pdf' },
        }),
        {
          headers: { 'content-type': 'application/json' },
          status: 200,
        },
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MantineProvider>
          <ExportMenu runSummary={runSummary()} candidate={candidate()} />
        </MantineProvider>
      </QueryClientProvider>,
    )

    expect(screen.getByText('MIDI').closest('a')?.getAttribute('href')).toContain(
      '/api/runs/run-1/candidates/strict_0001/midi',
    )

    await userEvent.click(screen.getByText('Render PDF'))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/runs/run-1/candidates/strict_0001/render',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(await screen.findByText('Download PDF')).toBeTruthy()
  })
})

function runSummary(): RunSummary {
  return {
    run_id: 'run-1',
    input_name: 'theme.musicxml',
    created_at: '2026-05-18T00:00:00Z',
    config_summary: {},
    artifacts: {},
    candidates: [],
  }
}

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
    artifacts: {},
    metadata: {},
  }
}
