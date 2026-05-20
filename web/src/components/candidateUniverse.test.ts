import { describe, expect, it } from 'vitest'
import type { CandidateViz, Experiment } from '../api/schemas'
import {
  candidateSource,
  mergeCandidateUniverse,
  parentCandidateId,
  sourceExperimentId,
} from './candidateUniverse'

describe('mergeCandidateUniverse', () => {
  it('merges reloaded experiment variants into the selectable candidate pool', () => {
    const base = candidateFixture('strict_0001')
    const variant = candidateFixture('strict_0001_polish_001')
    const experiment: Experiment = {
      experiment_id: 'experiment-0001',
      source_candidate_id: base.candidate_id,
      source_request: { bar_start: 1, bar_end: 1 },
      created_at: '2026-05-20T00:00:00Z',
      notes: '',
      variants: [{ candidate_id: variant.candidate_id, status: 'undecided', candidate: variant }],
    }

    const merged = mergeCandidateUniverse([base], [experiment])

    expect(merged.map((candidate) => candidate.candidate_id)).toEqual([
      'strict_0001',
      'strict_0001_polish_001',
    ])
    expect(candidateSource(merged[0])).toBe('run')
    expect(candidateSource(merged[1])).toBe('experiment')
    expect(sourceExperimentId(merged[1])).toBe('experiment-0001')
    expect(parentCandidateId(merged[1])).toBe('strict_0001')
  })
})

function candidateFixture(candidateId: string): CandidateViz {
  return {
    candidate_id: candidateId,
    rank: candidateId.endsWith('0001') ? 1 : null,
    title: candidateId,
    transform: {
      engine: 'strict',
      strict_canon: !candidateId.includes('polish'),
      label: 'canon',
      delay_q: { text: '1', value: 1 },
      interval: -12,
      transform_mode: 'transposition',
      inversion_axis: null,
      rhythm_scale: '1',
    },
    score: { total: 88, by_category: {}, by_rule: {}, bonuses: {} },
    musicality: null,
    analysis: null,
    notes: [],
    violations: [],
    repair_actions: [],
    artifacts: {},
    metadata: {},
  }
}
