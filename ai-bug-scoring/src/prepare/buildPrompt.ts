// Render the prompt template: every __PLACEHOLDER__ is substituted, and a placeholder left
// unreplaced is a build error — a prompt with a hole misleads the agent.
export const buildPrompt = (template: string, replacements: Record<string, string>): string => {
  const prompt = Object.entries(replacements).reduce(
    (text, [placeholder, value]) => text.replaceAll(`__${placeholder}__`, value),
    template,
  )
  const leftover = /__[A-Z_]+__/.exec(prompt)
  if (leftover) throw new Error(`prompt template placeholder not replaced: ${leftover[0]}`)
  return prompt
}
