import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'

const musicXml = readFileSync(
  new URL('../../examples/melodies/scale_c_major.musicxml', import.meta.url),
  'utf-8',
)

test('user can upload, inspect, play, render, and download a candidate', async ({ page }) => {
  let uploadRequested = false
  let renderRequested = false

  await page.route('**/api/runs', async (route) => {
    uploadRequested = true
    await route.fulfill({ json: runSummary() })
  })
  await page.route('**/api/runs/run-e2e/candidates/relaxed_0001/musicxml', async (route) => {
    await route.fulfill({
      body: musicXml,
      contentType: 'application/vnd.recordare.musicxml+xml',
    })
  })
  await page.route('**/api/runs/run-e2e/candidates/relaxed_0001/render', async (route) => {
    renderRequested = true
    await route.fulfill({
      json: {
        candidate_id: 'relaxed_0001',
        artifacts: { pdf: 'renders/relaxed_0001/relaxed_0001.pdf' },
      },
    })
  })
  await page.route('**/api/runs/run-e2e/artifact/visualization', async (route) => {
    await route.fulfill({
      body: JSON.stringify(runSummary()),
      contentType: 'application/json',
      headers: {
        'content-disposition': 'attachment; filename=visualization.json',
      },
    })
  })

  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'scale_c_major.musicxml',
    mimeType: 'application/vnd.recordare.musicxml+xml',
    buffer: Buffer.from(musicXml),
  })
  await page.getByRole('button', { name: 'Generate' }).click()

  await expect(page.getByRole('button', { name: 'Select Relaxed candidate' })).toBeVisible()
  await expect(page.getByRole('cell', { name: '87.5' })).toBeVisible()
  await expect(page.getByText('repair').first()).toBeVisible()
  await expect(page.getByTestId('score-view-svg')).toBeVisible({ timeout: 20_000 })

  await page.locator('.violation-row').first().click()
  await expect(page.getByText('Score target')).toBeVisible()
  await expect(page.getByText('Selected follower:n0001')).toBeVisible()
  await expect(page.getByText('Diff')).toBeVisible()

  await page.getByRole('button', { name: 'Play' }).click()
  await expect(page.getByRole('button', { name: 'Pause' })).toBeEnabled()
  await page.getByRole('button', { name: 'Stop' }).click()

  await page.getByRole('button', { name: 'Render PDF' }).click()
  await expect(page.getByRole('link', { name: 'Download PDF' })).toBeVisible()

  const visualizationLink = page.getByRole('link', { name: 'Visualization JSON' })
  await expect(visualizationLink).toHaveAttribute('download', '')
  const visualizationHref = await visualizationLink.getAttribute('href')
  const downloadedRunId = await page.evaluate(async (href) => {
    const response = await fetch(href)
    const payload = await response.json()
    return payload.run_id
  }, visualizationHref as string)

  expect(downloadedRunId).toBe('run-e2e')
  expect(uploadRequested).toBe(true)
  expect(renderRequested).toBe(true)
})

function runSummary() {
  return {
    run_id: 'run-e2e',
    input_name: 'scale_c_major.musicxml',
    created_at: '2026-05-19T00:00:00Z',
    config_summary: { generation: { engine: 'repair', top_k: 1 } },
    artifacts: {
      report: 'report.md',
      results: 'results.json',
      visualization: 'visualization.json',
      resolved_config: 'resolved_config.toml',
    },
    candidates: [
      {
        candidate_id: 'relaxed_0001',
        rank: 1,
        title: 'Relaxed candidate',
        transform: {
          engine: 'repair',
          strict_canon: false,
          label: 'relaxed canon',
          delay_q: rational('1', 1),
          interval: 7,
          transform_mode: 'transposition',
          inversion_axis: null,
          rhythm_scale: null,
        },
        score: {
          total: 87.5,
          by_category: { range: 5, parallel_motion: 2 },
          by_rule: { range: 5, parallel_motion: 2 },
          bonuses: { consonance: 1 },
        },
        notes: [
          note('leader:n0001', 'n0001', 'leader', 'leader', 60, 'C4', 0, 1, 'input'),
          note(
            'follower:n0001',
            'n0001',
            'follower',
            'follower',
            79,
            'G5',
            1,
            1,
            'repair',
            'repair_1',
          ),
        ],
        violations: [
          {
            violation_id: 'range_0001',
            rule_id: 'range',
            severity: 'hard',
            penalty: 5,
            message: 'Follower exceeds range.',
            bar: 1,
            beat: rational('2', 2),
            start_q: rational('1', 1),
            end_q: rational('2', 2),
            voice_ids: ['follower'],
            event_ids: ['follower:n0001'],
            ir_event_ids: ['n0001'],
            related_event_ids: ['follower:n0001'],
            category: 'range',
          },
        ],
        repair_actions: [
          {
            action_id: 'repair_1',
            kind: 'octave_displacement',
            original_event_id: 'follower:n0001',
            new_event_id: 'follower:n0001',
            message: 'Shift follower down an octave.',
            start_q: rational('1', 1),
            bar: 1,
            beat: rational('2', 2),
          },
        ],
        artifacts: {
          musicxml: 'candidates/relaxed_0001.musicxml',
          midi: 'candidates/relaxed_0001.mid',
        },
        metadata: {},
      },
    ],
  }
}

function rational(text: string, value: number) {
  return { text, value }
}

function note(
  eventId: string,
  irEventId: string,
  voiceId: string,
  role: 'leader' | 'follower',
  pitch: number,
  pitchName: string,
  startQ: number,
  durationQ: number,
  transformOrigin: 'input' | 'repair',
  repairActionId: string | null = null,
) {
  return {
    event_id: eventId,
    ir_event_id: irEventId,
    voice_id: voiceId,
    role,
    pitch,
    pitch_name: pitchName,
    start_q: rational(String(startQ), startQ),
    duration_q: rational(String(durationQ), durationQ),
    end_q: rational(String(startQ + durationQ), startQ + durationQ),
    bar: 1,
    beat: rational(String(startQ + 1), startQ + 1),
    velocity: 80,
    source_event_id: irEventId,
    transform_origin: transformOrigin,
    repair_action_id: repairActionId,
    score_element_id: eventId,
  }
}
