import { apiFetch, type ApiClientOptions } from './client'
import { RunSummarySchema, type RunSummary } from './schemas'

export type GenerationEngine = 'auto' | 'strict' | 'repair' | 'solver'
export type ScoreProfile = 'permissive' | 'pop-lite' | 'renaissance-lite'
export type ChordPolicy = 'error' | 'top_note' | 'bottom_note'
export type PartPolicy = 'first' | 'highest_average_pitch' | 'explicit_index'

export type RunUploadOptions = {
  file: File
  engine?: GenerationEngine
  scoreProfile?: ScoreProfile
  topK?: number
  chordPolicy?: ChordPolicy
  partPolicy?: PartPolicy
  partIndex?: number
  config?: Record<string, unknown>
}

export async function uploadRun(
  options: RunUploadOptions,
  clientOptions?: ApiClientOptions,
): Promise<RunSummary> {
  const form = new FormData()
  form.append('file', options.file)
  appendOptional(form, 'engine', options.engine)
  appendOptional(form, 'score_profile', options.scoreProfile)
  appendOptional(form, 'top_k', options.topK)
  appendOptional(form, 'chord_policy', options.chordPolicy)
  appendOptional(form, 'part_policy', options.partPolicy)
  appendOptional(form, 'part_index', options.partIndex)

  if (options.config !== undefined) {
    form.append('config', JSON.stringify(options.config))
  }

  const payload = await apiFetch<unknown>(
    '/api/runs',
    {
      method: 'POST',
      body: form,
    },
    clientOptions,
  )
  return RunSummarySchema.parse(payload)
}

function appendOptional(form: FormData, key: string, value: string | number | undefined) {
  if (value !== undefined) {
    form.append(key, String(value))
  }
}
