import {defineConfig} from 'vitest/config'

export default defineConfig({
  test: {
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      // main.ts and readInputs.ts bind the action to the runner; types.ts holds no code.
      exclude: ['src/**/*.test.ts', 'src/main.ts', 'src/readInputs.ts', 'src/types.ts', 'src/testing/**'],
      thresholds: {lines: 90, functions: 90, branches: 85, statements: 90}
    }
  }
})
