import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
} from '@mantine/core'
import { ApiClientError } from '../api/client'
import { polishCandidate } from '../api/runs'
import type {
  CandidateViz,
  Experiment,
  LockVoice,
  ObjectivePreset,
  PolishResult,
  RewriteVoice,
  RunSummary,
  SearchMode,
} from '../api/schemas'

type PhrasePolishPanelProps = {
  runSummary: RunSummary | null
  candidates: CandidateViz[]
  selectedCandidateId: string | null
  selectedCandidate: CandidateViz | null
  onSelectCandidate: (candidateId: string) => void
  onVariantsReceived: (variants: CandidateViz[], experiment: Experiment | null | undefined) => void
}

type LastResultState = {
  candidateId: string | null
  result: PolishResult
}

const lockVoiceOptions: Array<{ value: LockVoice; label: string }> = [
  { value: 'none', label: 'None' },
  { value: 'leader', label: 'Leader' },
  { value: 'follower', label: 'Follower' },
]

const rewriteVoiceOptions: Array<{ value: RewriteVoice; label: string }> = [
  { value: 'auto', label: 'Auto' },
  { value: 'leader', label: 'Leader' },
  { value: 'follower', label: 'Follower' },
]

const objectivePresetOptions: Array<{ value: ObjectivePreset; label: string }> = [
  { value: 'general_polish', label: 'General polish' },
  { value: 'reduce_repetition', label: 'Reduce repetition' },
  { value: 'smooth_bass', label: 'Smooth bass' },
  { value: 'strengthen_cadence', label: 'Strengthen cadence' },
]

type PolishMode = 'local_polish' | 'rewrite_follower' | 'rewrite_leader'

const polishModeOptions: Array<{ value: PolishMode; label: string }> = [
  { value: 'local_polish', label: 'Local polish' },
  { value: 'rewrite_follower', label: 'Rewrite lower under fixed upper' },
  { value: 'rewrite_leader', label: 'Rewrite upper above fixed lower' },
]

