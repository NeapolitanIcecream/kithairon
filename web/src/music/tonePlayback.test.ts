// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlaybackNote } from './time'

const toneMock = vi.hoisted(() => {
  const audibleAttacks: string[] = []

  class MockSynth {}

  class MockPolySynth {
    static instances: MockPolySynth[] = []

    disposed = false
    releaseAll = vi.fn()
    dispose = vi.fn(() => {
      this.disposed = true
    })
    triggerAttackRelease = vi.fn((noteName: string, _duration: number, time: number) => {
      const delayMs = Math.max(0, (time - toneMock.now()) * 1000)
      window.setTimeout(() => {
        if (!this.disposed) {
          audibleAttacks.push(noteName)
        }
      }, delayMs)
    })

    constructor() {
      MockPolySynth.instances.push(this)
    }

    toDestination() {
      return this
    }
  }

  return {
    audibleAttacks,
    now: vi.fn<() => number>(() => 10),
    start: vi.fn<() => Promise<void>>(async () => undefined),
    Synth: MockSynth,
    PolySynth: MockPolySynth,
  }
})

vi.mock('tone', () => toneMock)

import { TonePlaybackController } from './tonePlayback'

describe('TonePlaybackController', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    toneMock.audibleAttacks.length = 0
    toneMock.PolySynth.instances.length = 0
    toneMock.now.mockReturnValue(10)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('stops queued future notes before they can sound', async () => {
    const controller = new TonePlaybackController()

    await controller.play(notesWithFutureEvent(), playbackOptions())
    await vi.advanceTimersByTimeAsync(0)
    controller.stop()
    await vi.advanceTimersByTimeAsync(2500)

    expect(toneMock.audibleAttacks).toEqual(['C4'])
  })

  it('cancels queued notes from the previous playback before replaying', async () => {
    const controller = new TonePlaybackController()

    await controller.play(notesWithFutureEvent(), playbackOptions())
    await vi.advanceTimersByTimeAsync(0)
    await controller.play([note('E4', 0, 1)], playbackOptions())
    await vi.advanceTimersByTimeAsync(2500)

    expect(toneMock.audibleAttacks).toEqual(['C4', 'E4'])
  })

  it('does not start playback after it is stopped during audio startup', async () => {
    const controller = new TonePlaybackController()
    let resolveAudioStart: () => void = () => undefined
    toneMock.start.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveAudioStart = resolve
        }),
    )

    const started = controller.play(notesWithFutureEvent(), playbackOptions())
    controller.stop()
    resolveAudioStart()
    await vi.advanceTimersByTimeAsync(2500)

    await expect(started).resolves.toBe(false)
    expect(toneMock.audibleAttacks).toEqual([])
  })
})

function playbackOptions() {
  return {
    positionQ: 0,
    tempoMultiplier: 1,
    onEnded: vi.fn(),
  }
}

function notesWithFutureEvent(): PlaybackNote[] {
  return [note('C4', 0, 1), note('D4', 4, 5)]
}

function note(noteName: string, startQ: number, endQ: number): PlaybackNote {
  return {
    eventId: noteName,
    pitch: 60,
    noteName,
    startQ,
    durationQ: endQ - startQ,
    endQ,
    velocity: 0.75,
  }
}
