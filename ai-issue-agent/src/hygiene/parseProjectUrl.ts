// Only organization projects are supported — the board this duty targets is one.
export const parseProjectUrl = (url: string): { org: string; number: number } => {
  const match = /github\.com\/orgs\/([^/]+)\/projects\/(\d+)/.exec(url)
  if (!match?.[1] || !match[2]) {
    throw new Error(`not an organization project URL: ${url}`)
  }
  return { org: match[1], number: Number(match[2]) }
}
