import { describe, expect, it } from 'vitest'
import { RunSummarySchema } from './schemas'

describe('RunSummarySchema', () => {
  it('validates the visualization payload contract', () => {
    const payload = {
      run_id: 'run-1',
      input_name: 'scale.musicxml',
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
            label: 'strict canon',
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

    expect(RunSummarySchema.parse(payload).run_id).toBe('run-1')
  })
})
