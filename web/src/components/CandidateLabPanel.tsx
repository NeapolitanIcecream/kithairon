import { useState } from 'react'
import { Alert, Button, Group, Stack, Table, Text, Textarea } from '@mantine/core'
import { ApiClientError } from '../api/client'
import { patchExperiment } from '../api/runs'
import type { CandidateViz, Experiment, ExperimentVariantStatus, RunSummary } from '../api/schemas'

type CandidateLabPanelProps = {
  runSummary: RunSummary | null
  experiments: Experiment[]
  onExperimentsChange: (experiments: Experiment[]) => void
  onSelectCandidate: (candidateId: string) => void
}

export function CandidateLabPanel({
  runSummary,
  experiments,
  onExperimentsChange,
  onSelectCandidate,
}: CandidateLabPanelProps) {
  const [draftNotes, setDraftNotes] = useState<Record<string, string>>({})
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  async function applyPatch(
    experiment: Experiment,
    patch: { notes?: string; variantStatus?: Record<string, ExperimentVariantStatus> },
  ) {
    if (runSummary === null) {
      return
    }
    try {
      setErrorMessage(null)
      const updated = await patchExperiment(runSummary.run_id, experiment.experiment_id, patch)
      onExperimentsChange(
        experiments.map((item) =>
          item.experiment_id === updated.experiment_id ? updated : item,
        ),
      )
    } catch (error) {
      setErrorMessage(readableErrorMessage(error))
    }
  }

  if (runSummary === null) {
    return (
      <Alert color="gray" variant="light" title="No run">
        No run loaded.
      </Alert>
    )
  }

  if (experiments.length === 0) {
    return (
      <Alert color="gray" variant="light" title="No experiments">
        No polish experiments saved for this run.
      </Alert>
    )
  }

  return (
    <Stack gap="md">
      {errorMessage !== null ? (
        <Alert color="red" variant="light" title="Experiment update failed">
          {errorMessage}
        </Alert>
      ) : null}
      {experiments.map((experiment) => (
        <Stack key={experiment.experiment_id} className="candidate-lab-experiment" gap="xs">
          <Group justify="space-between">
            <Text fw={700}>{experiment.experiment_id}</Text>
            <Text size="xs" c="dimmed">
              {experiment.created_at}
            </Text>
          </Group>
          <Text size="sm" c="dimmed">
            {experiment.source_candidate_id} / {requestLabel(experiment.source_request)}
          </Text>
          <VariantTable
            variants={experiment.variants.map((variant) => variant.candidate)}
            statuses={Object.fromEntries(
              experiment.variants.map((variant) => [variant.candidate_id, variant.status]),
            )}
            onSelectCandidate={onSelectCandidate}
            onStatusChange={(candidateId, status) =>
              void applyPatch(experiment, { variantStatus: { [candidateId]: status } })
            }
          />
          <Textarea
            label="Notes"
            value={draftNotes[experiment.experiment_id] ?? experiment.notes}
            minRows={2}
            onChange={(event) =>
              setDraftNotes((current) => ({
                ...current,
                [experiment.experiment_id]: event.currentTarget.value,
              }))
            }
          />
          <Button
            variant="light"
            onClick={() =>
              void applyPatch(experiment, {
                notes: draftNotes[experiment.experiment_id] ?? experiment.notes,
              })
            }
          >
            Save notes
          </Button>
        </Stack>
      ))}
    </Stack>
  )
}

function VariantTable({
  variants,
  statuses,
  onSelectCandidate,
  onStatusChange,
}: {
  variants: CandidateViz[]
  statuses: Record<string, ExperimentVariantStatus>
  onSelectCandidate: (candidateId: string) => void
  onStatusChange: (candidateId: string, status: ExperimentVariantStatus) => void
}) {
  return (
    <Table className="candidate-lab-table" withTableBorder>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Variant</Table.Th>
          <Table.Th>Score</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Actions</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {variants.map((candidate) => (
          <Table.Tr key={candidate.candidate_id}>
            <Table.Td>
              <Button
                variant="subtle"
                size="compact-sm"
                onClick={() => onSelectCandidate(candidate.candidate_id)}
              >
                {candidate.candidate_id}
              </Button>
            </Table.Td>
            <Table.Td>{candidate.score.total.toFixed(1)}</Table.Td>
            <Table.Td>{statuses[candidate.candidate_id] ?? 'undecided'}</Table.Td>
            <Table.Td>
              <Group gap="xs" wrap="nowrap">
                <Button
                  variant="light"
                  size="compact-sm"
                  onClick={() => onStatusChange(candidate.candidate_id, 'kept')}
                >
                  Keep
                </Button>
                <Button
                  variant="light"
                  color="gray"
                  size="compact-sm"
                  onClick={() => onStatusChange(candidate.candidate_id, 'rejected')}
                >
                  Reject
                </Button>
              </Group>
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  )
}

function requestLabel(sourceRequest: Record<string, unknown>): string {
  const preset = sourceRequest.objective_preset
  const start = sourceRequest.bar_start
  const end = sourceRequest.bar_end
  const mode = sourceRequest.search_mode
  const modeLabel = mode === 'rewrite_selected_voice' ? 'fixed voice' : 'polish'
  return `${modeLabel} ${typeof preset === 'string' ? preset : 'polish'} bars ${start ?? '?'}-${end ?? '?'}`
}

function readableErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'The experiment could not be updated.'
}
