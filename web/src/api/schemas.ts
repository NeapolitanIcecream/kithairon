import { z } from 'zod'

export const RationalSchema = z.object({
  text: z.string(),
  value: z.number(),
})

export const NoteVizSchema = z.object({
  event_id: z.string(),
  ir_event_id: z.string(),
  voice_id: z.string(),
  role: z.enum(['leader', 'follower', 'unknown']),
  pitch: z.number().int().nullable(),
  pitch_name: z.string().nullable(),
  start_q: RationalSchema,
  duration_q: RationalSchema,
  end_q: RationalSchema,
  bar: z.number().int().nullable(),
  beat: RationalSchema.nullable(),
  velocity: z.number().int().nullable(),
  source_event_id: z.string().nullable(),
  transform_origin: z.enum([
    'input',
    'strict_transform',
    'repair',
    'solver',
    'unknown',
  ]),
  repair_action_id: z.string().nullable(),
  score_element_id: z.string().nullable(),
})

export const ViolationVizSchema = z.object({
  violation_id: z.string(),
  rule_id: z.string(),
  severity: z.enum(['hard', 'soft', 'info']),
  penalty: z.number(),
  message: z.string(),
  bar: z.number().int().nullable(),
  beat: RationalSchema.nullable(),
  start_q: RationalSchema.nullable(),
  end_q: RationalSchema.nullable(),
  voice_ids: z.array(z.string()),
  event_ids: z.array(z.string()),
  ir_event_ids: z.array(z.string()),
  related_event_ids: z.array(z.string()),
  category: z.enum([
    'consonance',
    'parallel_motion',
    'range',
    'crossing',
    'melody',
    'cadence',
    'similarity',
    'repair',
    'other',
  ]),
})

export const ScoreBreakdownSchema = z.object({
  total: z.number(),
  by_category: z.record(z.string(), z.number()),
  by_rule: z.record(z.string(), z.number()),
  bonuses: z.record(z.string(), z.number()),
})

export const RepairActionSchema = z.object({
  action_id: z.string(),
  kind: z.enum([
    'octave_displacement',
    'pitch_replacement',
    'passing_tone',
    'rest_insertion',
    'duration_adjustment',
    'solver_assignment',
    'unknown',
  ]),
  original_event_id: z.string().nullable(),
  new_event_id: z.string().nullable(),
  message: z.string(),
  start_q: RationalSchema.nullable(),
  bar: z.number().int().nullable(),
  beat: RationalSchema.nullable(),
})

export const TransformVizSchema = z.object({
  engine: z.enum(['strict', 'repair', 'solver', 'auto']),
  strict_canon: z.boolean(),
  label: z.string(),
  delay_q: RationalSchema.nullable(),
  interval: z.number().int().nullable(),
  transform_mode: z.string().nullable(),
  inversion_axis: z.number().int().nullable(),
  rhythm_scale: z.string().nullable(),
})

export const CandidateVizSchema = z.object({
  candidate_id: z.string(),
  rank: z.number().int().nullable(),
  title: z.string(),
  transform: TransformVizSchema,
  score: ScoreBreakdownSchema,
  notes: z.array(NoteVizSchema),
  violations: z.array(ViolationVizSchema),
  repair_actions: z.array(RepairActionSchema),
  artifacts: z.record(z.string(), z.string()),
  metadata: z.record(z.string(), z.unknown()),
})

export const RunSummarySchema = z.object({
  run_id: z.string(),
  input_name: z.string(),
  created_at: z.string(),
  config_summary: z.record(z.string(), z.unknown()),
  artifacts: z.record(z.string(), z.string()),
  candidates: z.array(CandidateVizSchema),
})

export type Rational = z.infer<typeof RationalSchema>
export type NoteViz = z.infer<typeof NoteVizSchema>
export type ViolationViz = z.infer<typeof ViolationVizSchema>
export type ScoreBreakdown = z.infer<typeof ScoreBreakdownSchema>
export type RepairAction = z.infer<typeof RepairActionSchema>
export type TransformViz = z.infer<typeof TransformVizSchema>
export type CandidateViz = z.infer<typeof CandidateVizSchema>
export type RunSummary = z.infer<typeof RunSummarySchema>
