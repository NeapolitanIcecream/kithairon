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
  private playbackVersion = 0

  async play(notes: PlaybackNote[], options: TonePlaybackOptions): Promise<boolean> {
    const playbackVersion = this.cancelPlayback()
    await Tone.start()
    if (playbackVersion !== this.playbackVersion) {
      return false
    }
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
    return true
  }

  pause(): void {
    this.cancelPlayback()
  }

  stop(): void {
    this.cancelPlayback()
  }

  dispose(): void {
    this.cancelPlayback()
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

  private cancelPlayback(): number {
    this.playbackVersion += 1
    this.stopTimer()
    const synth = this.synth
    if (synth === null) {
      return this.playbackVersion
    }
    synth.releaseAll()
    synth.dispose()
    this.synth = null
    return this.playbackVersion
  }
}
