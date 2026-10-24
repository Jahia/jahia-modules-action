import { readFileSync, writeFileSync } from 'node:fs'

// Render the prompt template: every __PLACEHOLDER__ in `replacements` is substituted, and a
// placeholder left unreplaced is a build error — a prompt with a hole misleads the agent.
export const buildPrompt = ({ templatePath, outputPath, replacements }) => {
  const template = readFileSync(templatePath, 'utf8')
  const prompt = Object.entries(replacements).reduce(
    (text, [placeholder, value]) => text.replaceAll(`__${placeholder}__`, String(value)),
    template,
  )
  const leftover = prompt.match(/__[A-Z_]+__/)
  if (leftover) throw new Error(`prompt template placeholder not replaced: ${leftover[0]}`)
  writeFileSync(outputPath, prompt)
}
