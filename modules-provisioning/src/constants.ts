export const NEXUS = 'https://devtools.jahia.com/nexus/content'
export const PUBLIC_REPOSITORY = `${NEXUS}/groups/public`
export const ENTERPRISE_REPOSITORY = `${NEXUS}/groups/enterprise`
export const STORE_PROXY = 'https://store.jahia.com/modules/mavenproxy/store'
export const PACKS_GROUP = 'org.jahia.packages'
export const PACKS = ['jahia-core-modules', 'jahia-additional-modules', 'jahia-ee-core-modules']
export const MANIFEST_KEYS = [
  'Bundle-SymbolicName',
  'Bundle-Version',
  'Jahia-Required-Version',
  'Jahia-Depends',
  'Jahia-Module-Type',
  'Jahia-Source-Control-Connection'
]
/**
 * The modules Jahia core names in `nonManageableModules` of applicationcontext-services.xml, the
 * same list from 8.1 to 8.2. The module manager offers no update of them, nor of what they depend on.
 */
export const NON_MANAGEABLE_MODULES = [
  'templates-system',
  'serverSettings',
  'serverSettings-ee',
  'siteSettings',
  'app-shell',
  'jahia-ui-root',
  'jahia-administration'
]
export const CONCURRENCY = 8
export const ZIP_TAIL = 64 * 1024
