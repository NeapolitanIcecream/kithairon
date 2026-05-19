import { useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react'
import { Alert, Button, Group, Slider, Stack, Text } from '@mantine/core'
import type { CandidateViz } from '../api/schemas'
import { TonePlaybackController } from '../music/tonePlayback'
import {
  activeEventIdsAt,
  durationQ,
  playbackNotesFromViz,
  quarterSeconds,
} from '../music/time'

type PlaybackControlsProps = {
  candidate: CandidateViz | null
  onActiveEventIdsChange: (eventIds: string[]) => void
}

export function PlaybackControls({ candidate, onActiveEventIdsChange }: PlaybackControlsProps) {
  const controllerRef = useRef<TonePlaybackController | null>(null)
  const clockRef = useRef<{ startedAt: number; startPositionQ: number; tempo: number } | null>(
    null,
  )
  const frameRef = useRef<number | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [positionQ, setPositionQ] = useState(0)
  const [tempoMultiplier, setTempoMultiplier] = useState(1)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  if (controllerRef.current === null) {
    controllerRef.current = new TonePlaybackController()
  }
  const notes = useMemo(() => playbackNotesFromViz(candidate?.notes ?? []), [candidate])
  const totalDuration = durationQ(notes)

  useEffect(() => {
    const controller = controllerRef.current
    return () => {
      stopClock(frameRef)
      controller?.dispose()
      onActiveEventIdsChange([])
    }
  }, [onActiveEventIdsChange])

  if (candidate === null) {
    return (
      <Alert color="gray" variant="light" title="No playback">
        No candidate selected.
      </Alert>
    )
  }

  const play = async (startPositionQ = positionQ, tempo = tempoMultiplier) => {
    const controller = controllerRef.current
    if (controller === null) {
      return
    }
    stopClock(frameRef)
    try {
      const playbackStarted = await controller.play(notes, {
        positionQ: startPositionQ,
        tempoMultiplier: tempo,
        onEnded: () => {
          stopClock(frameRef)
          setIsPlaying(false)
          setPositionQ(totalDuration)
          onActiveEventIdsChange([])
        },
      })
      if (!playbackStarted) {
        return
      }
      clockRef.current = {
        startedAt: performance.now(),
        startPositionQ,
        tempo,
      }
      setIsPlaying(true)
      setErrorMessage(null)
      startClock({
        frameRef,
        clockRef,
        notes,
        totalDuration,
        setPositionQ,
        setIsPlaying,
        onActiveEventIdsChange,
      })
    } catch (error) {
      setIsPlaying(false)
      setErrorMessage(error instanceof Error ? error.message : 'Playback failed.')
      onActiveEventIdsChange([])
    }
  }

  const pause = () => {
    const nextPosition = currentPosition(clockRef.current, totalDuration)
    controllerRef.current?.pause()
    stopClock(frameRef)
    setPositionQ(nextPosition)
    setIsPlaying(false)
    onActiveEventIdsChange(activeEventIdsAt(notes, nextPosition))
  }

  const stop = () => {
    controllerRef.current?.stop()
    stopClock(frameRef)
    setPositionQ(0)
    setIsPlaying(false)
    onActiveEventIdsChange([])
  }

  const seek = async (value: number) => {
    const nextPosition = Math.min(totalDuration, Math.max(0, value))
    setPositionQ(nextPosition)
    onActiveEventIdsChange(activeEventIdsAt(notes, nextPosition))
    if (isPlaying) {
      await play(nextPosition)
    }
  }

  const changeTempo = async (value: number) => {
    const nextTempo = Math.min(2, Math.max(0.5, value))
    setTempoMultiplier(nextTempo)
    if (isPlaying) {
      await play(positionQ, nextTempo)
    }
  }

  return (
    <Stack gap="sm">
      <Group justify="space-between" gap="sm">
        <Group gap="xs">
          <Button size="xs" variant="light" onClick={() => void play()} disabled={isPlaying}>
            Play
          </Button>
          <Button size="xs" variant="light" onClick={pause} disabled={!isPlaying}>
            Pause
          </Button>
          <Button size="xs" variant="light" onClick={stop}>
            Stop
          </Button>
        </Group>
        <Text size="sm" c="dimmed">
          {positionQ.toFixed(2)} / {totalDuration.toFixed(2)}
        </Text>
      </Group>
      <Slider
        min={0}
        max={Math.max(0, totalDuration)}
        step={0.25}
        value={Math.min(positionQ, totalDuration)}
        label={(value) => value.toFixed(2)}
        onChange={(value) => void seek(value)}
        disabled={totalDuration <= 0}
      />
      <Group gap="sm" align="center">
        <Text size="sm" c="dimmed">
          Tempo
        </Text>
        <Slider
          className="tempo-slider"
          min={0.5}
          max={2}
          step={0.25}
          value={tempoMultiplier}
          label={(value) => `${value.toFixed(2)}x`}
          onChange={(value) => void changeTempo(value)}
        />
        <Text size="sm" c="dimmed">
          {tempoMultiplier.toFixed(2)}x
        </Text>
      </Group>
      {errorMessage !== null ? (
        <Alert color="red" variant="light" title="Playback failed">
          {errorMessage}
        </Alert>
      ) : null}
    </Stack>
  )
}

function startClock({
  frameRef,
  clockRef,
  notes,
  totalDuration,
  setPositionQ,
  setIsPlaying,
  onActiveEventIdsChange,
}: {
  frameRef: MutableRefObject<number | null>
  clockRef: MutableRefObject<{
    startedAt: number
    startPositionQ: number
    tempo: number
  } | null>
  notes: ReturnType<typeof playbackNotesFromViz>
  totalDuration: number
  setPositionQ: (positionQ: number) => void
  setIsPlaying: (isPlaying: boolean) => void
  onActiveEventIdsChange: (eventIds: string[]) => void
}) {
  const tick = () => {
    const nextPosition = currentPosition(clockRef.current, totalDuration)
    setPositionQ(nextPosition)
    onActiveEventIdsChange(activeEventIdsAt(notes, nextPosition))
    if (nextPosition >= totalDuration) {
      setIsPlaying(false)
      onActiveEventIdsChange([])
      frameRef.current = null
      return
    }
    frameRef.current = window.requestAnimationFrame(tick)
  }
  frameRef.current = window.requestAnimationFrame(tick)
}

function stopClock(frameRef: MutableRefObject<number | null>) {
  if (frameRef.current !== null) {
    window.cancelAnimationFrame(frameRef.current)
    frameRef.current = null
  }
}

function currentPosition(
  clock: { startedAt: number; startPositionQ: number; tempo: number } | null,
  totalDuration: number,
): number {
  if (clock === null) {
    return 0
  }
  const elapsedSeconds = (performance.now() - clock.startedAt) / 1000
  return Math.min(totalDuration, clock.startPositionQ + elapsedSeconds / quarterSeconds(clock.tempo))
}
