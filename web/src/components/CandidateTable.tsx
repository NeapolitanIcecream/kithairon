import type { ReactNode } from 'react'
import {
  Alert,
  Badge,
  Button,
  Group,
  ScrollArea,
  Table,
  Text,
  UnstyledButton,
} from '@mantine/core'
import type { CandidateViz } from '../api/schemas'
import { candidateSource, sourceExperimentId } from './candidateUniverse'

type CandidateTableProps = {
  candidates: CandidateViz[]
  selectedCandidateId: string | null
  compareCandidateIds?: string[]
  onSelectCandidate: (candidateId: string) => void
  onToggleCompareCandidate?: (candidateId: string) => void
}

export function CandidateTable({
  candidates,
  selectedCandidateId,
  compareCandidateIds = [],
  onSelectCandidate,
  onToggleCompareCandidate,
}: CandidateTableProps) {
  if (candidates.length === 0) {
    return (
      <Alert color="gray" variant="light" title="No candidates">
        No candidates available.
      </Alert>
    )
  }

  return (
    <ScrollArea type="auto" offsetScrollbars>
      <Table className="candidate-table" striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Rank</Table.Th>
            <Table.Th>Score</Table.Th>
            <Table.Th>Music</Table.Th>
            <Table.Th>Engine</Table.Th>
            <Table.Th>Strict</Table.Th>
            <Table.Th>Source</Table.Th>
            <Table.Th>Label</Table.Th>
            <Table.Th>Delay</Table.Th>
            <Table.Th>Interval</Table.Th>
            <Table.Th>Main issue</Table.Th>
            <Table.Th>Compare</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {candidates.map((candidate) => {
            const selected = candidate.candidate_id === selectedCandidateId
            return (
              <Table.Tr
                key={candidate.candidate_id}
                data-selected={selected || undefined}
                className="candidate-row"
              >
                <Table.Td>
                  <CandidateButton
                    candidate={candidate}
                    onSelectCandidate={onSelectCandidate}
                  >
                    {candidate.rank ?? '-'}
                  </CandidateButton>
                </Table.Td>
                <Table.Td>{formatScore(candidate.score.total)}</Table.Td>
                <Table.Td>{formatOptionalScore(candidate.musicality?.total)}</Table.Td>
                <Table.Td>
                  <Badge variant="light" color={engineColor(candidate.transform.engine)}>
                    {candidate.transform.engine}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Badge
                    variant="light"
                    color={candidate.transform.strict_canon ? 'teal' : 'orange'}
                  >
                    {candidate.transform.strict_canon ? 'yes' : 'no'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <SourceBadge candidate={candidate} />
                </Table.Td>
                <Table.Td>{candidate.transform.label}</Table.Td>
                <Table.Td>{candidate.transform.delay_q?.text ?? '-'}</Table.Td>
                <Table.Td>{candidate.transform.interval ?? '-'}</Table.Td>
                <Table.Td>
                  <Text size="sm" lineClamp={2}>
                    {mainIssue(candidate)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  {onToggleCompareCandidate === undefined ? null : (
                    <Button
                      variant={compareCandidateIds.includes(candidate.candidate_id) ? 'filled' : 'light'}
                      size="compact-sm"
                      onClick={() => onToggleCompareCandidate(candidate.candidate_id)}
                    >
                      {compareCandidateIds.includes(candidate.candidate_id) ? 'Remove' : 'Compare'}
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            )
          })}
        </Table.Tbody>
      </Table>
    </ScrollArea>
  )
}

function SourceBadge({ candidate }: { candidate: CandidateViz }) {
  const source = candidateSource(candidate)
  const experimentId = sourceExperimentId(candidate)
  return (
    <Group gap={4} wrap="nowrap">
      <Badge variant="light" color={source === 'experiment' ? 'violet' : 'gray'}>
        {source}
      </Badge>
      {experimentId === null ? null : (
        <Text size="xs" c="dimmed">
          {experimentId}
        </Text>
      )}
    </Group>
  )
}

type CandidateButtonProps = {
  candidate: CandidateViz
  onSelectCandidate: (candidateId: string) => void
  children: ReactNode
}

function CandidateButton({ candidate, onSelectCandidate, children }: CandidateButtonProps) {
  return (
    <UnstyledButton
      className="candidate-select"
      aria-label={`Select ${candidate.title}`}
      onClick={() => onSelectCandidate(candidate.candidate_id)}
    >
      <Group gap="xs" wrap="nowrap">
        <Text fw={700} size="sm">
          {children}
        </Text>
        <Text size="xs" c="dimmed">
          {candidate.candidate_id}
        </Text>
      </Group>
    </UnstyledButton>
  )
}

function formatScore(score: number): string {
  return score.toFixed(1)
}

function formatOptionalScore(score: number | undefined): string {
  return score === undefined ? '-' : score.toFixed(1)
}

function mainIssue(candidate: CandidateViz): string {
  const hardViolation = candidate.violations.find((violation) => violation.severity === 'hard')
  const firstViolation = hardViolation ?? candidate.violations[0]
  return firstViolation?.message ?? 'None'
}

function engineColor(engine: CandidateViz['transform']['engine']): string {
  if (engine === 'strict') {
    return 'blue'
  }
  if (engine === 'repair') {
    return 'orange'
  }
  if (engine === 'solver') {
    return 'grape'
  }
  return 'gray'
}
