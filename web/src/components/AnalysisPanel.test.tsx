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
                high_point_event_id: 'leader:l4',
                high_point_pitch: 67,
                arrival_event_id: 'leader:l4',
                arrival_pitch: 67,
                repeated_note_plateaus: ['follower:f1', 'follower:f2', 'follower:f3'],
                flat_sequence_warning: true,
                warnings: ['repeated_note_plateau', 'flat_sequence'],
              },
            ],
            cadence: {
              cadence_id: 'final-cadence',
              bar: 2,
              beat: { text: '1', value: 1 },
              strength: 'weak',
              cadence_type: 'weak_close',
              final_interval: 'P8',
              bass_motion: 0,
              upper_motion: -2,
              event_ids: ['leader:l2', 'follower:f2'],
              label: 'Weak final cadence',
              rationale: 'Weak cadence: final interval P8, bass motion +0.',
            },
            cadences: [
              {
                cadence_id: 'phrase-01-cadence',
                bar: 1,
                beat: { text: '1', value: 1 },
                strength: 'moderate',
                cadence_type: 'open_phrase',
                final_interval: 'M3',
                bass_motion: 2,
                upper_motion: 1,
                event_ids: ['leader:l1', 'follower:f1'],
                label: 'Open Phrase',
                rationale: 'Open phrase.',
              },
            ],
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
              strong_beat_support_event_ids: ['follower:f1'],
              root_support_proxy: 1,
              sustained_foundation_score: 0.75,
              bass_independence_score: 0.2,
            },
          }}
        />
      </MantineProvider>,
    )

    expect(screen.getByText('Analysis')).toBeTruthy()
    expect(screen.getByText('Bars 1-2')).toBeTruthy()
    expect(screen.getByText('Weak final cadence')).toBeTruthy()
    expect(screen.getByText('Arrival leader:l4 / high 67')).toBeTruthy()
    expect(screen.getByText('flat_sequence')).toBeTruthy()
    expect(screen.getByText('Open Phrase')).toBeTruthy()
    expect(screen.getByText('Support 100% / foundation 75% / independence 20%')).toBeTruthy()
    expect(screen.getByText('static')).toBeTruthy()
  })
})
