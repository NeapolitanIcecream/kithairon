export type ScoreRenderOptions = {
  page: number
  scale: number
}

export type ScoreRenderResult = {
  svg: string
  page: number
  pageCount: number
}

export type ScoreRenderer = {
  renderMusicXml: (
    musicXml: string,
    options: ScoreRenderOptions,
  ) => Promise<ScoreRenderResult>
}
