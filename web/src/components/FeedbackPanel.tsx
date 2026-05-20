import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  NumberInput,
  Stack,
  Text,
  Textarea,
} from '@mantine/core'
import { ApiClientError } from '../api/client'
import { polishCandidate, translateFeedback } from '../api/runs'
import type {
  CandidateViz,
  Experiment,
  FeedbackTranslation,
  SuggestedPolishAction,
  RunSummary,
} from '../api/schemas'

type FeedbackPanelProps = {
  runSummary: RunSummary | null
  selectedCandidate: CandidateViz | null
  onVariantsReceived: (variants: CandidateViz[], experiment: Experiment | null | undefined) => void
}

export function FeedbackPanel({
  runSummary,
  selectedCandidate,
  onVariantsReceived,
}: FeedbackPanelProps) {
  const [feedbackText, setFeedbackText] = useState('')
  const [useTargetBars, setUseTargetBars] = useState(false)
  const [barStart, setBarStart] = useState(1)
  const [barEnd, setBarEnd] = useState(1)
  const [translation, setTranslation] = useState<FeedbackTranslation | null>(null)
  const [activeActionId, setActiveActionId] = useState<string | null>(null)

  useEffect(() => {
    setTranslation(null)
    setActiveActionId(null)
  }, [selectedCandidate?.candidate_id])

  const translateMutation = useMutation({
    mutationFn: () => {
      if (runSummary === null) {
        throw new Error('Load a run before translating feedback.')
      }
      return translateFeedback(runSummary.run_id, {
        text: feedbackText.trim(),
        candidateId: selectedCandidate?.candidate_id,
        barStart: useTargetBars ? barStart : undefined,
        barEnd: useTargetBars ? barEnd : undefined,
      })
    },
    onSuccess: setTranslation,
  })

  const actionMutation = useMutation({
    mutationFn: (action: SuggestedPolishAction) => {
      if (runSummary === null || selectedCandidate === null) {
        throw new Error('Select a run candidate before running feedback actions.')
      }
      setActiveActionId(action.action_id)
      return polishCandidate(runSummary.run_id, selectedCandidate.candidate_id, {
        barStart: action.request.bar_start,
        barEnd: action.request.bar_end,
        lockVoice: action.request.lock_voice,
        rewriteVoice: action.request.rewrite_voice,
        maxVariants: action.request.max_variants,
        objectivePreset: action.request.objective_preset,
        objectiveOverrides: action.request.objective_overrides,
      })
    },
    onSuccess: (result) => {
      onVariantsReceived(result.candidates, result.experiment)
    },
    onSettled: () => setActiveActionId(null),
  })

  const disabled = runSummary === null || selectedCandidate === null
  const error = translateMutation.error ?? actionMutation.error
  const errorMessage = error === null ? null : readableErrorMessage(error)

  return (
    <Stack gap="sm">
      <Textarea
        label="Feedback"
        minRows={3}
        value={feedbackText}
        disabled={runSummary === null}
        onChange={(event) => setFeedbackText(event.currentTarget.value)}
      />
      <Checkbox
        label="Target bars"
        checked={useTargetBars}
        disabled={runSummary === null}
        onChange={(event) => setUseTargetBars(event.currentTarget.checked)}
      />
      {useTargetBars ? (
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
      ) : null}
      <Button
        fullWidth
        disabled={disabled || feedbackText.trim().length === 0}
        loading={translateMutation.isPending}
        onClick={() => translateMutation.mutate()}
      >
        Translate feedback
      </Button>
      {errorMessage !== null ? (
        <Alert color="red" variant="light" title="Feedback action failed">
          {errorMessage}
        </Alert>
      ) : null}
      {translation !== null ? (
        <FeedbackTranslationSummary
          translation={translation}
          activeActionId={activeActionId}
          running={actionMutation.isPending}
          disabled={disabled}
          onRunAction={(action) => actionMutation.mutate(action)}
        />
      ) : null}
    </Stack>
  )
}

function FeedbackTranslationSummary({
  translation,
  activeActionId,
  running,
  disabled,
  onRunAction,
}: {
  translation: FeedbackTranslation
  activeActionId: string | null
  running: boolean
  disabled: boolean
  onRunAction: (action: SuggestedPolishAction) => void
}) {
  return (
    <Stack gap="xs">
      <Group gap="xs">
        {translation.intents.length > 0 ? (
          translation.intents.map((intent) => (
            <Badge key={intent} variant="light" color="blue">
              {intent}
            </Badge>
          ))
        ) : (
          <Badge variant="light" color="gray">
            general_polish
          </Badge>
        )}
      </Group>
      <Text size="sm" c="dimmed">
        Bars {translation.target.bar_start ?? '-'}-{translation.target.bar_end ?? '-'}
      </Text>
      {translation.actions.map((action) => (
        <Stack key={action.action_id} gap={4}>
          <Group justify="space-between" align="center">
            <Text size="sm" fw={700}>
              {action.label}
            </Text>
            <Button
              size="xs"
              variant="light"
              disabled={disabled}
              loading={running && activeActionId === action.action_id}
              onClick={() => onRunAction(action)}
            >
              Run action
            </Button>
          </Group>
          <Text size="xs" c="dimmed">
            {action.request.objective_preset}
          </Text>
        </Stack>
      ))}
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

function readableErrorMessage(error: Error): string {
  if (error instanceof ApiClientError) {
    return error.message
  }
  return error.message || 'Feedback could not be translated.'
}
