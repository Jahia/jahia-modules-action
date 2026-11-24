import {expect, test} from 'vitest'
import {fakeHttp} from '../testing/fakeHttp.js'
import {readStore} from './readStore.js'

test('reads the module list of the Store', async () => {
  const http = fakeHttp({
    'https://store/site/contents/modules-repository.moduleList.json':
      '[{"modules":[{"groupId":"g","name":"a"}]}]'
  })
  expect(Object.keys(await readStore(http, 'https://store/site/'))).toEqual(['g:a'])
})

test('fails when the Store does not answer the list', async () => {
  await expect(readStore(fakeHttp({}), 'https://store/site')).rejects.toThrow('answered HTTP 404')
})
