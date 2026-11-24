import type {Http} from '../types.js'
import {fetchFirst} from './fetchFirst.js'

export const fetchText = async (
  http: Http,
  repositories: string[],
  path: string
): Promise<string | undefined> => (await fetchFirst(http, repositories, path))?.text()
