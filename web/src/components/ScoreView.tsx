import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, Box, Button, Group, Loader, Stack, Text } from '@mantine/core'
import { fetchCandidateMusicXml } from '../api/artifacts'
import type { CandidateViz, ViolationViz } from '../api/schemas'
import type { ScoreRenderer, ScoreRenderResult } from '../music/scoreRenderer'
import { defaultScoreRenderer } from '../music/verovioScoreRenderer'

type ScoreViewProps = {
  runId: string | null
  candidate: CandidateViz | null
  selectedViolation: ViolationViz | null
  renderer?: ScoreRenderer
}

export function ScoreView({
  runId,
  candidate,
  selectedViolation,
  renderer = defaultScoreRenderer,
}: ScoreViewProps) {
  const [page, setPage] = useState(1)
  const [scale, setScale] = useState(40)
  const [renderResult, setRenderResult] = useState<ScoreRenderResult | null>(null)
  const [renderError, setRenderError] = useState<string | null>(null)
  const candidateId = candidate?.candidate_id ?? null

  const musicXmlQuery = useQuery({
    queryKey: ['candidate-musicxml', runId, candidateId],
    enabled: runId !== null && candidateId !== null,
    queryFn: () => fetchCandidateMusicXml(runId as string, candidateId as string),
    retry: false,
  })

  useEffect(() => {
    if (musicXmlQuery.data === undefined) {
      return
    }

    let active = true
    void renderer
      .renderMusicXml(musicXmlQuery.data, { page, scale })
      .then((result) => {
        if (!active) {
          return
        }
        setRenderResult(result)
        setRenderError(null)
        if (result.page !== page) {
          setPage(result.page)
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return
        }
        setRenderResult(null)
        setRenderError(error instanceof Error ? error.message : 'Score rendering failed.')
      })

    return () => {
      active = false
    }
  }, [musicXmlQuery.data, page, renderer, scale])

  if (candidate === null || runId === null) {
    return (
      <Alert color="gray" variant="light" title="No score">
        No candidate selected.
      </Alert>
    )
  }

  if (musicXmlQuery.isLoading) {
    return (
      <Group className="score-loading" gap="sm">
        <Loader size="sm" />
        <Text size="sm" c="dimmed">
          Loading MusicXML
        </Text>
      </Group>
    )
  }

  if (musicXmlQuery.isError) {
    return (
      <Alert color="red" variant="light" title="MusicXML unavailable">
        {readableError(musicXmlQuery.error)}
      </Alert>
    )
  }

  if (renderError !== null) {
    return (
      <Alert color="red" variant="light" title="Score rendering failed">
        {renderError}
      </Alert>
    )
  }

  return (
    <Stack gap="sm">
      {selectedViolation !== null ? (
        <Alert color="blue" variant="light" title="Score target">
          Bar {selectedViolation.bar ?? '-'} / Beat {selectedViolation.beat?.text ?? '-'}
        </Alert>
      ) : null}
      <Group justify="space-between" gap="sm">
        <Group gap="xs">
          <Button
            variant="light"
            size="xs"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Prev
          </Button>
          <Button
            variant="light"
            size="xs"
            disabled={renderResult === null || page >= renderResult.pageCount}
            onClick={() =>
              setPage((current) =>
                renderResult === null ? current : Math.min(renderResult.pageCount, current + 1),
              )
            }
          >
            Next
          </Button>
          <Text size="sm" c="dimmed">
            Page {renderResult?.page ?? page} / {renderResult?.pageCount ?? '-'}
          </Text>
        </Group>
        <Group gap="xs">
          <Button
            variant="light"
            size="xs"
            disabled={scale <= 25}
            onClick={() => setScale((current) => Math.max(25, current - 5))}
          >
            Zoom -
          </Button>
          <Text size="sm" c="dimmed">
            {scale}%
          </Text>
          <Button
            variant="light"
            size="xs"
            disabled={scale >= 100}
            onClick={() => setScale((current) => Math.min(100, current + 5))}
          >
            Zoom +
          </Button>
        </Group>
      </Group>
      <Box className="score-svg-surface">
        {renderResult === null ? (
          <Group className="score-loading" gap="sm">
            <Loader size="sm" />
            <Text size="sm" c="dimmed">
              Rendering score
            </Text>
          </Group>
        ) : (
          <Box
            className="score-svg"
            data-testid="score-view-svg"
            dangerouslySetInnerHTML={{ __html: renderResult.svg }}
          />
        )}
      </Box>
    </Stack>
  )
}

function readableError(error: Error): string {
  return error.message || 'The score artifact could not be loaded.'
}
