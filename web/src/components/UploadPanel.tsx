import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Alert,
  Button,
  FileInput,
  Group,
  NumberInput,
  Select,
  Stack,
} from '@mantine/core'
import { ApiClientError } from '../api/client'
import {
  uploadRun,
  type ChordPolicy,
  type GenerationEngine,
  type PartPolicy,
} from '../api/runs'
import type { RunSummary } from '../api/schemas'

type UploadPanelProps = {
  onRunLoaded: (runSummary: RunSummary) => void
}

const engineOptions: Array<{ value: GenerationEngine; label: string }> = [
  { value: 'auto', label: 'Auto' },
  { value: 'strict', label: 'Strict' },
  { value: 'repair', label: 'Repair' },
  { value: 'solver', label: 'Solver' },
]

const chordPolicyOptions: Array<{ value: ChordPolicy; label: string }> = [
  { value: 'error', label: 'Error' },
  { value: 'top_note', label: 'Top note' },
  { value: 'bottom_note', label: 'Bottom note' },
]

const partPolicyOptions: Array<{ value: PartPolicy; label: string }> = [
  { value: 'first', label: 'First' },
  { value: 'highest_average_pitch', label: 'Highest average pitch' },
  { value: 'explicit_index', label: 'Explicit index' },
]

export function UploadPanel({ onRunLoaded }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [engine, setEngine] = useState<GenerationEngine>('auto')
  const [topK, setTopK] = useState(8)
  const [chordPolicy, setChordPolicy] = useState<ChordPolicy>('error')
  const [partPolicy, setPartPolicy] = useState<PartPolicy>('first')
  const [partIndex, setPartIndex] = useState(0)

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (file === null) {
        throw new Error('Choose a MIDI or MusicXML file before generating.')
      }
      return uploadRun({
        file,
        engine,
        topK,
        chordPolicy,
        partPolicy,
        partIndex: partPolicy === 'explicit_index' ? partIndex : undefined,
      })
    },
    onSuccess: onRunLoaded,
  })

  const errorMessage = uploadMutation.error
    ? readableErrorMessage(uploadMutation.error)
    : null

  return (
    <Stack gap="sm">
      <FileInput
        label="Input file"
        accept=".mid,.midi,.musicxml,.xml,.mxl"
        value={file}
        onChange={setFile}
        clearable
      />
      <Group grow align="flex-end">
        <Select
          label="Engine"
          data={engineOptions}
          value={engine}
          allowDeselect={false}
          onChange={(value) => setEngine((value ?? 'auto') as GenerationEngine)}
        />
        <NumberInput
          label="Top K"
          min={1}
          max={50}
          value={topK}
          onChange={(value) => setTopK(toPositiveInteger(value, 8))}
        />
      </Group>
      <Group grow align="flex-end">
        <Select
          label="Chord policy"
          data={chordPolicyOptions}
          value={chordPolicy}
          allowDeselect={false}
          onChange={(value) => setChordPolicy((value ?? 'error') as ChordPolicy)}
        />
        <Select
          label="Part policy"
          data={partPolicyOptions}
          value={partPolicy}
          allowDeselect={false}
          onChange={(value) => setPartPolicy((value ?? 'first') as PartPolicy)}
        />
      </Group>
      {partPolicy === 'explicit_index' ? (
        <NumberInput
          label="Part index"
          min={0}
          value={partIndex}
          onChange={(value) => setPartIndex(toNonNegativeInteger(value, 0))}
        />
      ) : null}
      <Button
        fullWidth
        loading={uploadMutation.isPending}
        disabled={file === null}
        onClick={() => uploadMutation.mutate()}
      >
        Generate
      </Button>
      {errorMessage !== null ? (
        <Alert color="red" variant="light" title="Generation failed">
          {errorMessage}
        </Alert>
      ) : null}
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

function toNonNegativeInteger(value: string | number, fallback: number): number {
  const parsed = typeof value === 'number' ? value : Number.parseInt(value, 10)
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback
  }
  return Math.floor(parsed)
}

function readableErrorMessage(error: Error): string {
  if (error instanceof ApiClientError) {
    return error.message
  }
  return error.message || 'The run could not be generated.'
}
