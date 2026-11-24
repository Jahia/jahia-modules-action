import type {ReleaseModule} from '../types.js'

const URL = /url:\s*['"]?(js:)?mvn:([^/'"\s]+)\/([^/'"\s]+)\/([^/'"\s]+)/
const START_LEVEL = /startLevel:\s*(\d+)/

/**
 * The modules of the provisioning YAML of a pack: an url line opens a module, and a startLevel line
 * under it belongs to it. A JavaScript module is a js:mvn: url.
 */
export const parsePackProvisioning = (text: string, pack: string): ReleaseModule[] =>
  text.split('\n').reduce<ReleaseModule[]>((modules, line) => {
    const url = URL.exec(line)
    if (url) {
      const [, js, groupId = '', artifactId = '', version = ''] = url
      return [...modules, {groupId, artifactId, version, pack, ...(js ? {type: 'js' as const} : {})}]
    }
    const startLevel = START_LEVEL.exec(line)
    const last = modules.at(-1)
    return startLevel && last
      ? [...modules.slice(0, -1), {...last, startLevel: Number(startLevel[1])}]
      : modules
  }, [])
