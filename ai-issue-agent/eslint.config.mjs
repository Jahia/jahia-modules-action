// Strict, type-checked linting for the issue-agent actions. The style contract of this
// package: functional TypeScript, arrow functions only, one function per file.
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['**/dist/**', 'jest.config.js'] },
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      'func-style': ['error', 'expression'],
      'prefer-arrow-callback': 'error',
      'no-restricted-syntax': ['error', { selector: 'ClassDeclaration', message: 'Functional style only — no classes.' }],
    },
  },
  {
    files: ['__tests__/**/*.ts'],
    rules: {
      // jest.fn() mocks trip these without adding safety to a test file
      '@typescript-eslint/unbound-method': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
    },
  },
)