export function PhrasePolishPanel({
  runSummary,
  candidates,
  selectedCandidateId,
  selectedCandidate,
  onSelectCandidate,
  onVariantsReceived,
}: PhrasePolishPanelProps) {
  const [barStart, setBarStart] = useState(1)
  const [barEnd, setBarEnd] = useState(1)
  const [lockVoice, setLockVoice] = useState<LockVoice>('none')
  const [rewriteVoice, setRewriteVoice] = useState<RewriteVoice>('auto')
  const [objectivePreset, setObjectivePreset] = useState<ObjectivePreset>('general_polish')
  const [polishMode, setPolishMode] = useState<PolishMode>('local_polish')
  const [maxVariants, setMaxVariants] = useState(6)
  const [lastResultState, setLastResultState] = useState<LastResultState | null>(null)
  const lastResult =
    lastResultState?.candidateId === selectedCandidateId ? lastResultState.result : null

  const candidateOptions = useMemo(
    () =>
      candidates.map((candidate) => ({
        value: candidate.candidate_id,
        label: `${candidate.rank ?? '-'} ${candidate.candidate_id}`,
      })),
    [candidates],
  )

  const polishMutation = useMutation({
    mutationFn: () => {
      if (runSummary === null || selectedCandidate === null) {
        throw new Error('Select a run candidate before polishing.')
      }
      const plan = voicePlanForMode(polishMode, lockVoice, rewriteVoice)
      return polishCandidate(runSummary.run_id, selectedCandidate.candidate_id, {
        barStart,
        barEnd,
        lockVoice: plan.lockVoice,
        rewriteVoice: plan.rewriteVoice,
        maxVariants,
        objectivePreset,
        searchMode: plan.searchMode,
      })
    },
    onSuccess: (result) => {
      setLastResultState({
        candidateId: result.summary.parent_candidate_id,
        result,
      })
      onVariantsReceived(result.candidates, result.experiment)
    },
  })

  const errorMessage = polishMutation.error
    ? readableErrorMessage(polishMutation.error)
    : null
  const disabled = runSummary === null || selectedCandidate === null

  return (
    <Stack gap="sm">
      <Select
        label="Candidate"
        data={candidateOptions}
        value={selectedCandidateId}
        disabled={candidates.length === 0}
        searchable
        onChange={(value) => {
          if (value !== null) {
            onSelectCandidate(value)
          }
        }}
      />
      <Group grow align="flex-end">
        <NumberInput
          label="Start bar"
          min={1}
          value={barStart}
          onChange={(value) => setBarStart(toPositiveInteger(value, 1))}
        />
        <NumberInput
          label="End bar"
          min={1}
          value={barEnd}
          onChange={(value) => setBarEnd(toPositiveInteger(value, barStart))}
        />
      </Group>
      <Select
        label="Mode"
        data={polishModeOptions}
        value={polishMode}
        allowDeselect={false}
        onChange={(value) => {
          const nextMode = (value ?? 'local_polish') as PolishMode
          setPolishMode(nextMode)
          if (nextMode === 'rewrite_follower') {
            setObjectivePreset('smooth_bass')
          } else if (nextMode === 'rewrite_leader') {
            setObjectivePreset('general_polish')
          }
        }}
      />
      {polishMode === 'local_polish' ? (
        <Group grow align="flex-end">
          <Select
            label="Lock"
            data={lockVoiceOptions}
            value={lockVoice}
            allowDeselect={false}
            onChange={(value) => setLockVoice((value ?? 'none') as LockVoice)}
          />
          <Select
            label="Rewrite"
            data={rewriteVoiceOptions}
            value={rewriteVoice}
            allowDeselect={false}
            onChange={(value) => setRewriteVoice((value ?? 'auto') as RewriteVoice)}
          />
        </Group>
      ) : null}
      <Select
        label="Preset"
        data={objectivePresetOptions}
        value={objectivePreset}
        allowDeselect={false}
        onChange={(value) => setObjectivePreset((value ?? 'general_polish') as ObjectivePreset)}
      />
      <NumberInput
        label="Variants"
        min={1}
        max={50}
        value={maxVariants}
        onChange={(value) => setMaxVariants(toPositiveInteger(value, 6))}
      />
      <Button
        fullWidth
        disabled={disabled}
        loading={polishMutation.isPending}
        onClick={() => polishMutation.mutate()}
      >
        Polish
      </Button>
      {errorMessage !== null ? (
        <Alert color="red" variant="light" title="Polish failed">
          {errorMessage}
        </Alert>
      ) : null}
      {lastResult !== null ? <PolishVariantSummary result={lastResult} /> : null}
    </Stack>
  )
}

function PolishVariantSummary({ result }: { result: PolishResult }) {
  if (result.candidates.length === 0) {
    return (
      <Alert color="gray" variant="light" title="No variants">
        No variants returned.
      </Alert>
    )
  }

  return (
    <Stack gap="xs">
      <Group gap="xs">
        <Badge variant="light" color="teal">
          {result.summary.returned_variants}
        </Badge>
        <Text size="sm" c="dimmed">
          {result.summary.rewrite_voice}
        </Text>
      </Group>
      <Table className="polish-result-table" withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Variant</Table.Th>
            <Table.Th>Score</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {result.candidates.map((candidate) => (
            <Table.Tr key={candidate.candidate_id}>
              <Table.Td>
                <Text size="sm" lineClamp={1}>
                  {candidate.candidate_id}
                </Text>
              </Table.Td>
              <Table.Td>{candidate.score.total.toFixed(1)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  )
}

function toPositiveInteger(value: string | number, fallback: number): number {
  const parsed = typeof value === 'number' ? value : Number.parseInt(value, 10)
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback
  }
  return Math.floor(parsed)
}

function voicePlanForMode(
  polishMode: PolishMode,
  lockVoice: LockVoice,
  rewriteVoice: RewriteVoice,
): {
  lockVoice: LockVoice
  rewriteVoice: RewriteVoice
  searchMode: SearchMode
} {
  if (polishMode === 'rewrite_follower') {
    return { lockVoice: 'leader', rewriteVoice: 'follower', searchMode: 'rewrite_selected_voice' }
  }
  if (polishMode === 'rewrite_leader') {
    return { lockVoice: 'follower', rewriteVoice: 'leader', searchMode: 'rewrite_selected_voice' }
  }
  return { lockVoice, rewriteVoice, searchMode: 'local_polish' }
}

function readableErrorMessage(error: Error): string {
  if (error instanceof ApiClientError) {
    return error.message
  }
  return error.message || 'The candidate could not be polished.'
}
