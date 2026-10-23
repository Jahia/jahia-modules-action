// Trim + case-insensitive: board option names carry emoji and stray spaces, and a rename
// that only changes casing must not break the hygiene run.
export const pickOption = (
  options: readonly { id: string; name: string }[],
  wanted: string,
): string | null => {
  const target = wanted.trim().toLowerCase()
  const found = options.find((option) => option.name.trim().toLowerCase() === target)
  return found ? found.id : null
}
