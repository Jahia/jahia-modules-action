import {expect, test} from 'vitest'
import {parseStore} from './parseStore.js'

test('keys the modules and strips the prefix of the required version', () => {
  const store = parseStore(
    JSON.stringify([
      {
        modules: [
          {
            groupId: 'org.jahia.modules',
            name: 'jcontent',
            title: 'jContent',
            status: 'supported',
            versions: [
              {
                version: '3.8.1',
                requiredVersion: 'version-8.2.1.0',
                downloadUrl: 'https://store/jcontent.jar'
              }
            ]
          },
          {groupId: 'org.acme', name: 'bare'}
        ]
      }
    ])
  )
  expect(store).toEqual({
    'org.jahia.modules:jcontent': {
      groupId: 'org.jahia.modules',
      artifactId: 'jcontent',
      title: 'jContent',
      status: 'supported',
      versions: {'3.8.1': {requiredVersion: '8.2.1.0', downloadUrl: 'https://store/jcontent.jar'}}
    },
    'org.acme:bare': {
      groupId: 'org.acme',
      artifactId: 'bare',
      title: undefined,
      status: undefined,
      versions: {}
    }
  })
  expect(parseStore('[]')).toEqual({})
})
