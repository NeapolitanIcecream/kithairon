// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ScoreBreakdown } from './ScoreBreakdown'

describe('ScoreBreakdown', () => {
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

  it('shows score tables and links category selection to violation filters', async () => {
    const onCategoryFilterChange = vi.fn()
    render(
      <MantineProvider>
        <ScoreBreakdown
          score={{
            total: 88.5,
            by_category: { range: 5, melody: 2 },
            by_rule: { range: 5, large_leap: 2 },
            bonuses: { diversity: 1.5 },
          }}
          activeCategory="all"
          onCategoryFilterChange={onCategoryFilterChange}
        />
      </MantineProvider>,
    )

    expect(screen.getByText('88.5')).toBeTruthy()
    expect(screen.getByText('large_leap')).toBeTruthy()
    expect(screen.getByText('diversity')).toBeTruthy()

    await userEvent.click(screen.getAllByText('range')[0])

    expect(onCategoryFilterChange).toHaveBeenCalledWith('range')
  })
})
