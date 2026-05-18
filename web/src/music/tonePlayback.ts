import * as Tone from 'tone'
import type { PlaybackNote } from './time'
import { quarterSeconds } from './time'

export type TonePlaybackOptions = {
  positionQ: number
  tempoMultiplier: number
  onEnded: () => void
}

export class TonePlaybackController {
  private synth: Tone.PolySynth<Tone.Synth> | null = null
  private endTimer: number | null = null

  async play(notes: PlaybackNote[], options: TonePlaybackOptions): Promise<void> {
    this.stop()
    await Tone.start()
    const synth = this.getSynth()
    const secondsPerQuarter = quarterSeconds(options.tempoMultiplier)
    const now = Tone.now()
    let lastEndQ = options.positionQ

    for (const note of notes) {
      if (note.noteName === null || note.endQ <= options.positionQ) {
        continue
      }
      const startQ = Math.max(note.startQ, options.positionQ)
      const offsetSeconds = Math.max(0, note.startQ - options.positionQ) * secondsPerQuarter
      const durationSeconds = Math.max(0.05, (note.endQ - startQ) * secondsPerQuarter)
      synth.triggerAttackRelease(
        note.noteName,
        durationSeconds,
        now + offsetSeconds,
        note.velocity,
      )
      lastEndQ = Math.max(lastEndQ, note.endQ)
    }

    const remainingSeconds = Math.max(0, lastEndQ - options.positionQ) * secondsPerQuarter
    this.endTimer = window.setTimeout(options.onEnded, remainingSeconds * 1000 + 80)
  }

  pause(): void {
    this.stopTimer()
    this.synth?.releaseAll()
  }

  stop(): void {
    this.stopTimer()
    this.synth?.releaseAll()
  }

  dispose(): void {
    this.stop()
    this.synth?.dispose()
    this.synth = null
  }

  private getSynth(): Tone.PolySynth<Tone.Synth> {
    this.synth ??= new Tone.PolySynth(Tone.Synth, {
      envelope: {
        attack: 0.01,
        decay: 0.12,
        sustain: 0.45,
        release: 0.25,
      },
    }).toDestination()
    return this.synth
  }

  private stopTimer(): void {
    if (this.endTimer !== null) {
      window.clearTimeout(this.endTimer)
      this.endTimer = null
    }
  }
}
