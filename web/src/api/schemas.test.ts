import { describe, expect, it } from 'vitest'
import { FeedbackTranslationSchema, PolishResultSchema, RunSummarySchema } from './schemas'

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
          musicality: {
            total: 84,
            metrics: [
              {
                key: 'contour_variety',
                label: 'Contour variety',
                raw_value: 0.75,
                normalized_value: 0.75,
                weight: 0.15,
                higher_is_better: true,
              },
            ],
            raw_values: { contour_variety: 0.75 },
            normalized_values: { contour_variety: 0.75 },
            weights: { contour_variety: 0.15 },
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

describe('PolishResultSchema', () => {
  it('validates lineaged polish variants', () => {
    const payload = {
      request: {
        bar_start: 1,
        bar_end: 2,
        lock_voice: 'leader',
        rewrite_voice: 'follower',
        max_variants: 2,
        objective_preset: 'reduce_repetition',
        objective_overrides: { repeated_note_penalty: 1.5 },
      },
      summary: {
        parent_candidate_id: 'strict_0001',
        edited_bars: [1, 2],
        lock_voice: 'leader',
        rewrite_voice: 'follower',
        objective_preset: 'reduce_repetition',
        requested_variants: 2,
        returned_variants: 1,
        changed_notes: 1,
      },
      candidates: [
        {
          candidate_id: 'strict_0001_polish_001',
          rank: 1,
          title: 'Candidate 1',
          transform: {
            engine: 'strict',
            strict_canon: false,
            label: 'relaxed canon',
            delay_q: { text: '1', value: 1 },
            interval: 7,
            transform_mode: 'transposition',
            inversion_axis: null,
            rhythm_scale: '1',
          },
          score: {
            total: 88,
            by_category: {},
            by_rule: {},
            bonuses: {},
          },
          notes: [],
          violations: [],
          repair_actions: [],
          artifacts: {},
          metadata: {
            parent_candidate_id: 'strict_0001',
            edited_bars: [1, 2],
            rewrite_voice: 'follower',
          },
        },
      ],
      experiment: {
        experiment_id: 'experiment-0001',
        source_candidate_id: 'strict_0001',
        source_request: { bar_start: 1, bar_end: 2 },
        created_at: '2026-05-20T00:00:00Z',
        notes: '',
        variants: [
          {
            candidate_id: 'strict_0001_polish_001',
            status: 'undecided',
            candidate: {
              candidate_id: 'strict_0001_polish_001',
              rank: 1,
              title: 'Candidate 1',
              transform: {
                engine: 'strict',
                strict_canon: false,
                label: 'relaxed canon',
                delay_q: { text: '1', value: 1 },
                interval: 7,
                transform_mode: 'transposition',
                inversion_axis: null,
                rhythm_scale: '1',
              },
              score: {
                total: 88,
                by_category: {},
                by_rule: {},
                bonuses: {},
              },
              notes: [],
              violations: [],
              repair_actions: [],
              artifacts: {},
              metadata: {},
            },
          },
        ],
      },
    }

    const result = PolishResultSchema.parse(payload)
    expect(result.summary.returned_variants).toBe(1)
    expect(result.experiment?.experiment_id).toBe('experiment-0001')
  })
})

describe('FeedbackTranslationSchema', () => {
  it('validates deterministic feedback actions', () => {
    const payload = {
      input_text: 'bass too static',
      candidate_id: 'strict_0001',
      intents: ['bass_too_static'],
      target: { bar_start: 1, bar_end: 2 },
      actions: [
        {
          action_id: 'feedback-action-01',
          label: 'Rewrite lower support',
          reason: 'Mapped feedback intent bass_too_static.',
          request: {
            bar_start: 1,
            bar_end: 2,
            lock_voice: 'leader',
            rewrite_voice: 'follower',
            max_variants: 6,
            objective_preset: 'smooth_bass',
            objective_overrides: { bass_smoothness_penalty: 2.5 },
          },
        },
      ],
      explanation: 'Recognized feedback intents: bass_too_static',
    }

    const translation = FeedbackTranslationSchema.parse(payload)
    expect(translation.actions[0].request.rewrite_voice).toBe('follower')
  })
})
