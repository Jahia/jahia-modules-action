type State = {parts: string[]; current: string; depth: number}

/** Split on the separator outside brackets, since a version range such as [1.0,2.0) holds a comma. */
export const splitTopLevel = (value: string, separator = ','): string[] => {
  const {parts, current} = [...value].reduce<State>(
    (state, char) => {
      const depth = state.depth + ('[('.includes(char) ? 1 : 0) - ('])'.includes(char) ? 1 : 0)
      return char === separator && depth === 0
        ? {parts: [...state.parts, state.current], current: '', depth}
        : {parts: state.parts, current: state.current + char, depth}
    },
    {parts: [], current: '', depth: 0}
  )
  return [...parts, current].map(part => part.trim()).filter(Boolean)
}
