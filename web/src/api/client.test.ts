import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiClientError, apiFetch } from './client'

describe('apiFetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns parsed JSON for successful responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(JSON.stringify({ status: 'ok' }), {
          headers: { 'content-type': 'application/json' },
          status: 200,
        })
      }),
    )

    await expect(apiFetch<{ status: string }>('/api/health')).resolves.toEqual({
      status: 'ok',
    })
  })

  it('throws ApiClientError with server diagnostic message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        return new Response(JSON.stringify({ message: 'Unsupported file' }), {
          headers: { 'content-type': 'application/json' },
          status: 400,
        })
      }),
    )

    await expect(apiFetch('/api/runs')).rejects.toMatchObject({
      message: 'Unsupported file',
      status: 400,
    } satisfies Partial<ApiClientError>)
  })
})
