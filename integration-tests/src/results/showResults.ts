import * as path from 'path'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

export async function showResults(testsPath: string): Promise<any> {
  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')

  if (!fs.existsSync(reportsPath)) {
    return
  }

  const files = fs.readdirSync(reportsPath).sort()
  const commands = []
  for (const f of files) {
    if (f.includes('.xml')) {
      commands.push(
        `junit-cli-report-viewer ${path.join(
          reportsPath,
          f
        )} | grep -v ">" | grep -v "Root Suite"`
      )
    }
  }

  await runShellCommands(commands)
}
