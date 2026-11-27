import { readFileSync, writeFileSync } from 'node:fs'

// Render the prompt template: every __PLACEHOLDER__ in `replacements` is substituted, and a
// placeholder left unreplaced is a build error — a prompt with a hole misleads the agent.
// `literal` holds text that comes from a person or a dispatcher (the dispatched request): it
// is substituted last and never scanned, so a `__NAME__` or a `$&` inside it stays as written.
// A function replacer keeps `$` in a value from being read as a replacement pattern.
export const buildPrompt = ({ templatePath, outputPath, replacements, literal = {} }) => {
  const template = readFileSync(templatePath, 'utf8')
  const substituted = Object.entries(replacements).reduce(
    (text, [placeholder, value]) => text.replaceAll(`__${placeholder}__`, () => String(value)),
    template,
  )
  const leftover = [...substituted.matchAll(/__[A-Z_]+__/g)].find(
    ([name]) => !Object.hasOwn(literal, name.slice(2, -2)),
  )
  if (leftover) throw new Error(`prompt template placeholder not replaced: ${leftover[0]}`)
  const prompt = Object.entries(literal).reduce(
    (text, [placeholder, value]) => text.replaceAll(`__${placeholder}__`, () => String(value)),
    substituted,
  )
  writeFileSync(outputPath, prompt)
}
