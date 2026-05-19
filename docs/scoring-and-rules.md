# Scoring And Rules

This page explains how Kithairon ranks canon candidates. It is for users who want to understand why one candidate is preferred over another, why a candidate is labeled strict or relaxed, and which musical assumptions are built into the default rules.

Kithairon is an explainable symbolic generator, not a complete counterpoint teacher. The rules are deliberately small and inspectable. They favor playable two-voice canon variants that avoid the most obvious vertical and voice-leading problems.

## Score Model

Each candidate starts from a base score of `100`. Kithairon analyzes the two voices, collects rule violations, weights each violation, subtracts the weighted penalties, and clamps the final score to the `0..100` range.

The weighted penalty is:

```text
base rule penalty * score-profile rule weight * severity weight
```

The final score, penalty breakdown, top penalties, score profile, and quality status are written to `results.json`, `report.md`, and `visualization.json`.

## Hard And Soft Rules

Hard rules are not absolute generation blockers in the strict engine. They are high-severity findings that strongly reduce the score and make the report explain why a candidate is weak. Repair and solver engines can then try to improve those candidates under edit limits.

Soft rules mark weaker preferences. A candidate can still be useful when it has soft violations, especially in the `permissive` profile.

| Rule ID | Severity | Base penalty | What it checks |
| --- | --- | ---: | --- |
| `strong_beat_consonance` | hard | 12 | Strong and medium beat verticalities should be consonant. |
| `weak_beat_dissonance` | soft | 2 | Weak-beat dissonance is allowed but penalized. |
| `parallel_perfect` | hard | 14 | Adjacent sonorities should not move in parallel perfect unisons, fifths, or octaves. |
| `voice_crossing` | hard | 10 | The two voices should not flip register order between adjacent verticalities. |
| `range` | soft | 4 | Pitches should stay in the configured lower or upper voice range. |
| `large_leap` | soft | 3 | Melodic leaps larger than 12 semitones are penalized. |
| `cadence_stability` | soft | 6 | The final vertical sonority should resolve to a cadential consonance. |

## Consonance Assumptions

Vertical consonance uses simple intervals modulo the octave. The default consonant semitone classes are:

```text
0, 3, 4, 7, 8, 9
```

Those correspond to unison or octave, minor and major thirds, perfect fifth, and minor and major sixths. Seconds, fourths, tritones, and sevenths are treated as dissonant by default.

This is a compact rule set aimed at clear two-voice output. It does not model every historical exception, suspension treatment, preparation, resolution, style period, or species-counterpoint distinction.

## Score Profiles

The default score profile is `pop-lite`. Profiles do not change the rule set. They change how strongly each rule and severity affects the final score.

| Profile | Intended use | Main effect |
| --- | --- | --- |
| `permissive` | Exploration and rough sketches. | Reduces hard and soft severity weights and lowers some rule weights. |
| `pop-lite` | Default practical ranking. | Keeps consonance important while being less strict than a Renaissance-style profile. |
| `renaissance-lite` | Stricter contrapuntal filtering. | Raises weights for accented dissonance, parallels, crossing, leap, and cadence issues. |

Use a stricter profile when you want the top candidates to avoid traditional counterpoint problems more aggressively. Use a looser profile when you want more variety or plan to edit the result manually.

## Strict And Relaxed Candidates

A strict canon keeps the follower voice as an exact transform of the input melody. Its `results.json` entry has:

```json
{
  "strict_canon": true,
  "canon_label": "strict canon"
}
```

A relaxed canon keeps the source transform and candidate lineage, but it may edit follower notes. Its `results.json` entry has:

```json
{
  "strict_canon": false,
  "canon_label": "relaxed canon"
}
```

Relaxed candidates are useful when strict transforms produce too many penalties. The report records the edit plan so users can see which notes changed and why.

## Solver Objective

The CP-SAT solver searches for a relaxed follower voice under edit limits. It uses hard constraints and soft objective terms:

Hard constraints:

- Strong and medium beat verticalities must meet the consonance requirements used by the solver.
- Follower pitches must stay within the solver range.
- The number of edited follower notes must stay under `[solver].max_edited_notes`.

Soft objectives:

- Minimize edit distance from the strict follower.
- Prefer nearby pitch changes.
- Prefer consonance on weak beats.
- Prefer a cadential consonance at the end.

Current solver constants are intentionally simple: follower pitch range `36..88`, edit cost `100`, pitch-distance weight `2`, weak-dissonance cost `12`, cadence cost `16`, and cadential semitone classes `0, 3, 4, 7`. These values make the solver conservative: it should improve weak strict candidates without rewriting the melody beyond recognition.

## Suitable Melody Types

Kithairon works best with:

- Short monophonic melodies.
- Clear rhythmic placement.
- Mostly stepwise or moderate melodic motion.
- Pitches that stay within a practical vocal or instrumental register.
- Inputs where imitation at delays such as `1`, `2`, `4`, or `8` quarter notes is musically plausible.

Kithairon is more likely to struggle with:

- Dense chromatic lines.
- Very large leaps.
- Highly syncopated melodies where strong-beat alignment is ambiguous.
- Wide-register melodies that force the follower out of range.
- Source material that already contains implied harmony that clashes with the canon delay.

When strict results are weak, try `--engine repair` or install the solver extra and use `--engine solver`.
