import type {Http} from '../types.js'
import {isAbsent} from './isAbsent.js'

/** The answer of the first repository that serves the path, or undefined when none does. */
export const fetchFirst = async (
  http: Http,
  repositories: string[],
  path: string
): Promise<Response | undefined> => {
  const [repository, ...others] = repositories
  if (repository === undefined) return undefined
  const response = await http(`${repository}/${path}`)
  if (response.ok) return response
  if (!isAbsent(response)) throw new Error(`${repository}/${path} answered HTTP ${response.status}`)
  return fetchFirst(http, others, path)
}
