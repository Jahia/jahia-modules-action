import {ENTERPRISE_REPOSITORY, PUBLIC_REPOSITORY} from './constants.js'

/** The Maven repositories read, in order: the enterprise group needs the Nexus account. */
export const repositories = (username: string, password: string): string[] =>
  username && password ? [ENTERPRISE_REPOSITORY, PUBLIC_REPOSITORY] : [PUBLIC_REPOSITORY]
