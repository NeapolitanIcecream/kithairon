import type { CandidateViz, Experiment } from '../api/schemas'

export function mergeCandidateUniverse(
  runCandidates: CandidateViz[],
  experiments: Experiment[],
): CandidateViz[] {
  const merged = new Map<string, CandidateViz>()
  for (const candidate of runCandidates) {
    merged.set(
      candidate.candidate_id,
      withProvenance(candidate, 'run', null, null),
    )
  }
  for (const experiment of experiments) {
    for (const variant of experiment.variants) {
      if (merged.has(variant.candidate.candidate_id)) {
        console.warn(
          'Duplicate candidate id ignored while merging candidate universe.',
          {
            candidateId: variant.candidate.candidate_id,
            sourceExperimentId: experiment.experiment_id,
          },
        )
        continue
      }
      const parentCandidateId =
        stringOrNull(variant.candidate.metadata.parent_candidate_id) ??
        experiment.source_candidate_id
      merged.set(
        variant.candidate.candidate_id,
        withProvenance(
          variant.candidate,
          'experiment',
          experiment.experiment_id,
          parentCandidateId,
        ),
      )
    }
  }
  return Array.from(merged.values())
}

export function candidateSource(candidate: CandidateViz): 'run' | 'experiment' {
  return candidate.metadata.source_kind === 'experiment' ? 'experiment' : 'run'
}

export function sourceExperimentId(candidate: CandidateViz): string | null {
  return stringOrNull(candidate.metadata.source_experiment_id)
}

export function parentCandidateId(candidate: CandidateViz): string | null {
  return stringOrNull(candidate.metadata.parent_candidate_id)
}

function withProvenance(
  candidate: CandidateViz,
  sourceKind: 'run' | 'experiment',
  experimentId: string | null,
  parentId: string | null,
): CandidateViz {
  return {
    ...candidate,
    metadata: {
      ...candidate.metadata,
      source_kind: sourceKind,
      source_experiment_id: experimentId,
      parent_candidate_id: parentId,
    },
  }
}

function stringOrNull(value: unknown): string | null {
  return typeof value === 'string' ? value : null
}
