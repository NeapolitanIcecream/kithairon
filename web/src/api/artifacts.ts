import { apiFetch, type ApiClientOptions } from './client'

export type RunArtifactKind = 'report' | 'results' | 'visualization' | 'resolved_config'
export type CandidateArtifactKind = 'musicxml' | 'midi' | 'pdf' | 'svg' | 'png'
export type RenderFormat = 'pdf' | 'svg' | 'png'

export type RenderCandidateResponse = {
  candidate_id: string
  artifacts: Partial<Record<RenderFormat, string>>
}

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

export function runArtifactUrl(runId: string, kind: RunArtifactKind): string {
  return `/api/runs/${encodeURIComponent(runId)}/artifact/${encodeURIComponent(kind)}`
}

export function candidateArtifactUrl(
  runId: string,
  candidateId: string,
  kind: CandidateArtifactKind,
): string {
  if (kind === 'musicxml' || kind === 'midi') {
    return `/api/runs/${encodeURIComponent(runId)}/candidates/${encodeURIComponent(candidateId)}/${kind}`
  }
  return `/api/runs/${encodeURIComponent(runId)}/candidates/${encodeURIComponent(candidateId)}/artifact/${kind}`
}

export function renderCandidateArtifacts(
  runId: string,
  candidateId: string,
  formats: RenderFormat[],
  options?: ApiClientOptions,
): Promise<RenderCandidateResponse> {
  return apiFetch<RenderCandidateResponse>(
    `/api/runs/${encodeURIComponent(runId)}/candidates/${encodeURIComponent(candidateId)}/render`,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ formats }),
    },
    options,
  )
}
