// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MusicalityBreakdown } from './MusicalityBreakdown'

describe('MusicalityBreakdown', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it('shows total musicality and normalized metric values', () => {
    render(
      <MantineProvider>
        <MusicalityBreakdown
          musicality={{
            total: 81.5,
            metrics: [
              {
                key: 'repeated_note_density',
                label: 'Repeated-note density',
                raw_value: 0.25,
                normalized_value: 0.75,
                weight: 0.2,
                higher_is_better: false,
              },
            ],
            raw_values: { repeated_note_density: 0.25 },
            normalized_values: { repeated_note_density: 0.75 },
            weights: { repeated_note_density: 0.2 },
          }}
        />
      </MantineProvider>,
    )

    expect(screen.getByText('81.5')).toBeTruthy()
    expect(screen.getByText('Repeated-note density')).toBeTruthy()
    expect(screen.getByText('75')).toBeTruthy()
  })
})
