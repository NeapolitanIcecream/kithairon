import { apiFetch, type ApiClientOptions } from './client'

export function fetchCandidateMusicXml(
  runId: string,
  candidateId: string,
  options?: ApiClientOptions,
): Promise<string> {
  return apiFetch<string>(
    `/api/runs/${encodeURIComponent(runId)}/candidates/${encodeURIComponent(candidateId)}/musicxml`,
    {},
    options,
  )
}
