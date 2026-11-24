import type {JahiaDependency} from '../types.js'
import {splitTopLevel} from './splitTopLevel.js'

/** Jahia-Depends: name[=version or range][;optional], comma separated. */
export const parseJahiaDepends = (value: string | undefined): JahiaDependency[] =>
  splitTopLevel(value ?? '').map(entry => {
    const equals = entry.indexOf('=')
    const [name = '', ...nameFlags] = (equals === -1 ? entry : entry.slice(0, equals)).split(';')
    const [version = '', ...versionFlags] = (equals === -1 ? '' : entry.slice(equals + 1)).split(';')
    const optional = [...nameFlags, ...versionFlags].some(flag => flag.trim() === 'optional')
    return {
      module: name.trim(),
      ...(version.trim() ? {version: version.trim()} : {}),
      ...(optional ? {optional: true as const} : {})
    }
  })
