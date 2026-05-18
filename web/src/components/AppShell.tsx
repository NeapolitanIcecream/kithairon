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
import type { CandidateViz, RunSummary } from '../api/schemas'
import { CandidateTable } from './CandidateTable'
import { UploadPanel } from './UploadPanel'

export function KithaironAppShell() {
  const [runSummary, setRunSummary] = useState<RunSummary | null>(null)
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)
  const candidates = useMemo(() => runSummary?.candidates ?? [], [runSummary])
  const selectedCandidate = useMemo(
    () =>
      candidates.find((candidate) => candidate.candidate_id === selectedCandidateId) ?? null,
    [candidates, selectedCandidateId],
  )

  function handleRunLoaded(nextRunSummary: RunSummary) {
    setRunSummary(nextRunSummary)
    setSelectedCandidateId(nextRunSummary.candidates[0]?.candidate_id ?? null)
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
              onSelectCandidate={setSelectedCandidateId}
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
              <CandidateSummary candidate={selectedCandidate} runSummary={runSummary} />
            </Paper>
            <Paper className="roll-surface" mih={240} p="md">
              <Text className="surface-title">Piano Roll</Text>
              <EmptyWorkSurface
                message={
                  selectedCandidate === null
                    ? 'No candidate selected.'
                    : 'Timeline not available.'
                }
              />
            </Paper>
          </Stack>
          <Paper className="inspector-surface" mih={596} p="md">
            <Text className="surface-title">Inspector</Text>
            <InspectorPreview candidate={selectedCandidate} />
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

function InspectorPreview({ candidate }: { candidate: CandidateViz | null }) {
  if (candidate === null) {
    return <EmptyWorkSurface message="No candidate selected." />
  }

  const firstViolation = candidate.violations[0]
  if (firstViolation === undefined) {
    return <EmptyWorkSurface message="No violations for this candidate." />
  }

  return (
    <Stack gap="sm" mt="md">
      <Badge variant="light" color={firstViolation.severity === 'hard' ? 'red' : 'yellow'}>
        {firstViolation.severity}
      </Badge>
      <Text fw={700}>{firstViolation.rule_id}</Text>
      <Text size="sm">{firstViolation.message}</Text>
      <Text size="sm" c="dimmed">
        Bar {firstViolation.bar ?? '-'} / Beat {firstViolation.beat?.text ?? '-'}
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

function EmptyWorkSurface({ message }: { message: string }) {
  return (
    <Text className="empty-surface" mt="md">
      {message}
    </Text>
  )
}
