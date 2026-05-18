import createVerovioModule from 'verovio/wasm'
import { VerovioToolkit } from 'verovio/esm'
import type { ScoreRenderer, ScoreRenderOptions, ScoreRenderResult } from './scoreRenderer'

type VerovioToolkitInstance = {
  setOptions?: (options: Record<string, unknown>) => void
  loadData: (data: string) => boolean | number | void
  redoLayout?: () => void
  getPageCount?: () => number
  renderToSVG: (page: number, options?: Record<string, unknown>) => string
}

let toolkitPromise: Promise<VerovioToolkitInstance> | null = null

export class VerovioScoreRenderer implements ScoreRenderer {
  async renderMusicXml(
    musicXml: string,
    options: ScoreRenderOptions,
  ): Promise<ScoreRenderResult> {
    const toolkit = await getToolkit()
    toolkit.setOptions?.({
      adjustPageHeight: true,
      breaks: 'auto',
      pageHeight: 1600,
      pageWidth: 1200,
      scale: options.scale,
    })

    const loaded = toolkit.loadData(musicXml)
    if (loaded === false || loaded === 0) {
      throw new Error('Verovio could not load this MusicXML file.')
    }
    toolkit.redoLayout?.()

    const pageCount = Math.max(1, toolkit.getPageCount?.() ?? 1)
    const page = Math.min(Math.max(options.page, 1), pageCount)
    const svg = toolkit.renderToSVG(page, {})
    if (svg.trim() === '') {
      throw new Error('Verovio returned an empty SVG.')
    }
    return { svg, page, pageCount }
  }
}

export const defaultScoreRenderer = new VerovioScoreRenderer()

async function getToolkit(): Promise<VerovioToolkitInstance> {
  toolkitPromise ??= createVerovioModule().then((module) => {
    return new VerovioToolkit(module) as VerovioToolkitInstance
  })
  return toolkitPromise
}
