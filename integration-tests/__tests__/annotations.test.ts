import * as core from '@actions/core'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import {expect, jest, test} from '@jest/globals'

import {
  annotateFailedTests,
  readFailedTests
} from '../src/jahia-reporter/annotations'

// Cut from the report of Jahia/content-versioning, run 40911919756
const REPORT = `<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Mocha Tests" time="462.282" tests="3" failures="2">
  <testsuite name="Root Suite" tests="0" file="cypress/e2e/jcontent/versionCopyField.cy.ts" failures="0">
  </testsuite>
  <testsuite name="Version history" tests="3" failures="2">
    <testcase name="Version history offers the arrow" time="0.000" classname="offers the arrow">
      <failure message="Expected to find element: \`[data-sel-role=&quot;right-column&quot;]\`, but never found it." type="AssertionError"><![CDATA[AssertionError: Expected to find element
    at copyArrow (webpack://content-versioning-cypress/./cypress/e2e/jcontent/versionCopyField.cy.ts:36:13)
    at Context.eval (webpack://content-versioning-cypress/./cypress/e2e/jcontent/versionCopyField.cy.ts:128:8)]]></failure>
    </testcase>
    <testcase name="Version history keeps the arrow out" time="42.777" classname="keeps the arrow out">
    </testcase>
    <testcase name="Version history copies a datetime" time="0.000" classname="copies a datetime">
      <failure message="Timed out" type="CypressError"><![CDATA[CypressError: Timed out
    at ensureIsDescendent (http://jahia:8080/__cypress/runner/cypress_runner.js:115346:68)]]></failure>
    </testcase>
  </testsuite>
</testsuites>`

test('reads each failed test with its message, its spec file and the line of the test', () => {
  expect(readFailedTests(REPORT)).toEqual([
    {
      title: 'Version history offers the arrow',
      message:
        'Expected to find element: `[data-sel-role="right-column"]`, but never found it.',
      file: 'cypress/e2e/jcontent/versionCopyField.cy.ts',
      line: 128
    },
    {
      title: 'Version history copies a datetime',
      message: 'Timed out',
      file: 'cypress/e2e/jcontent/versionCopyField.cy.ts',
      line: undefined
    }
  ])
})

test('annotates 9 failed tests at most, and counts the others', () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'reports-'))
  fs.mkdirSync(path.join(folder, 'cypress'))
  for (let index = 0; index < 6; index++) {
    fs.writeFileSync(path.join(folder, 'cypress', `${index}.xml`), REPORT)
  }
  fs.writeFileSync(path.join(folder, 'broken.xml'), '<testsuites><testsuite')
  const error = jest.spyOn(core, 'error').mockImplementation(() => {})

  expect(annotateFailedTests(folder, 'tests')).toBe(3)
  expect(error).toHaveBeenCalledTimes(9)
  expect(error).toHaveBeenCalledWith(
    'Timed out',
    expect.objectContaining({
      title: 'Version history copies a datetime',
      file: 'tests/cypress/e2e/jcontent/versionCopyField.cy.ts'
    })
  )
})
