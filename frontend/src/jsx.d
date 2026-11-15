/** Fallback so JSX tags type-check when @types/react is unavailable or
 * react/jsx-runtime cannot be resolved in this toolchain. Safe no-op when the
 * real React types ARE present (interface merging). */
declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}
export {};