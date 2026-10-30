import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'
import {XMLParser} from 'fast-xml-parser'

// GitHub shows 10 error annotations per step, and the failure of the step takes the last one
const MAX_ANNOTATIONS = 9

interface Failure {
  message?: string
  '#text'?: string
}

interface TestCase {
  name: string
  failure?: (Failure | string)[]
}

interface TestSuite {
  file?: string
  testcase?: TestCase[]
}

interface Report {
  testsuites?: {testsuite?: TestSuite[]}
  testsuite?: TestSuite[]
}

export interface FailedTest {
  title: string
  message: string
  file?: string
  line?: number
}

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '',
  isArray: name => ['testsuite', 'testcase', 'failure'].includes(name)
})

// The failed tests of one JUnit report of mocha-junit-reporter, where the root suite alone names the spec file
export function readFailedTests(xml: string): FailedTest[] {
  const report: Report = parser.parse(xml)
  const suites = report.testsuites?.testsuite ?? report.testsuite ?? []
  const file = suites.find(suite => suite.file)?.file
  const failed: FailedTest[] = []
  for (const suite of suites) {
    for (const testcase of suite.testcase ?? []) {
      if (!testcase.failure) continue
      const failure =
        typeof testcase.failure[0] === 'string'
          ? {'#text': testcase.failure[0]}
          : testcase.failure[0]
      const stack = failure['#text'] ?? ''
      failed.push({
        title: testcase.name,
        message: failure.message || stack.split('\n')[0],
        file,
        line: file ? findLine(stack, file) : undefined
      })
    }
  }
  return failed
}

// The line of the last frame in the spec file, which is the line of the test itself
function findLine(stack: string, file: string): number | undefined {
  const escaped = file.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const frame = new RegExp(`${escaped}:(\\d+):\\d+`, 'g')
  let line: number | undefined
  for (let match = frame.exec(stack); match; match = frame.exec(stack)) {
    line = Number(match[1])
  }
  return line
}

function listReports(reportsPath: string): string[] {
  if (!fs.statSync(reportsPath).isDirectory()) return [reportsPath]
  const reports: string[] = []
  for (const name of fs.readdirSync(reportsPath).sort()) {
    const child = path.join(reportsPath, name)
    if (fs.statSync(child).isDirectory()) reports.push(...listReports(child))
    else if (name.endsWith('.xml')) reports.push(child)
  }
  return reports
}

// Writes one error annotation for each failed test, and returns the number of failed tests left without one.
// specFolder is the folder of the spec files, relative to the root of the repository.
export function annotateFailedTests(
  reportsPath: string,
  specFolder: string
): number {
  if (!fs.existsSync(reportsPath)) return 0
  const failed: FailedTest[] = []
  for (const report of listReports(reportsPath)) {
    try {
      failed.push(...readFailedTests(fs.readFileSync(report, 'utf8')))
    } catch (error) {
      // A report that does not parse must not stop the upload of the artifacts
      core.info(`Could not read the JUnit report ${report}: ${error}`)
    }
  }
  for (const test of failed.slice(0, MAX_ANNOTATIONS)) {
    core.error(test.message, {
      title: test.title,
      file: test.file ? path.join(specFolder, test.file) : undefined,
      startLine: test.line
    })
  }
  return Math.max(failed.length - MAX_ANNOTATIONS, 0)
}
