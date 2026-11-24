import type {Http, RemoteFile} from '../types.js'
import {openRemoteFile} from './openRemoteFile.js'

/** The first of the URLs that names a file. */
export const openFirstRemoteFile = async (http: Http, urls: string[]): Promise<RemoteFile | undefined> => {
  const [url, ...others] = urls
  if (url === undefined) return undefined
  return (await openRemoteFile(http, url)) ?? openFirstRemoteFile(http, others)
}
