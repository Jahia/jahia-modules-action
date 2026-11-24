import {zipSync} from 'fflate'

/** A jar with the given manifest, behind enough other entries to look like a module. */
export const jarOf = (manifest: string, others: Record<string, Uint8Array> = {}): Uint8Array =>
  zipSync({
    'META-INF/': new Uint8Array(),
    'org/jahia/Some.class': new Uint8Array(2000).fill(7),
    ...others,
    'META-INF/MANIFEST.MF': new TextEncoder().encode(manifest)
  })
