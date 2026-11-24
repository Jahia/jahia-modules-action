import type {Http, Store} from '../types.js'
import {parseStore} from './parseStore.js'

export const readStore = async (http: Http, url: string): Promise<Store> => {
  const list = `${url.replace(/\/+$/, '')}/contents/modules-repository.moduleList.json`
  const response = await http(list)
  if (!response.ok) throw new Error(`${list} answered HTTP ${response.status}`)
  return parseStore(await response.text())
}
