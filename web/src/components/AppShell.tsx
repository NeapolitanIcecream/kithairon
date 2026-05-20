import { useMemo, useState } from 'react'
import {
  Alert,
  AppShell,
  Badge,
  Box,
  Divider,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import type { CandidateViz, RepairAction, RunSummary, ViolationViz } from '../api/schemas'
import type { Experiment } from '../api/schemas'
import { listExperiments } from '../api/runs'
import { CandidateLabPanel } from './CandidateLabPanel'
import { CandidateTable } from './CandidateTable'
import { ExportMenu } from './ExportMenu'
import { MusicalityBreakdown } from './MusicalityBreakdown'
import { PianoRollView } from './PianoRollView'
import { PlaybackControls } from './PlaybackControls'
import { PhrasePolishPanel } from './PhrasePolishPanel'
import { ScoreBreakdown } from './ScoreBreakdown'
import { ScoreView } from './ScoreView'
import { StrictRelaxedDiff } from './StrictRelaxedDiff'
import { UploadPanel } from './UploadPanel'
import { ViolationInspector } from './ViolationInspector'

export function KithaironAppShell() {
  const [runSummary, setRunSummary] = useState<RunSummary | null>(null)
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [selectedViolationId, setSelectedViolationId] = useState<string | null>(null)
  const [selectedRepairActionId, setSelectedRepairActionId] = useState<string | null>(null)
  const [violationCategoryFilter, setViolationCategoryFilter] = useState('all')
  const [activePlaybackEventIds, setActivePlaybackEventIds] = useState<string[]>([])
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const candidates = useMemo(() => runSummary?.candidates ?? [], [runSummary])
  const selectedCandidate = useMemo(
    () =>
      candidates.find((candidate) => candidate.candidate_id === selectedCandidateId) ?? null,
    [candidates, selectedCandidateId],
  )
  const selectedViolation = useMemo(
    () =>
      selectedCandidate?.violations.find(
        (violation) => violation.violation_id === selectedViolationId,
      ) ?? null,
    [selectedCandidate, selectedViolationId],
  )
  const selectedRepairAction = useMemo(
    () =>
      selectedCandidate?.repair_actions.find(
        (action) => action.action_id === selectedRepairActionId,
      ) ?? null,
    [selectedCandidate, selectedRepairActionId],
  )
  const highlightedEventIds = uniqueEventIds([
    ...(selectedViolation?.event_ids ?? (selectedEventId === null ? [] : [selectedEventId])),
    ...repairActionEventIds(selectedRepairAction),
    ...activePlaybackEventIds,
  ])
  const modifiedEventIds = uniqueEventIds(
    selectedCandidate?.repair_actions.flatMap(repairActionEventIds) ?? [],
  )

  function handleRunLoaded(nextRunSummary: RunSummary) {
    setRunSummary(nextRunSummary)
    setSelectedCandidateId(nextRunSummary.candidates[0]?.candidate_id ?? null)
    setSelectedEventId(null)
    setSelectedViolationId(null)
    setSelectedRepairActionId(null)
    setViolationCategoryFilter('all')
    setActivePlaybackEventIds([])
    setExperiments([])
    void listExperiments(nextRunSummary.run_id).then(setExperiments).catch(() => setExperiments([]))
  }

  function handlePolishVariants(
    variants: CandidateViz[],
    experiment: Experiment | null | undefined,
  ) {
    if (variants.length === 0) {
      return
    }
    setRunSummary((current) => {
      if (current === null) {
        return current
      }
      const variantIds = new Set(variants.map((variant) => variant.candidate_id))
      return {
        ...current,
        candidates: [
          ...current.candidates.filter(
            (candidate) => !variantIds.has(candidate.candidate_id),
          ),
          ...variants,
        ],
      }
    })
    setSelectedCandidateId(variants[0].candidate_id)
    setSelectedEventId(null)
    setSelectedViolationId(null)
    setSelectedRepairActionId(null)
    setViolationCategoryFilter('all')
    setActivePlaybackEventIds([])
    if (experiment !== null && experiment !== undefined) {
      setExperiments((current) => [
        ...current.filter((item) => item.experiment_id !== experiment.experiment_id),
        experiment,
      ])
    }
  }

  function handleCandidateSelect(candidateId: string) {
    setSelectedCandidateId(candidateId)
    setSelectedEventId(null)
    setSelectedViolationId(null)
    setSelectedRepairActionId(null)
    setViolationCategoryFilter('all')
    setActivePlaybackEventIds([])
  }

  function handleEventSelect(eventId: string) {
    setSelectedEventId(eventId)
    setSelectedViolationId(null)
    setSelectedRepairActionId(null)
  }

  function handleViolationSelect(violation: ViolationViz) {
    setSelectedViolationId(violation.violation_id)
    setSelectedRepairActionId(null)
    setSelectedEventId(violation.event_ids[0] ?? null)
  }

  function handleRepairActionSelect(action: RepairAction) {
    setSelectedRepairActionId(action.action_id)
    setSelectedViolationId(null)
    setSelectedEventId(action.new_event_id ?? action.original_event_id)
  }

  return (
    <AppShell
      className="app-root"
      header={{ height: 58 }}
      navbar={{ width: 300, breakpoint: 'sm' }}
      padding="md"
    >
      <AppShell.Header className="app-header">
        <Group h="100%" px="md" justify="space-between">
          <Box>
            <Title order={1} className="app-title">
              Kithairon Visualizer
            </Title>
            <Text className="app-subtitle">Canon candidate workspace</Text>
          </Box>
          <Badge variant="light" color="teal">
            API-backed
          </Badge>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar className="app-navbar" p="md">
        <Stack gap="md">
          <Paper className="candidate-surface" p="md">
            <Text className="surface-title">Run</Text>
            <Box mt="sm">
              <UploadPanel onRunLoaded={handleRunLoaded} />
            </Box>
          </Paper>
          <Paper className="candidate-surface" p="md">
            <Group justify="space-between" mb="sm">
              <Text className="surface-title">Candidates</Text>
              {runSummary !== null ? (
                <Badge variant="light" color="gray">
                  {candidates.length}
                </Badge>
              ) : null}
            </Group>
            <CandidateTable
              candidates={candidates}
              selectedCandidateId={selectedCandidateId}
              onSelectCandidate={handleCandidateSelect}
            />
          </Paper>
          <Paper className="candidate-surface" p="md">
            <Text className="surface-title" mb="sm">
              Phrase Polish
            </Text>
            <PhrasePolishPanel
              runSummary={runSummary}
              candidates={candidates}
              selectedCandidateId={selectedCandidateId}
              selectedCandidate={selectedCandidate}
              onSelectCandidate={handleCandidateSelect}
              onVariantsReceived={handlePolishVariants}
            />
          </Paper>
          <Paper className="candidate-surface" p="md">
            <Text className="surface-title" mb="sm">
              Candidate Lab
            </Text>
            <CandidateLabPanel
              runSummary={runSummary}
              experiments={experiments}
              onExperimentsChange={setExperiments}
              onSelectCandidate={handleCandidateSelect}
            />
          </Paper>
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Box className="workspace-grid">
          <Stack gap="md">
            <Paper className="score-surface" mih={340} p="md">
              <Group justify="space-between" mb="md">
                <Text className="surface-title">Score</Text>
                {selectedCandidate !== null ? (
                  <Badge variant="light" color="blue">
                    {selectedCandidate.candidate_id}
                  </Badge>
                ) : null}
              </Group>
              {selectedCandidate !== null && runSummary !== null ? (
                <Stack gap="md">
                  <CandidateSummary candidate={selectedCandidate} runSummary={runSummary} />
                  <ScoreView
                    key={selectedCandidate.candidate_id}
                    runId={runSummary.run_id}
                    candidate={selectedCandidate}
                    selectedViolation={selectedViolation}
                  />
                </Stack>
              ) : (
                <CandidateSummary candidate={selectedCandidate} runSummary={runSummary} />
              )}
            </Paper>
            <Paper className="roll-surface" mih={240} p="md">
              <Text className="surface-title">Piano Roll</Text>
              <Box mt="md">
                <PlaybackControls
                  key={selectedCandidate?.candidate_id ?? 'empty-playback'}
                  candidate={selectedCandidate}
                  onActiveEventIdsChange={setActivePlaybackEventIds}
                />
              </Box>
              <Box mt="md">
                <PianoRollView
                  key={selectedCandidate?.candidate_id ?? 'empty'}
                  candidate={selectedCandidate}
                  selectedEventIds={highlightedEventIds}
                  modifiedEventIds={modifiedEventIds}
                  onSelectEvent={handleEventSelect}
                />
              </Box>
              {selectedEventId !== null ? (
                <Text className="empty-surface" mt="sm">
                  Selected {selectedEventId}
                </Text>
              ) : null}
            </Paper>
          </Stack>
          <Paper className="inspector-surface" mih={596} p="md">
            <Text className="surface-title">Inspector</Text>
            <SelectedEventPreview candidate={selectedCandidate} selectedEventId={selectedEventId} />
            {selectedCandidate !== null ? (
              <Box mt="md">
                <ScoreBreakdown
                  score={selectedCandidate.score}
                  activeCategory={violationCategoryFilter}
                  onCategoryFilterChange={setViolationCategoryFilter}
                />
                <Box mt="md">
                  <MusicalityBreakdown musicality={selectedCandidate.musicality} />
                </Box>
              </Box>
            ) : null}
            <Box mt="md">
              <ExportMenu runSummary={runSummary} candidate={selectedCandidate} />
            </Box>
            <StrictRelaxedDiff
              candidate={selectedCandidate}
              selectedActionId={selectedRepairActionId}
              onSelectAction={handleRepairActionSelect}
            />
            <ViolationInspector
              candidate={selectedCandidate}
              selectedViolationId={selectedViolationId}
              categoryFilter={violationCategoryFilter}
              onCategoryFilterChange={setViolationCategoryFilter}
              onSelectViolation={handleViolationSelect}
            />
          </Paper>
        </Box>
      </AppShell.Main>
    </AppShell>
  )
}

type CandidateSummaryProps = {
  candidate: CandidateViz | null
  runSummary: RunSummary | null
}

function CandidateSummary({ candidate, runSummary }: CandidateSummaryProps) {
  if (runSummary === null) {
    return (
      <Alert color="gray" variant="light" title="No run">
        No run loaded.
      </Alert>
    )
  }
  if (candidate === null) {
    return (
      <Alert color="gray" variant="light" title="No selection">
        This run did not return any candidates.
      </Alert>
    )
  }

  return (
    <Stack gap="sm">
      <Group gap="xs">
        <Badge variant="light" color={candidate.transform.strict_canon ? 'teal' : 'orange'}>
          {candidate.transform.strict_canon ? 'strict' : 'relaxed'}
        </Badge>
        <Badge variant="light" color="gray">
          {candidate.transform.engine}
        </Badge>
      </Group>
      <Title order={2} className="candidate-heading">
        {candidate.title}
      </Title>
      <Group gap="xl">
        <Metric label="Score" value={candidate.score.total.toFixed(1)} />
        <Metric label="Music" value={candidate.musicality?.total.toFixed(1) ?? '-'} />
        <Metric label="Delay" value={candidate.transform.delay_q?.text ?? '-'} />
        <Metric label="Interval" value={String(candidate.transform.interval ?? '-')} />
        <Metric label="Violations" value={String(candidate.violations.length)} />
      </Group>
      <Divider />
      <Text size="sm" c="dimmed">
        {runSummary.input_name}
      </Text>
    </Stack>
  )
}

function SelectedEventPreview({
  candidate,
  selectedEventId,
}: {
  candidate: CandidateViz | null
  selectedEventId: string | null
}) {
  if (candidate === null) {
    return null
  }

  const selectedNote = candidate.notes.find((note) => note.event_id === selectedEventId)
  if (selectedNote === undefined) {
    return null
  }

  return (
    <Stack className="selected-event-panel" gap="xs" mt="md">
      <Text fw={700}>{selectedNote.event_id}</Text>
      <Text size="sm">{selectedNote.pitch_name ?? 'Rest'}</Text>
      <Text size="sm" c="dimmed">
        Start {selectedNote.start_q.text} / End {selectedNote.end_q.text}
      </Text>
    </Stack>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Box className="metric">
      <Text className="metric-label">{label}</Text>
      <Text className="metric-value">{value}</Text>
    </Box>
  )
}

function uniqueEventIds(eventIds: string[]): string[] {
  return Array.from(new Set(eventIds))
}

function repairActionEventIds(action: RepairAction | null): string[] {
  if (action === null) {
    return []
  }
  return [action.original_event_id, action.new_event_id].filter(
    (eventId): eventId is string => eventId !== null,
  )
}
