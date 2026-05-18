declare module 'd3-scale' {
  export type ScaleLinear = {
    (value: number): number
    domain(domain: [number, number]): ScaleLinear
    range(range: [number, number]): ScaleLinear
    clamp(enabled: boolean): ScaleLinear
    ticks(count?: number): number[]
    invert(value: number): number
  }

  export function scaleLinear(): ScaleLinear
}
