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
