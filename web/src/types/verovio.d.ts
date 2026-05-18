declare module 'verovio/wasm' {
  const createVerovioModule: () => Promise<unknown>
  export default createVerovioModule
}

declare module 'verovio/esm' {
  export class VerovioToolkit {
    constructor(module: unknown)
    setOptions(options: Record<string, unknown>): void
    loadData(data: string): boolean | number | void
    redoLayout(): void
    getPageCount(): number
    renderToSVG(page: number, options?: Record<string, unknown>): string
  }
}
