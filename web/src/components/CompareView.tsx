import type { ReactNode } from 'react'
import { Alert, Anchor, Badge, Button, Group, Stack, Table, Text, Title } from '@mantine/core'
import type { CandidateViz, RunSummary } from '../api/schemas'

type CompareViewProps = {
  runSummary: RunSummary | null
  candidates: CandidateViz[]
  onClear: () => void
}

export function CompareView({ runSummary, candidates, onClear }: CompareViewProps) {
  if (candidates.length < 2) {
    return (
      <Alert color="gray" variant="light" title="Compare">
        Select two candidates to compare.
      </Alert>
    )
  }

  const [left, right] = candidates
  return (
    <Stack className="compare-view" gap="sm">
      <Group justify="space-between">
        <Text className="surface-title">A/B Compare</Text>
        <Button variant="subtle" size="compact-sm" onClick={onClear}>
          Clear
        </Button>
      </Group>
      <Table className="compare-table" withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Field</Table.Th>
            <Table.Th>{left.candidate_id}</Table.Th>
            <Table.Th>{right.candidate_id}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          <CompareRow label="Title" left={<CandidateHeader candidate={left} />} right={<CandidateHeader candidate={right} />} />
          <CompareRow label="Rule score" left={left.score.total.toFixed(1)} right={right.score.total.toFixed(1)} />
          <CompareRow
            label="Musicality"
            left={formatOptionalScore(left.musicality?.total)}
            right={formatOptionalScore(right.musicality?.total)}
          />
          <CompareRow
            label="Violations"
            left={<ViolationSummary candidate={left} />}
            right={<ViolationSummary candidate={right} />}
          />
          <CompareRow
            label="Rewrite diff"
            left={<RewriteSummary candidate={left} />}
            right={<RewriteSummary candidate={right} />}
          />
          <CompareRow
            label="Exports"
            left={<ArtifactLinks runSummary={runSummary} candidate={left} />}
            right={<ArtifactLinks runSummary={runSummary} candidate={right} />}
          />
        </Table.Tbody>
      </Table>
    </Stack>
  )
}

function CompareRow({
  label,
  left,
  right,
}: {
  label: string
  left: ReactNode
  right: ReactNode
}) {
  return (
    <Table.Tr>
      <Table.Td>
        <Text fw={700} size="sm">
          {label}
        </Text>
      </Table.Td>
      <Table.Td>{left}</Table.Td>
      <Table.Td>{right}</Table.Td>
    </Table.Tr>
  )
}

function CandidateHeader({ candidate }: { candidate: CandidateViz }) {
  return (
    <Stack gap={4}>
      <Title order={3} className="compare-heading">
        {candidate.title}
      </Title>
      <Group gap="xs">
        <Badge variant="light" color={candidate.transform.strict_canon ? 'teal' : 'orange'}>
          {candidate.transform.strict_canon ? 'strict' : 'relaxed'}
        </Badge>
        <Badge variant="light" color="gray">
          {candidate.transform.engine}
        </Badge>
      </Group>
    </Stack>
  )
}

function ViolationSummary({ candidate }: { candidate: CandidateViz }) {
  const hard = candidate.violations.filter((violation) => violation.severity === 'hard').length
  const soft = candidate.violations.filter((violation) => violation.severity === 'soft').length
  const first = candidate.violations[0]?.message ?? 'None'
  return (
    <Stack gap={4}>
      <Text size="sm">
        {hard} hard / {soft} soft
      </Text>
      <Text size="xs" c="dimmed" lineClamp={2}>
        {first}
      </Text>
    </Stack>
  )
}

function RewriteSummary({ candidate }: { candidate: CandidateViz }) {
  const parent = candidate.metadata.parent_candidate_id
  const editedBars = candidate.metadata.edited_bars
  const rewriteVoice = candidate.metadata.rewrite_voice
  const searchMode = candidate.metadata.search_mode
  if (typeof parent === 'string') {
    const mode = searchMode === 'rewrite_selected_voice' ? 'fixed voice' : 'local polish'
    return (
      <Stack gap={4}>
        <Text size="sm">Parent {parent}</Text>
        <Text size="xs" c="dimmed">
          {mode} / {typeof rewriteVoice === 'string' ? rewriteVoice : 'rewrite'} /{' '}
          {Array.isArray(editedBars) ? editedBars.join('-') : 'bars ?'}
        </Text>
      </Stack>
    )
  }
  if (candidate.repair_actions.length > 0) {
    return <Text size="sm">{candidate.repair_actions.length} repair actions</Text>
  }
  return <Text size="sm">No rewrite metadata</Text>
}

function ArtifactLinks({
  runSummary,
  candidate,
}: {
  runSummary: RunSummary | null
  candidate: CandidateViz
}) {
  if (runSummary === null || Object.keys(candidate.artifacts).length === 0) {
    return <Text size="sm">No exports</Text>
  }
  return (
    <Group gap="xs">
      {Object.entries(candidate.artifacts).map(([kind, path]) => (
        <Anchor key={kind} href={artifactHref(runSummary.run_id, candidate.candidate_id, kind, path)}>
          {kind}
        </Anchor>
      ))}
    </Group>
  )
}

function artifactHref(runId: string, candidateId: string, kind: string, path: string): string {
  if (path.startsWith('/')) {
    return path
  }
  return `/api/runs/${encodeURIComponent(runId)}/candidates/${encodeURIComponent(candidateId)}/artifact/${encodeURIComponent(kind)}`
}

function formatOptionalScore(value: number | undefined): string {
  return value === undefined ? '-' : value.toFixed(1)
}
