import {NEXUS} from '../constants.js'
import type {Http} from '../types.js'
import {basicAuthorization} from './basicAuthorization.js'
import {withRetry} from './withRetry.js'

type Options = {
  fetch: typeof globalThis.fetch
  username?: string
  password?: string
  attempts?: number
  wait?: (milliseconds: number) => Promise<void>
}

/**
 * The one way out to the network. The Nexus credentials go to Nexus only, never to the Store or its
 * proxy. A server error or a network failure is tried again, and any other status goes to the caller.
 */
export const createHttp =
  ({
    fetch,
    username,
    password,
    attempts = 3,
    wait = ms => new Promise(resolve => setTimeout(resolve, ms))
  }: Options): Http =>
  (url, headers = {}) =>
    withRetry(
      async () => {
        const response = await fetch(encodeURI(decodeURI(url)), {
          headers: {
            'User-Agent': 'jahia-modules-provisioning',
            ...(username && password && url.startsWith(`${NEXUS}/`)
              ? {Authorization: basicAuthorization(username, password)}
              : {}),
            ...headers
          }
        })
        if (response.status >= 500) throw new Error(`${url} answered HTTP ${response.status}`)
        return response
      },
      attempts,
      wait
    )
