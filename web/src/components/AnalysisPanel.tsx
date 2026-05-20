import { Badge, Group, Stack, Table, Text } from '@mantine/core'
import type { CandidateAnalysis } from '../api/schemas'

type AnalysisPanelProps = {
  analysis: CandidateAnalysis | null | undefined
}

export function AnalysisPanel({ analysis }: AnalysisPanelProps) {
  if (analysis === null || analysis === undefined) {
    return null
  }

  return (
    <Stack className="analysis-panel" gap="sm">
      <Group justify="space-between">
        <Text className="surface-title">Analysis</Text>
        {analysis.cadence !== null && analysis.cadence !== undefined ? (
          <Badge variant="light" color={cadenceColor(analysis.cadence.strength)}>
            {analysis.cadence.strength}
          </Badge>
        ) : null}
      </Group>
      {analysis.phrases.length > 0 ? (
        <Table className="breakdown-table" withTableBorder>
          <Table.Tbody>
            {analysis.phrases.map((phrase) => (
              <Table.Tr key={phrase.phrase_id}>
                <Table.Td>
                  <Text size="sm">{phrase.label}</Text>
                <Text size="xs" c="dimmed">
                  {phrase.note_count} notes
                </Text>
                {phrase.arrival_event_id !== null && phrase.arrival_event_id !== undefined ? (
                  <Text size="xs" c="dimmed">
                    Arrival {phrase.arrival_event_id} / high {phrase.high_point_pitch ?? '-'}
                  </Text>
                ) : null}
                {phrase.warnings.length > 0 ? (
                  <Group gap={4} mt={4}>
                    {phrase.warnings.map((warning) => (
                      <Badge key={warning} size="xs" variant="light" color="orange">
                        {warning}
                      </Badge>
                    ))}
                  </Group>
                ) : null}
              </Table.Td>
                <Table.Td className="breakdown-value">
                  {phrase.start_q.text}-{phrase.end_q.text}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : null}
      {analysis.cadence !== null && analysis.cadence !== undefined ? (
        <Stack gap={4}>
          <Text size="sm" fw={700}>
            {analysis.cadence.label}
          </Text>
          <Text size="xs" c="dimmed">
            Bar {analysis.cadence.bar}, interval {analysis.cadence.final_interval}, bass{' '}
            {motionText(analysis.cadence.bass_motion)}
          </Text>
        </Stack>
      ) : null}
      {analysis.cadences.length > 0 ? (
        <Stack gap={4}>
          {analysis.cadences.map((cadence) => (
            <Group key={cadence.cadence_id} justify="space-between">
              <Text size="sm">{cadence.label}</Text>
              <Badge size="xs" variant="light" color={cadenceColor(cadence.strength)}>
                Bar {cadence.bar}
              </Badge>
            </Group>
          ))}
        </Stack>
      ) : null}
      {analysis.bass_support !== null && analysis.bass_support !== undefined ? (
        <Stack gap={4}>
          <Group gap="xs">
            <Badge variant="light" color={analysis.bass_support.static_bass ? 'orange' : 'teal'}>
              {analysis.bass_support.motion_label}
            </Badge>
            <Text size="sm">{analysis.bass_support.voice_id}</Text>
          </Group>
          <Text size="xs" c="dimmed">
            Repeat {(analysis.bass_support.repeated_note_ratio * 100).toFixed(0)}% / stepwise{' '}
            {(analysis.bass_support.stepwise_motion_ratio * 100).toFixed(0)}%
          </Text>
          <Text size="xs" c="dimmed">
            Support {(analysis.bass_support.root_support_proxy * 100).toFixed(0)}% / foundation{' '}
            {(analysis.bass_support.sustained_foundation_score * 100).toFixed(0)}% / independence{' '}
            {(analysis.bass_support.bass_independence_score * 100).toFixed(0)}%
          </Text>
        </Stack>
      ) : null}
    </Stack>
  )
}

function cadenceColor(strength: string): string {
  if (strength === 'strong') {
    return 'teal'
  }
  if (strength === 'moderate') {
    return 'blue'
  }
  return 'orange'
}

function motionText(value: number | null): string {
  if (value === null) {
    return '-'
  }
  return value > 0 ? `+${value}` : String(value)
}
