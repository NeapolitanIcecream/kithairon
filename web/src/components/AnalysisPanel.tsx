import { Badge, Button, Group, Stack, Table, Text } from '@mantine/core'
import type { CandidateAnalysis, ObjectivePreset, SearchMode } from '../api/schemas'

export type AnalysisPolishRequest = {
  barStart: number
  barEnd: number
  lockVoice?: 'leader' | 'follower' | 'none'
  rewriteVoice?: 'leader' | 'follower' | 'auto'
  objectivePreset: ObjectivePreset
  searchMode?: SearchMode
}

type AnalysisPanelProps = {
  analysis: CandidateAnalysis | null | undefined
  onHighlightEvents?: (eventIds: string[]) => void
  onPolishFinding?: (request: AnalysisPolishRequest) => void
  polishDisabled?: boolean
  polishRunning?: boolean
}

export function AnalysisPanel({
  analysis,
  onHighlightEvents,
  onPolishFinding,
  polishDisabled = false,
  polishRunning = false,
}: AnalysisPanelProps) {
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
                  <Button
                    variant="subtle"
                    size="compact-sm"
                    onClick={() => onHighlightEvents?.(phrase.event_ids)}
                  >
                    {phrase.label}
                  </Button>
                <Text size="xs" c="dimmed">
                  {phrase.note_count} notes
                </Text>
                {phrase.arrival_event_id !== null && phrase.arrival_event_id !== undefined ? (
                  <Group gap={4} mt={4}>
                    <Button
                      variant="subtle"
                      size="compact-xs"
                      onClick={() => highlightKnownEvents(onHighlightEvents, [phrase.arrival_event_id])}
                    >
                      Arrival {phrase.arrival_event_id}
                    </Button>
                    {phrase.high_point_event_id === null ||
                    phrase.high_point_event_id === undefined ? null : (
                      <Button
                        variant="subtle"
                        size="compact-xs"
                        onClick={() =>
                          highlightKnownEvents(onHighlightEvents, [phrase.high_point_event_id])
                        }
                      >
                        High {phrase.high_point_pitch ?? '-'}
                      </Button>
                    )}
                  </Group>
                ) : null}
                {phrase.warnings.length > 0 ? (
                  <Group gap={4} mt={4}>
                    {phrase.warnings.map((warning) => (
                      <Button
                        key={warning}
                        variant="light"
                        color="orange"
                        size="compact-xs"
                        onClick={() =>
                          onHighlightEvents?.(
                            warning === 'repeated_note_plateau' &&
                              phrase.repeated_note_plateaus.length > 0
                              ? phrase.repeated_note_plateaus
                              : phrase.event_ids,
                          )
                        }
                      >
                        {warning}
                      </Button>
                    ))}
                    <Button
                      variant="light"
                      color="teal"
                      size="compact-xs"
                      disabled={polishDisabled}
                      loading={polishRunning}
                      onClick={() =>
                        onPolishFinding?.({
                          barStart: phrase.bar_start,
                          barEnd: phrase.bar_end,
                          objectivePreset: 'reduce_repetition',
                        })
                      }
                    >
                      Polish finding
                    </Button>
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
              <Button
                variant="subtle"
                size="compact-sm"
                onClick={() => onHighlightEvents?.(cadence.event_ids)}
              >
                {cadence.label}
              </Button>
              <Group gap={4}>
                <Badge size="xs" variant="light" color={cadenceColor(cadence.strength)}>
                  Bar {cadence.bar}
                </Badge>
                {cadence.strength === 'strong' ? null : (
                  <Button
                    variant="light"
                    color="teal"
                    size="compact-xs"
                    disabled={polishDisabled}
                    loading={polishRunning}
                    onClick={() =>
                      onPolishFinding?.({
                        barStart: Math.max(1, cadence.bar - 1),
                        barEnd: cadence.bar,
                        rewriteVoice: 'auto',
                        objectivePreset: 'strengthen_cadence',
                      })
                    }
                  >
                    Polish cadence
                  </Button>
                )}
              </Group>
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
          {analysis.bass_support.strong_beat_support_event_ids.length > 0 ? (
            <Group gap={4}>
              {analysis.bass_support.strong_beat_support_event_ids.map((eventId) => (
                <Button
                  key={eventId}
                  variant="subtle"
                  size="compact-xs"
                  onClick={() => onHighlightEvents?.([eventId])}
                >
                  {eventId}
                </Button>
              ))}
            </Group>
          ) : null}
          {analysis.bass_support.static_bass ? (
            <Button
              variant="light"
              color="teal"
              size="compact-xs"
              disabled={polishDisabled}
              loading={polishRunning}
              onClick={() =>
                onPolishFinding?.({
                  barStart: analysis.bass_support?.static_bars[0] ?? analysis.bass_support?.bar_start ?? 1,
                  barEnd:
                    analysis.bass_support?.static_bars.at(-1) ??
                    analysis.bass_support?.bar_end ??
                    1,
                  lockVoice: 'leader',
                  rewriteVoice: 'follower',
                  objectivePreset: 'smooth_bass',
                  searchMode: 'rewrite_selected_voice',
                })
              }
            >
              Polish bass support
            </Button>
          ) : null}
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

function highlightKnownEvents(
  onHighlightEvents: ((eventIds: string[]) => void) | undefined,
  eventIds: Array<string | null | undefined>,
) {
  const knownEventIds = eventIds.filter((eventId): eventId is string => typeof eventId === 'string')
  if (knownEventIds.length > 0) {
    onHighlightEvents?.(knownEventIds)
  }
}
