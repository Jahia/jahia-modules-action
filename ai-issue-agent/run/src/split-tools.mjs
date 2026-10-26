// Split an --allowedTools/--disallowedTools value into { plain, shell }. Entries are
// comma-separated, but a `Bash(...)` entry may itself contain commas, so the split tracks
// parenthesis depth rather than calling String.split(',').
export const splitTools = (value) => {
  const entries = []
  let depth = 0
  let current = ''
  for (const char of value ?? '') {
    if (char === ',' && depth === 0) {
      entries.push(current.trim())
      current = ''
      continue
    }
    depth += (char === '(' ? 1 : 0) - (char === ')' ? 1 : 0)
    current += char
  }
  entries.push(current.trim())

  const plain = []
  const shell = []
  for (const entry of entries.filter(Boolean)) {
    const match = /^Bash\((.*)\)$/.exec(entry)
    if (match) {
      // `git log:*` and `git log *` both name the prefix `git log`. Any other `*` stays, as
      // the CLI reads it: `:**` and `-*` keep their meaning in the rendered prompt.
      shell.push(match[1].replace(/(:| )\*$/, '').trim())
    } else {
      plain.push(entry)
    }
  }
  return { plain, shell }
}
