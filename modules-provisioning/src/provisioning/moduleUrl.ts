import type {ProvisioningModule} from '../types.js'

/** The url Jahia's provisioning installs a module from: a JavaScript module is a js:mvn: tgz. */
export const moduleUrl = ({type, groupId, artifactId, version}: ProvisioningModule): string =>
  type === 'js' ? `js:mvn:${groupId}/${artifactId}/${version}/tgz` : `mvn:${groupId}/${artifactId}/${version}`
