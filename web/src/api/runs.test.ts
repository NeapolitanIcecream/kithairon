import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  listExperiments,
  patchExperiment,
  polishCandidate,
  translateFeedback,
  uploadRun,
} from './runs'

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
      search_mode: 'local_polish',
      allow_rhythm_change: false,
    })
  })
})

describe('experiment API', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists and patches run-local experiments', async () => {
    const experiment = {
      experiment_id: 'experiment-0001',
      source_candidate_id: 'strict_0001',
      source_request: { bar_start: 1, bar_end: 1 },
      created_at: '2026-05-20T00:00:00Z',
      notes: 'keeper',
      variants: [
        {
          candidate_id: 'strict_0001_polish_001',
          status: 'kept',
          candidate: runSummaryPayload.candidates[0],
        },
      ],
    }
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
      void init
      return new Response(JSON.stringify(path.endsWith('/experiments') ? [experiment] : experiment), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const listed = await listExperiments('run-1')
    const patched = await patchExperiment('run-1', 'experiment-0001', {
      notes: 'keeper',
      variantStatus: { strict_0001_polish_001: 'kept' },
    })

    expect(listed[0].experiment_id).toBe('experiment-0001')
    expect(patched.variants[0].status).toBe('kept')
    const patchCall = fetchMock.mock.calls[1] as [string, RequestInit]
    expect(patchCall[0]).toBe('/api/runs/run-1/experiments/experiment-0001')
    expect(JSON.parse(patchCall[1].body as string)).toEqual({
      notes: 'keeper',
      variant_status: { strict_0001_polish_001: 'kept' },
    })
  })
})

describe('translateFeedback', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts feedback text and validates suggested polish actions', async () => {
    const fetchMock = vi.fn(async (...args: [string, RequestInit?]) => {
      void args
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
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await translateFeedback('run-1', {
      text: 'cadence weak',
      candidateId: 'strict_0001',
      barStart: 3,
      barEnd: 4,
    })

    expect(result.actions[0].request.objective_preset).toBe('strengthen_cadence')
    const call = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(call[0]).toBe('/api/runs/run-1/feedback/translate')
    expect(JSON.parse(call[1].body as string)).toEqual({
      text: 'cadence weak',
      candidate_id: 'strict_0001',
      target: { bar_start: 3, bar_end: 4 },
    })
  })
})
