// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnalysisPanel } from './AnalysisPanel'

describe('AnalysisPanel', () => {
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

  it('shows phrase, cadence, and bass summaries', () => {
    render(
      <MantineProvider>
        <AnalysisPanel
          analysis={{
            phrases: [
              {
                phrase_id: 'phrase-01',
                bar_start: 1,
                bar_end: 2,
                start_q: { text: '0', value: 0 },
                end_q: { text: '8', value: 8 },
                event_ids: ['leader:l1'],
                note_count: 8,
                label: 'Bars 1-2',
              },
            ],
            cadence: {
              cadence_id: 'final-cadence',
              bar: 2,
              beat: { text: '1', value: 1 },
              strength: 'weak',
              final_interval: 'P8',
              bass_motion: 0,
              upper_motion: -2,
              event_ids: ['leader:l2', 'follower:f2'],
              label: 'Weak final cadence',
              rationale: 'Weak cadence: final interval P8, bass motion +0.',
            },
            bass_support: {
              voice_id: 'follower',
              bar_start: 1,
              bar_end: 2,
              unique_pitch_count: 1,
              repeated_note_ratio: 1,
              stepwise_motion_ratio: 0,
              average_abs_motion: 0,
              static_bars: [1, 2],
              static_bass: true,
              motion_label: 'static',
            },
          }}
        />
      </MantineProvider>,
    )

    expect(screen.getByText('Analysis')).toBeTruthy()
    expect(screen.getByText('Bars 1-2')).toBeTruthy()
    expect(screen.getByText('Weak final cadence')).toBeTruthy()
    expect(screen.getByText('static')).toBeTruthy()
  })
})
