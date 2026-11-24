/**
 * The modules whose update the module manager never offers: the non-manageable modules a release
 * ships, and each module they depend on, through every level of Jahia-Depends. The page of the
 * module manager marks them "mandatory system dependency".
 */
export const mandatoryModules = (
  dependencies: Record<string, string[]>,
  roots: string[],
  found: ReadonlySet<string> = new Set()
): ReadonlySet<string> => {
  const reached = roots.filter(root => root in dependencies && !found.has(root))
  if (reached.length === 0) return found
  return mandatoryModules(
    dependencies,
    reached.flatMap(root => dependencies[root] ?? []),
    new Set([...found, ...reached])
  )
}
