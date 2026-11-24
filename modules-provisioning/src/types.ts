export type Http = (url: string, headers?: Record<string, string>) => Promise<Response>

export type Coordinate = {groupId: string; artifactId: string; version: string}

export type ReleaseModule = Coordinate & {pack: string; type?: 'js'; startLevel?: number}

export type Release = {packs: Record<string, number | null>; modules: ReleaseModule[]}

export type JahiaDependency = {module: string; version?: string; optional?: true}

export type ModuleVersion = {
  packaging?: 'jar' | 'tgz'
  moduleType?: string
  jahiaRequiredVersion?: string
  jahiaDepends?: JahiaDependency[]
  manifest?: Record<string, string>
  error?: string
}

export type StoreVersion = {requiredVersion: string; downloadUrl?: string}

export type StoreModule = {
  groupId: string
  artifactId: string
  title?: string
  status?: string
  versions: Record<string, StoreVersion>
}

export type Store = Record<string, StoreModule>

export type ProvisioningModule = ReleaseModule & {
  shippedVersion: string
  /** The version the Store offers the release, when it differs from the version of the script. */
  withheldVersion?: string
  mandatory: boolean
}

export type RemoteFile = {size: number; read: (start: number, end: number) => Promise<Uint8Array>}

export type VersionsMode = 'store' | 'shipped'

export type Inputs = {
  jahiaVersion: string
  versions: VersionsMode
  storeUrl: string
  nexusUsername: string
  nexusPassword: string
  provisioningPath: string
  matrixPath: string
}

export type Outputs = {provisioningPath: string; matrixPath: string; modules: number; upgraded: number}

export type Environment = {
  http: Http
  writeFile: (path: string, content: string) => Promise<void>
  now: () => Date
  log: (message: string) => void
}
