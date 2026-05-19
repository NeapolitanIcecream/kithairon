import { afterEach, describe, expect, it, vi } from 'vitest'
import { uploadRun } from './runs'

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
