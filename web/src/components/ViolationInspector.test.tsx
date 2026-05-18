// @vitest-environment jsdom
import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CandidateViz, ViolationViz } from '../api/schemas'
import { ViolationInspector } from './ViolationInspector'

describe('ViolationInspector', () => {
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

  it('selects violations with their full visualization payload', async () => {
    const onSelectViolation = vi.fn()
    render(
      <MantineProvider>
        <ViolationInspector
          candidate={candidate()}
          selectedViolationId={null}
          onSelectViolation={onSelectViolation}
        />
      </MantineProvider>,
    )

    await userEvent.click(screen.getByText('large_leap'))

    expect(onSelectViolation).toHaveBeenCalledWith(
      expect.objectContaining({
        violation_id: 'strict_0001:v0002:large_leap',
        event_ids: ['follower:n0001', 'follower:n0002'],
      }),
    )
  })
})

function candidate(): CandidateViz {
  return {
    candidate_id: 'strict_0001',
    rank: 1,
    title: 'Candidate 1',
    transform: {
      engine: 'strict',
      strict_canon: true,
      label: 'transposition',
      delay_q: { text: '1', value: 1 },
      interval: 7,
      transform_mode: 'transposition',
      inversion_axis: null,
      rhythm_scale: '1',
    },
    score: {
      total: 92,
      by_category: {},
      by_rule: {},
      bonuses: {},
    },
    notes: [],
    violations: [
      violation('strict_0001:v0001:range', 'range', 'hard', ['follower:n0001']),
      violation('strict_0001:v0002:large_leap', 'large_leap', 'soft', [
        'follower:n0001',
        'follower:n0002',
      ]),
    ],
    repair_actions: [],
    artifacts: {},
    metadata: {},
  }
}

function violation(
  violationId: string,
  ruleId: string,
  severity: ViolationViz['severity'],
  eventIds: string[],
): ViolationViz {
  return {
    violation_id: violationId,
    rule_id: ruleId,
    severity,
    penalty: severity === 'hard' ? 5 : 2,
    message: `${ruleId} message`,
    bar: 1,
    beat: { text: '1', value: 1 },
    start_q: { text: '0', value: 0 },
    end_q: { text: '1', value: 1 },
    voice_ids: ['follower'],
    event_ids: eventIds,
    ir_event_ids: eventIds.map((eventId) => eventId.split(':')[1]),
    related_event_ids: [],
    category: ruleId === 'range' ? 'range' : 'melody',
  }
}
