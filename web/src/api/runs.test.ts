import { afterEach, describe, expect, it, vi } from 'vitest'
import { polishCandidate, uploadRun } from './runs'

const runSummaryPayload = {
  run_id: 'run-1',
  input_name: 'theme.musicxml',
  created_at: '2026-05-18T00:00:00Z',
  config_summary: {},
  artifacts: { report: '/api/runs/run-1/artifact/report' },
  candidates: [
    {
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
    },
  ],
}

describe('uploadRun', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts an upload form and validates the run summary response', async () => {
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
      void path
      void init
      return new Response(JSON.stringify(runSummaryPayload), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const file = new File(['<score />'], 'theme.musicxml', {
      type: 'application/vnd.recordare.musicxml+xml',
    })
    const summary = await uploadRun({
      file,
      engine: 'strict',
      scoreProfile: 'renaissance-lite',
      topK: 4,
      chordPolicy: 'top_note',
      partPolicy: 'explicit_index',
      partIndex: 2,
    })

    expect(summary.run_id).toBe('run-1')
    expect(fetchMock).toHaveBeenCalledOnce()
    const calls = fetchMock.mock.calls as Array<[string, RequestInit]>
    const init = calls[0][1]
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    const form = init.body as FormData
    expect(form.get('file')).toBe(file)
    expect(form.get('engine')).toBe('strict')
    expect(form.get('score_profile')).toBe('renaissance-lite')
    expect(form.get('top_k')).toBe('4')
    expect(form.get('chord_policy')).toBe('top_note')
    expect(form.get('part_policy')).toBe('explicit_index')
    expect(form.get('part_index')).toBe('2')
  })
})

describe('polishCandidate', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts a polish request and validates returned variants', async () => {
    const polishPayload = {
      request: {
        bar_start: 3,
        bar_end: 4,
        lock_voice: 'leader',
        rewrite_voice: 'follower',
        max_variants: 2,
        objective_preset: 'reduce_repetition',
        objective_overrides: { repeated_note_penalty: 1.5 },
      },
      summary: {
        parent_candidate_id: 'strict_0001',
        edited_bars: [3, 4],
        lock_voice: 'leader',
        rewrite_voice: 'follower',
        objective_preset: 'reduce_repetition',
        requested_variants: 2,
        returned_variants: 1,
        changed_notes: 1,
      },
      candidates: [
        {
          ...runSummaryPayload.candidates[0],
          candidate_id: 'strict_0001_polish_001',
          metadata: {
            parent_candidate_id: 'strict_0001',
            edited_bars: [3, 4],
            rewrite_voice: 'follower',
          },
        },
      ],
    }
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
      void path
      void init
      return new Response(JSON.stringify(polishPayload), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await polishCandidate('run-1', 'strict_0001', {
      barStart: 3,
      barEnd: 4,
      lockVoice: 'leader',
      rewriteVoice: 'follower',
      maxVariants: 2,
      objectivePreset: 'reduce_repetition',
      objectiveOverrides: { repeated_note_penalty: 1.5 },
    })

    expect(result.summary.returned_variants).toBe(1)
    expect(fetchMock).toHaveBeenCalledOnce()
    const calls = fetchMock.mock.calls as Array<[string, RequestInit]>
    expect(calls[0][0]).toBe('/api/runs/run-1/candidates/strict_0001/polish')
    const init = calls[0][1]
    expect(init.method).toBe('POST')
    expect(init.headers).toEqual({ 'content-type': 'application/json' })
    expect(JSON.parse(init.body as string)).toEqual({
      bar_start: 3,
      bar_end: 4,
      lock_voice: 'leader',
      rewrite_voice: 'follower',
      max_variants: 2,
      objective_preset: 'reduce_repetition',
      objective_overrides: { repeated_note_penalty: 1.5 },
    })
  })
})
