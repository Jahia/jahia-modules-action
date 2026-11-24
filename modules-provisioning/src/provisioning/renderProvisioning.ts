import type {ProvisioningModule, VersionsMode} from '../types.js'
import {moduleComment} from './moduleComment.js'
import {moduleUrl} from './moduleUrl.js'

type Options = {jahiaVersion: string; versions: VersionsMode; storeUrl: string; generatedAt: string}

/** The provisioning script: one installOrUpgradeBundle block that Jahia's provisioning reads. */
export const renderProvisioning = (
  modules: ProvisioningModule[],
  {jahiaVersion, versions, storeUrl, generatedAt}: Options
): string =>
  [
    `# Jahia ${jahiaVersion}: the ${modules.length} modules it ships, each at ` +
      (versions === 'store'
        ? 'the version its module manager offers from the Store.'
        : 'the version it ships.'),
    ...(versions === 'store'
      ? [
          `# ${modules.filter(module => module.version !== module.shippedVersion).length} of them are newer than shipped. Store: ${storeUrl}`
        ]
      : []),
    `# Generated on ${generatedAt} by jahia-modules-action/modules-provisioning.`,
    '- installOrUpgradeBundle:',
    ...modules.flatMap(module => [
      `    - url: '${moduleUrl(module)}'${moduleComment(module)}`,
      ...(module.startLevel === undefined ? [] : [`      startLevel: ${module.startLevel}`])
    ]),
    '  autoStart: true',
    ''
  ].join('\n')
