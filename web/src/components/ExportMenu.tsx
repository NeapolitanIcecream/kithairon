import type { ReactNode } from 'react'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Alert, Button, Group, Stack, Text } from '@mantine/core'
import { ApiClientError } from '../api/client'
import {
  candidateArtifactUrl,
  renderCandidateArtifacts,
  runArtifactUrl,
  type RenderFormat,
} from '../api/artifacts'
import type { CandidateViz, RunSummary } from '../api/schemas'

type ExportMenuProps = {
  runSummary: RunSummary | null
  candidate: CandidateViz | null
}

const renderFormats: RenderFormat[] = ['pdf', 'svg', 'png']

export function ExportMenu({ runSummary, candidate }: ExportMenuProps) {
  const [renderedFormats, setRenderedFormats] = useState<RenderFormat[]>([])
  const renderMutation = useMutation({
    mutationFn: (format: RenderFormat) => {
      if (runSummary === null || candidate === null) {
        throw new Error('No candidate selected.')
      }
      return renderCandidateArtifacts(runSummary.run_id, candidate.candidate_id, [format])
    },
    onSuccess: (payload) => {
      setRenderedFormats((current) =>
        Array.from(new Set([...current, ...Object.keys(payload.artifacts)])) as RenderFormat[],
      )
    },
  })

  if (runSummary === null || candidate === null) {
    return (
      <Alert color="gray" variant="light" title="No exports">
        No candidate selected.
      </Alert>
    )
  }

  return (
    <Stack className="export-menu" gap="sm">
      <Text className="surface-title">Exports</Text>
      <Group gap="xs">
        <DownloadButton href={candidateArtifactUrl(runSummary.run_id, candidate.candidate_id, 'midi')}>
          MIDI
        </DownloadButton>
        <DownloadButton
          href={candidateArtifactUrl(runSummary.run_id, candidate.candidate_id, 'musicxml')}
        >
          MusicXML
        </DownloadButton>
        <DownloadButton href={runArtifactUrl(runSummary.run_id, 'report')}>Report</DownloadButton>
        <DownloadButton href={runArtifactUrl(runSummary.run_id, 'results')}>Results</DownloadButton>
        <DownloadButton href={runArtifactUrl(runSummary.run_id, 'visualization')}>
          Visualization JSON
        </DownloadButton>
      </Group>
      <Group gap="xs">
        {renderFormats.map((format) => (
          <Button
            key={format}
            size="xs"
            variant="light"
            loading={renderMutation.isPending && renderMutation.variables === format}
            onClick={() => renderMutation.mutate(format)}
          >
            Render {format.toUpperCase()}
          </Button>
        ))}
      </Group>
      {renderedFormats.length > 0 ? (
        <Group gap="xs">
          {renderedFormats.map((format) => (
            <DownloadButton
              key={format}
              href={candidateArtifactUrl(runSummary.run_id, candidate.candidate_id, format)}
            >
              Download {format.toUpperCase()}
            </DownloadButton>
          ))}
        </Group>
      ) : null}
      {renderMutation.error !== null ? (
        <Alert color="red" variant="light" title="Render failed">
          {readableError(renderMutation.error)}
        </Alert>
      ) : null}
    </Stack>
  )
}

function DownloadButton({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Button component="a" href={href} download size="xs" variant="light">
      {children}
    </Button>
  )
}

function readableError(error: Error): string {
  if (error instanceof ApiClientError) {
    return error.message
  }
  return error.message || 'Export failed.'
}
