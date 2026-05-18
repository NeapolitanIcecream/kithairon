import { Alert, Badge, Group, Stack, Text, UnstyledButton } from '@mantine/core'
import type { CandidateViz, RepairAction } from '../api/schemas'

type StrictRelaxedDiffProps = {
  candidate: CandidateViz | null
  selectedActionId: string | null
  onSelectAction: (action: RepairAction) => void
}

export function StrictRelaxedDiff({
  candidate,
  selectedActionId,
  onSelectAction,
}: StrictRelaxedDiffProps) {
  if (candidate === null || candidate.transform.strict_canon) {
    return null
  }

  return (
    <Stack className="strict-relaxed-diff" gap="sm">
      <Group justify="space-between">
        <Text className="surface-title">Diff</Text>
        <Badge variant="light" color={candidate.transform.engine === 'solver' ? 'grape' : 'orange'}>
          {candidate.transform.engine === 'solver' ? 'solver' : 'relaxed'}
        </Badge>
      </Group>
      {candidate.repair_actions.length === 0 ? (
        <Alert color="gray" variant="light" title="No actions">
          No repair actions available.
        </Alert>
      ) : (
        <Stack gap="xs">
          {candidate.repair_actions.map((action) => (
            <UnstyledButton
              key={action.action_id}
              className="repair-action-row"
              data-selected={action.action_id === selectedActionId || undefined}
              onClick={() => onSelectAction(action)}
            >
              <Group justify="space-between" align="flex-start" gap="sm">
                <Stack gap={4}>
                  <Group gap="xs">
                    <Badge variant="light" color={action.kind === 'solver_assignment' ? 'grape' : 'orange'}>
                      {action.kind}
                    </Badge>
                    <Text size="xs" c="dimmed">
                      Bar {action.bar ?? '-'} / Beat {action.beat?.text ?? '-'}
                    </Text>
                  </Group>
                  <Text size="sm" fw={700}>
                    {action.message}
                  </Text>
                  <Text size="xs" c="dimmed" lineClamp={1}>
                    {action.original_event_id ?? '-'} {'->'} {action.new_event_id ?? '-'}
                  </Text>
                </Stack>
              </Group>
            </UnstyledButton>
          ))}
        </Stack>
      )}
    </Stack>
  )
}
