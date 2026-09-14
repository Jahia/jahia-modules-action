/**
 * Post-package script to patch dist/index.js with the signal option
 * for child.spawn support (step cancellation).
 *
 * This is needed until https://github.com/actions/toolkit/pull/1469
 * is merged into @actions/exec.
 */

const fs = require('fs')
const path = require('path')

const distFile = path.join(__dirname, '..', 'dist', 'index.js')

if (!fs.existsSync(distFile)) {
  console.error('Error: dist/index.js not found. Run "yarn run package" first.')
  process.exit(1)
}

let content = fs.readFileSync(distFile, 'utf8')

const searchPattern = 'result.cwd = options.cwd;\n        result.env = options.env;'
const replacement = 'result.cwd = options.cwd;\n        result.signal = options.signal;\n        result.env = options.env;'

if (content.includes('result.signal = options.signal;')) {
  console.log('patch-signal: signal option already present in dist/index.js, skipping.')
  process.exit(0)
}

if (!content.includes(searchPattern)) {
  console.error('Error: Could not find the expected pattern in dist/index.js to patch.')
  console.error('The @actions/exec internals may have changed. Please verify manually.')
  process.exit(1)
}

content = content.replace(searchPattern, replacement)
fs.writeFileSync(distFile, content, 'utf8')

console.log('patch-signal: Successfully added signal option to _getSpawnOptions in dist/index.js')
