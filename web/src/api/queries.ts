import { apiFetch } from './client'

export type HealthResponse = {
  status: string
  service: string
  version: string
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/api/health')
}
