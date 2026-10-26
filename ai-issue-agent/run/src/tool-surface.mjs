import { splitTools } from './split-tools.mjs'

// Render the agent's tool surface from the very strings the run passes to the CLI, so the
// prompt and the flags cannot drift apart. The agent works from inside the cortex harness,
// whose CLAUDE.md mandates routes (gh through gh-wrapper, no cd) this allowlist may or may
// not carry; a headless agent that guesses wrong reads a denial as "the tool is gone".
export const renderToolSurface = (allowedTools, disallowedTools) => {
  const allowed = splitTools(allowedTools)
  const denied = splitTools(disallowedTools)
  const bullets = (commands) => commands.map((command) => `  - \`${command}\``)

  const lines = [
    'You run under an allowlist. A refusal is FINAL: it does not mean the tool is missing,',
    'and there is no way around it — a denied call means "use another route from this list".',
    'Never spend turns probing the permission surface; it is stated here in full.',
    '',
    '**You may use:**',
    '',
  ]
  if (allowed.plain.length) lines.push(`- Tools: ${allowed.plain.join(', ')}.`)
  lines.push(
    '- These shell commands, and NOTHING else. Each entry is a command prefix — any',
    '  arguments are allowed after it:',
    ...bullets(allowed.shell),
    '- A pipeline or a `;`-chain runs only when EVERY command in it is allowed:',
    '  `gh issue view … | head -200` works, `… | jq …` and `… | python3 -c …` do not.',
    '',
    '**Denied — never retry these, in any spelling:**',
    '',
  )
  if (denied.plain.length) lines.push(`- Tools: ${denied.plain.join(', ')}.`)
  lines.push(
    '- These shell commands:',
    ...bullets(denied.shell),
    '',
    'Two consequences of working from inside the cortex harness, whose CLAUDE.md you have',
    'also been given. On these two points THIS section wins — it is what the CLI enforces:',
    '',
    '- cortex routes every `gh` write through `tools/gh-wrapper/bin/gh-wrapper`, and the list',
    '  above carries the reads under both gh spellings but the writes under the wrapper alone:',
    '  `issue comment`, `issue edit`, `pr edit` and `pr comment`.',
    '- cortex denies `cd`, and it is not on the list above, so a directory is reached by',
    '  naming it: Read, Grep and Glob all take an absolute path. git takes none here —',
    '  `git -C` is not on the list, and `tools/jahia-pr/bin/jahia-pr` commits and pushes',
    '  in the worktree for you (`open` for a new pull request, `push` to iterate on one).',
  )
  return lines.join('\n')
}
