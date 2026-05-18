import { useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Group,
  Select,
  Stack,
  Text,
  Tooltip,
  UnstyledButton,
} from '@mantine/core'
import type { CandidateViz, ViolationViz } from '../api/schemas'

type ViolationInspectorProps = {
  candidate: CandidateViz | null
  selectedViolationId: string | null
  onSelectViolation: (violation: ViolationViz) => void
}

const severityOptions = [
  { value: 'all', label: 'All severities' },
  { value: 'hard', label: 'Hard' },
  { value: 'soft', label: 'Soft' },
  { value: 'info', label: 'Info' },
]

export function ViolationInspector({
  candidate,
  selectedViolationId,
  onSelectViolation,
}: ViolationInspectorProps) {
  const [severityFilter, setSeverityFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const categoryOptions = useMemo(() => {
    const categories = Array.from(
      new Set((candidate?.violations ?? []).map((violation) => violation.category)),
    ).sort()
    return [
      { value: 'all', label: 'All categories' },
      ...categories.map((category) => ({ value: category, label: category })),
    ]
  }, [candidate])

  const violations = useMemo(() => {
    return (candidate?.violations ?? []).filter((violation) => {
      if (severityFilter !== 'all' && violation.severity !== severityFilter) {
        return false
      }
      if (categoryFilter !== 'all' && violation.category !== categoryFilter) {
        return false
      }
      return true
    })
  }, [candidate, categoryFilter, severityFilter])

  if (candidate === null) {
    return (
      <Alert color="gray" variant="light" title="No candidate">
        No candidate selected.
      </Alert>
    )
  }

  return (
    <Stack gap="sm" mt="md">
      <Group grow>
        <Select
          label="Severity"
          data={severityOptions}
          value={severityFilter}
          allowDeselect={false}
          onChange={(value) => setSeverityFilter(value ?? 'all')}
        />
        <Select
          label="Category"
          data={categoryOptions}
          value={categoryFilter}
          allowDeselect={false}
          onChange={(value) => setCategoryFilter(value ?? 'all')}
        />
      </Group>

      {violations.length === 0 ? (
        <Alert color="gray" variant="light" title="No violations">
          No matching violations.
        </Alert>
      ) : (
        <Stack gap="xs">
          {violations.map((violation) => (
            <ViolationRow
              key={violation.violation_id}
              violation={violation}
              selected={violation.violation_id === selectedViolationId}
              onSelectViolation={onSelectViolation}
            />
          ))}
        </Stack>
      )}
    </Stack>
  )
}

function ViolationRow({
  violation,
  selected,
  onSelectViolation,
}: {
  violation: ViolationViz
  selected: boolean
  onSelectViolation: (violation: ViolationViz) => void
}) {
  return (
    <Tooltip
      label={`${violation.rule_id} penalty ${violation.penalty}`}
      openDelay={250}
      withArrow
    >
      <UnstyledButton
        className="violation-row"
        data-selected={selected || undefined}
        onClick={() => onSelectViolation(violation)}
      >
        <Group justify="space-between" align="flex-start" gap="sm">
          <Stack gap={4}>
            <Group gap="xs">
              <Badge variant="light" color={severityColor(violation.severity)}>
                {violation.severity}
              </Badge>
              <Badge variant="outline" color="gray">
                {violation.category}
              </Badge>
            </Group>
            <Text fw={700} size="sm">
              {violation.rule_id}
            </Text>
            <Text size="sm" lineClamp={2}>
              {violation.message}
            </Text>
            <Text size="xs" c="dimmed">
              Bar {violation.bar ?? '-'} / Beat {violation.beat?.text ?? '-'}
            </Text>
            <Text size="xs" c="dimmed" lineClamp={1}>
              {violation.event_ids.length === 0
                ? 'No event ids'
                : violation.event_ids.join(', ')}
            </Text>
          </Stack>
          <Text className="penalty-value">{violation.penalty.toFixed(1)}</Text>
        </Group>
      </UnstyledButton>
    </Tooltip>
  )
}

function severityColor(severity: ViolationViz['severity']): string {
  if (severity === 'hard') {
    return 'red'
  }
  if (severity === 'soft') {
    return 'yellow'
  }
  return 'blue'
}
