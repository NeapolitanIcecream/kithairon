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

export const MusicalityMetricSchema = z.object({
  key: z.string(),
  label: z.string(),
  raw_value: z.number(),
  normalized_value: z.number(),
  weight: z.number(),
  higher_is_better: z.boolean(),
})

export const MusicalityBreakdownSchema = z.object({
  total: z.number(),
  metrics: z.array(MusicalityMetricSchema),
  raw_values: z.record(z.string(), z.number()),
  normalized_values: z.record(z.string(), z.number()),
  weights: z.record(z.string(), z.number()),
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

export const PhraseSpanSchema = z.object({
  phrase_id: z.string(),
  bar_start: z.number().int(),
  bar_end: z.number().int(),
  start_q: RationalSchema,
  end_q: RationalSchema,
  event_ids: z.array(z.string()),
  note_count: z.number().int(),
  label: z.string(),
  high_point_event_id: z.string().nullable().optional(),
  high_point_pitch: z.number().int().nullable().optional(),
  arrival_event_id: z.string().nullable().optional(),
  arrival_pitch: z.number().int().nullable().optional(),
  repeated_note_plateaus: z.array(z.string()).optional().default([]),
  flat_sequence_warning: z.boolean().optional().default(false),
  warnings: z.array(z.string()).optional().default([]),
})

export const CadenceSummarySchema = z.object({
  cadence_id: z.string(),
  bar: z.number().int(),
  beat: RationalSchema,
  strength: z.enum(['strong', 'moderate', 'weak']),
  cadence_type: z
    .enum([
      'open_phrase',
      'half_cadence_tendency',
      'authentic_close_tendency',
      'weak_close',
      'ambiguous_close',
    ])
    .optional()
    .default('ambiguous_close'),
  final_interval: z.string(),
  bass_motion: z.number().int().nullable(),
  upper_motion: z.number().int().nullable(),
  event_ids: z.array(z.string()),
  label: z.string(),
  rationale: z.string(),
})

export const BassSupportSchema = z.object({
  voice_id: z.string(),
  bar_start: z.number().int(),
  bar_end: z.number().int(),
  unique_pitch_count: z.number().int(),
  repeated_note_ratio: z.number(),
  stepwise_motion_ratio: z.number(),
  average_abs_motion: z.number(),
  static_bars: z.array(z.number().int()),
  static_bass: z.boolean(),
  motion_label: z.enum(['static', 'stepwise', 'active']),
  strong_beat_support_event_ids: z.array(z.string()).optional().default([]),
  root_support_proxy: z.number().optional().default(0),
  sustained_foundation_score: z.number().optional().default(0),
  bass_independence_score: z.number().optional().default(0),
})

export const CandidateAnalysisSchema = z.object({
  phrases: z.array(PhraseSpanSchema),
  cadence: CadenceSummarySchema.nullable().optional(),
  cadences: z.array(CadenceSummarySchema).optional().default([]),
  bass_support: BassSupportSchema.nullable().optional(),
})

export const CandidateVizSchema = z.object({
  candidate_id: z.string(),
  rank: z.number().int().nullable(),
  title: z.string(),
  transform: TransformVizSchema,
  score: ScoreBreakdownSchema,
  musicality: MusicalityBreakdownSchema.nullable().optional(),
  analysis: CandidateAnalysisSchema.nullable().optional(),
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

export const LockVoiceSchema = z.enum(['leader', 'follower', 'none'])
export const RewriteVoiceSchema = z.enum(['leader', 'follower', 'auto'])
export const ResolvedRewriteVoiceSchema = z.enum(['leader', 'follower'])
export const ObjectivePresetSchema = z.enum([
  'reduce_repetition',
  'smooth_bass',
  'strengthen_cadence',
  'general_polish',
])
export const SearchModeSchema = z.enum(['local_polish', 'rewrite_selected_voice'])

export const PolishObjectiveWeightsSchema = z.object({
  repeated_note_penalty: z.number().nullable().optional(),
  leap_penalty: z.number().nullable().optional(),
  bass_smoothness_penalty: z.number().nullable().optional(),
  cadence_motion_reward: z.number().nullable().optional(),
})

export const PolishRequestSchema = z.object({
  bar_start: z.number().int(),
  bar_end: z.number().int(),
  lock_voice: LockVoiceSchema,
  rewrite_voice: RewriteVoiceSchema,
  max_variants: z.number().int(),
  objective_preset: ObjectivePresetSchema,
  objective_overrides: PolishObjectiveWeightsSchema,
  search_mode: SearchModeSchema.optional().default('local_polish'),
  allow_rhythm_change: z.boolean().optional().default(false),
})

export const PolishSummarySchema = z.object({
  parent_candidate_id: z.string(),
  edited_bars: z.array(z.number().int()),
  lock_voice: LockVoiceSchema,
  rewrite_voice: ResolvedRewriteVoiceSchema,
  objective_preset: ObjectivePresetSchema,
  search_mode: SearchModeSchema.optional().default('local_polish'),
  allow_rhythm_change: z.boolean().optional().default(false),
  requested_variants: z.number().int(),
  returned_variants: z.number().int(),
  changed_notes: z.number().int(),
})

export const ExperimentVariantStatusSchema = z.enum(['undecided', 'kept', 'rejected'])

export const ExperimentVariantSchema = z.object({
  candidate_id: z.string(),
  status: ExperimentVariantStatusSchema,
  candidate: CandidateVizSchema,
})

export const ExperimentSchema = z.object({
  experiment_id: z.string(),
  source_candidate_id: z.string(),
  source_request: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  notes: z.string(),
  variants: z.array(ExperimentVariantSchema),
})

export const PolishResultSchema = z.object({
  request: PolishRequestSchema,
  summary: PolishSummarySchema,
  candidates: z.array(CandidateVizSchema),
  experiment: ExperimentSchema.nullable().optional(),
})

export const FeedbackIntentSchema = z.enum([
  'too_mechanical',
  'too_repetitive',
  'bass_too_static',
  'cadence_weak',
  'melody_too_jumpy',
  'voices_too_rhythmically_similar',
])

export const FeedbackTargetSchema = z.object({
  bar_start: z.number().int().nullable().optional(),
  bar_end: z.number().int().nullable().optional(),
})

export const SuggestedPolishActionSchema = z.object({
  action_id: z.string(),
  label: z.string(),
  reason: z.string(),
  request: PolishRequestSchema,
})

export const FeedbackTranslationSchema = z.object({
  input_text: z.string(),
  candidate_id: z.string().nullable(),
  intents: z.array(FeedbackIntentSchema),
  target: FeedbackTargetSchema,
  actions: z.array(SuggestedPolishActionSchema),
  explanation: z.string(),
})

export type Rational = z.infer<typeof RationalSchema>
export type NoteViz = z.infer<typeof NoteVizSchema>
export type ViolationViz = z.infer<typeof ViolationVizSchema>
export type ScoreBreakdown = z.infer<typeof ScoreBreakdownSchema>
export type MusicalityMetric = z.infer<typeof MusicalityMetricSchema>
export type MusicalityBreakdown = z.infer<typeof MusicalityBreakdownSchema>
export type RepairAction = z.infer<typeof RepairActionSchema>
export type TransformViz = z.infer<typeof TransformVizSchema>
export type PhraseSpan = z.infer<typeof PhraseSpanSchema>
export type CadenceSummary = z.infer<typeof CadenceSummarySchema>
export type BassSupport = z.infer<typeof BassSupportSchema>
export type CandidateAnalysis = z.infer<typeof CandidateAnalysisSchema>
export type CandidateViz = z.infer<typeof CandidateVizSchema>
export type RunSummary = z.infer<typeof RunSummarySchema>
export type LockVoice = z.infer<typeof LockVoiceSchema>
export type RewriteVoice = z.infer<typeof RewriteVoiceSchema>
export type ObjectivePreset = z.infer<typeof ObjectivePresetSchema>
export type SearchMode = z.infer<typeof SearchModeSchema>
export type PolishObjectiveWeights = z.infer<typeof PolishObjectiveWeightsSchema>
export type PolishRequest = z.infer<typeof PolishRequestSchema>
export type PolishSummary = z.infer<typeof PolishSummarySchema>
export type ExperimentVariantStatus = z.infer<typeof ExperimentVariantStatusSchema>
export type ExperimentVariant = z.infer<typeof ExperimentVariantSchema>
export type Experiment = z.infer<typeof ExperimentSchema>
export type PolishResult = z.infer<typeof PolishResultSchema>
export type FeedbackIntent = z.infer<typeof FeedbackIntentSchema>
export type FeedbackTarget = z.infer<typeof FeedbackTargetSchema>
export type SuggestedPolishAction = z.infer<typeof SuggestedPolishActionSchema>
export type FeedbackTranslation = z.infer<typeof FeedbackTranslationSchema>
