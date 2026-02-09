# Copilot Instructions for jahia-modules-action

## Repository Overview

This is a **GitHub Actions monorepo** containing 35+ reusable composite and TypeScript-based actions for managing Jahia module lifecycle operations. The actions are designed to be composed into GitHub workflows and cover:

- **Build & Compilation**: Maven and JavaScript/Node.js builds
- **Release Management**: Complete orchestration with semantic versioning
- **Dependency Management**: Version checking, unused detection, vulnerability scanning
- **Code Quality**: SonarQube integration, static analysis, SBOM processing
- **Infrastructure**: VPN tunnels, Docker management, Maven caching, bastion hosts
- **Issue & Delivery Management**: Issue tracking, labeling, delivery workflows
- **Publishing**: Maven and JavaScript module publishing

## Repository Structure

### Action Organization

Each action is in its own directory at the root level with an `action.yml` file. The 35+ actions include:

**Build Actions**: `build/`, `build-step-mvn/`, `build-step-javascript/`, `build-javascript/`

**Release Actions**: `release/`, `release-javascript/`, `release-publication/`, `release-rollback/`, `publish/`, `publish-javascript/`

**Dependency Actions**: `dependencies-check-java/`, `dependencies-check-javascript/`, `dependencies-get-new-versions-java/`, `dependencies-get-new-versions-javascript/`, `dependencies-get-unused-java/`, `dependencies-get-unused-javascript/`

**Quality Actions**: `sonar-analysis/`, `static-analysis/`, `sbom-processing/`

**Infrastructure Actions**: `vpn-tunnel/`, `docker-tags/`, `docker-images-cleanup/`, `maven-cache-warmup/`, `download-bastion/`, `upload-bastion/`, `upload-artifact/`

**Utility Actions**: `helper/`, `integration-tests/`, `code-signer/`, `slack-jahia/`, `generate-changelog/`, `update-signature/`, `academy-publish/`

**Delivery Actions**: `delivery/` (contains 5 sub-actions for issue/PR management)

### TypeScript Projects

Two actions are full TypeScript projects with build tooling:

- **`helper/`**: Reusable TypeScript utilities library
- **`integration-tests/`**: Integration test runner

Both use:
- TypeScript (v4.x)
- ESLint + Prettier for code quality
- Jest for testing
- @vercel/ncc for bundling
- @actions/core and @actions/github for GitHub API integration

### Reusable Workflows

Located in `.github/workflows/`, these are composable workflows that can be called from other repositories:

- `reusable-on-code-change.yml`: Complete CI pipeline (build, test, analysis)
- `reusable-integration-tests.yml`: Integration testing
- `reusable-release-module.yml`: Release orchestration
- `reusable-sonar-scan.yml`: SonarQube analysis
- `reusable-delivery-*.yml`: Delivery management
- `reusable-academy-*.yml`: Documentation publishing

## Development Workflow

### Working with TypeScript Actions

For `helper/` and `integration-tests/` directories:

```bash
cd helper/  # or integration-tests/

# Install dependencies
yarn  # or npm install

# Build TypeScript
yarn run build  # or npm run build

# Run tests
yarn test  # or npm test

# Format code
yarn run format  # or npm run format

# Lint code
yarn run lint  # or npm run lint

# Package for distribution
NODE_OPTIONS=--openssl-legacy-provider yarn run package  # or npm run package

# Run all checks
yarn run all  # or npm run all
```

### Important Build Notes

1. **Always build and package before committing**: TypeScript actions must have their `dist/` folder committed with bundled code.

2. **Manual patch required for integration-tests**: After building/packaging, manually modify `dist/index.js` to add signal support:

   Find `_getSpawnOptions(options, toolPath)` and update:
   ```javascript
   // Before:
   const result = {};
   result.cwd = options.cwd;
   result.env = options.env;
   
   // After:
   const result = {};
   result.cwd = options.cwd;
   result.signal = options.signal;  // ADD THIS LINE
   result.env = options.env;
   ```
   
   Or use this Mac command:
   ```bash
   sed -i '' '/result\.cwd = options\.cwd;/a\
   result.signal = options.signal;
   ' dist/index.js
   ```

   This is a workaround until https://github.com/actions/toolkit/issues/1534 is resolved.

3. **Node version**: Use LTS version. The codebase supports Node 16+, but newer versions work.

### Working with Composite Actions

Most actions are composite actions (shell-based) defined in `action.yml`:

```yaml
name: Action Name
description: Action description
inputs:
  input_name:
    description: 'Input description'
    required: false
    default: 'default value'
runs:
  using: 'composite'
  steps:
    - name: Step name
      shell: bash
      run: |
        # Shell commands here
```

**Key points:**
- No build step required - edit `action.yml` directly
- Always specify `shell: bash` for run steps
- Use `${{ inputs.input_name }}` to access inputs
- Use environment variables for passing data between steps

### Testing Actions

#### Local Testing

Test actions by creating a workflow in a test repository that references your development branch:

```yaml
- uses: jahia/jahia-modules-action/build@YOUR_BRANCH_NAME
  with:
    module_id: test-module
```

#### TypeScript Unit Tests

For `helper/` and `integration-tests/`:

```bash
# Run tests
yarn test  # or npm test

# Tests are in __tests__/ directory
# Use Jest testing framework
```

## Release Process

**IMPORTANT: Do NOT create `v2` branches anymore.** Version tags are now managed as Git tags and generated automatically.

### Creating a Release

1. Go to https://github.com/Jahia/jahia-modules-action/releases
2. Click "Draft a new release"
3. Select/create a tag following **semantic versioning**: `v2.5.6`
4. Enter the version number as the title
5. Select "Set as the latest release"
6. Click "Publish release"

This automatically creates:
- The specific version tag (e.g., `v2.5.6`)
- The major version alias tag (e.g., `v2`)

### Versioning Strategy

- **Semantic Versioning**: `vMAJOR.MINOR.PATCH` (e.g., `v2.5.6`)
- **Major version tags**: Automatically aliased (e.g., `v2` always points to latest `v2.x.x`)
- Users can pin to specific versions or use major version tags

## Action Usage Pattern

Actions are referenced with the path and version/branch:

```yaml
- uses: jahia/jahia-modules-action/ACTION_FOLDER@VERSION
  with:
    parameter_name: value
```

Examples:
```yaml
# Use specific version
- uses: jahia/jahia-modules-action/build@v2.5.6

# Use major version (recommended for stability)
- uses: jahia/jahia-modules-action/build@v2

# Use development branch (for testing)
- uses: jahia/jahia-modules-action/build@my-dev-branch
```

## Key Technologies & Tools

### Languages
- **TypeScript**: For complex actions with logic (helper, integration-tests)
- **Shell/Bash**: For composite actions and build steps
- **YAML**: For action definitions and workflows
- **Maven**: For Java module builds
- **Node.js/npm/yarn**: For JavaScript modules and TypeScript actions

### GitHub Actions APIs
- `@actions/core`: Core action functionality (inputs, outputs, logging)
- `@actions/github`: GitHub API access and context
- `@actions/exec`: Executing commands
- `@actions/artifact`: Artifact management

### Build & Quality Tools
- **@vercel/ncc**: Bundles TypeScript actions into single file
- **ESLint**: Code linting
- **Prettier**: Code formatting
- **Jest**: Testing framework
- **SonarQube**: Code quality analysis
- **Maven**: Java build tool

### External Services
- **Nexus**: Maven artifact repository
- **Docker**: Container management
- **WireGuard**: VPN tunneling
- **Slack**: Notifications
- **TestRail**: Test management
- **PagerDuty**: Incident management
- **DependencyTrack**: SBOM management

## Common Patterns & Best Practices

### 1. Composite Action Structure

```yaml
name: Action Name
description: Brief description
inputs:
  required_input:
    description: 'What this input does'
    required: true
  optional_input:
    description: 'What this input does'
    required: false
    default: 'default_value'
runs:
  using: 'composite'
  steps:
    - name: Descriptive step name
      shell: bash
      run: |
        echo "Use ${{ inputs.required_input }}"
```

### 2. Reusable Workflow Structure

```yaml
name: Reusable Workflow Name
on:
  workflow_call:
    inputs:
      input_name:
        type: string
        required: true
    secrets:
      secret_name:
        required: true

jobs:
  job_name:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jahia/jahia-modules-action/some-action@v2
```

### 3. Artifact Management

```yaml
# Upload artifacts
- uses: actions/upload-artifact@v4
  with:
    name: artifact-name
    path: path/to/files
    retention-days: 2

# Download artifacts
- uses: actions/download-artifact@v4
  with:
    name: artifact-name
```

### 4. Caching Strategy

Maven cache example:
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.m2/repository
      /root/.m2/repository
    key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}
    restore-keys: |
      ${{ runner.os }}-maven-
```

### 5. Environment Variables

Pass credentials and configuration:
```yaml
- name: Set environment variables
  shell: bash
  run: |
    echo "VAR_NAME=value" >> $GITHUB_ENV
    echo "SECRET_VAR=${{ inputs.secret_input }}" >> $GITHUB_ENV
```

### 6. Conditional Execution

```yaml
- name: Step name
  if: ${{ condition }}
  # or
  if: ${{ inputs.param == 'value' }}
  # or
  if: ${{ success() }}  # or failure(), always()
```

## Troubleshooting & Common Issues

### 1. TypeScript Build Errors

**Issue**: `jest: not found` or similar dependency errors

**Solution**: Install dependencies first
```bash
cd helper/  # or integration-tests/
yarn install  # or npm install
```

### 2. Package Command Fails

**Issue**: `error:0308010C:digital envelope routines::unsupported`

**Solution**: Use legacy OpenSSL provider
```bash
NODE_OPTIONS=--openssl-legacy-provider yarn run package
```

### 3. dist/ Folder Not Updated

**Issue**: Changes not reflected in action execution

**Solution**: Always build AND package TypeScript actions
```bash
yarn run build
NODE_OPTIONS=--openssl-legacy-provider yarn run package
git add dist/
git commit -m "Update built action"
```

### 4. Action Not Found

**Issue**: `Action 'jahia/jahia-modules-action/action-name@branch' not found`

**Solution**: 
- Verify the action folder exists
- Verify the branch/tag exists
- Check the action path is correct (folder name, not action name)

### 5. Maven Build Failures

**Issue**: Dependencies not resolving

**Solution**: Check Nexus credentials and settings.xml configuration
- Ensure `NEXUS_USERNAME` and `NEXUS_PASSWORD` are set
- Verify `mvn_settings_filepath` points to valid settings file (default: `.github/maven.settings.xml`)

### 6. Integration Test Signal Handling

**Issue**: Tests don't cancel properly

**Solution**: Apply the manual patch to `dist/index.js` as documented in the "Manual patch required for integration-tests" section above

## Git & Version Control

### Branch Strategy

- **main/master**: Primary development branch
- **v2, v3, etc.**: These are now TAGS, not branches (automatically created on release)
- **Feature branches**: Use descriptive names for development

### Commit Guidelines

Follow conventional commits for changelog generation:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Test changes
- `build:` - Build system changes
- `ci:` - CI/CD changes
- `chore:` - Other changes

### .gitignore

Current .gitignore is minimal:
```
/.settings/
/.project
*.iml
.DS_Store
.idea
```

**Note**: TypeScript actions commit their `dist/` folder (this is intentional - it's the bundled distribution)

## File Locations & Paths

- **Actions**: Root level directories (e.g., `/build/`, `/release/`)
- **Workflows**: `.github/workflows/`
- **Issue Templates**: `.github/ISSUE_TEMPLATE/`
- **Release Config**: `.github/release.yml`
- **TypeScript Source**: `helper/src/`, `integration-tests/src/`
- **TypeScript Tests**: `helper/__tests__/`, `integration-tests/__tests__/`
- **TypeScript Config**: `tsconfig.json`, `jest.config.js`, `.eslintrc.json`, `.prettierrc.json`
- **Built Actions**: `helper/dist/`, `integration-tests/dist/`

## Documentation Resources

### Internal Documentation
- Main README: `/README.md`
- Integration Tests README: `/integration-tests/README.md`
- Helper README: `/helper/README.md`
- Delivery README: `/delivery/README.md`
- Maven Cache Warmup README: `/maven-cache-warmup/README.md`

### External Resources
- GitHub Actions Documentation: https://docs.github.com/en/actions
- Awesome Actions: https://github.com/sdras/awesome-actions
- CodeQL Action Example: https://github.com/github/codeql-action
- Workflow Syntax: https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions
- Dependency Checks Blog: https://medium.com/jahia-techblog/why-and-how-to-automate-dependency-checks-73649d42cf87
- Jahia Open Source: https://github.com/Jahia/open-source

## Making Changes: Checklist

When modifying this repository:

1. **Understand the scope**: Identify which action(s) need changes
2. **For TypeScript actions**:
   - [ ] Make code changes in `src/` directory
   - [ ] Update tests in `__tests__/` if needed
   - [ ] Run `yarn run build`
   - [ ] Run `yarn run lint` and fix issues
   - [ ] Run `yarn test` and ensure passing
   - [ ] Run `NODE_OPTIONS=--openssl-legacy-provider yarn run package`
   - [ ] Apply manual patch to `dist/index.js` if working with integration-tests
   - [ ] Commit both source AND `dist/` folder
3. **For composite actions**:
   - [ ] Edit `action.yml` directly
   - [ ] Test in a workflow pointing to your branch
   - [ ] Commit changes
4. **For reusable workflows**:
   - [ ] Edit workflow file in `.github/workflows/`
   - [ ] Test by calling from another repository
   - [ ] Commit changes
5. **Documentation**:
   - [ ] Update relevant README files
   - [ ] Update action descriptions in `action.yml` if needed
6. **Testing**:
   - [ ] Test changes using a development branch reference
   - [ ] Verify in real workflow execution
7. **Release**:
   - [ ] Create release via GitHub UI
   - [ ] Use semantic versioning
   - [ ] Verify tags are created correctly

## Security & Secrets

### Common Secrets Used
- `NEXUS_USERNAME` / `NEXUS_PASSWORD`: Maven repository access
- `NEXUS_INTERNAL_URL` / `NEXUS_INTERNAL_RELEASES_URL`: Internal repositories
- `GH_PACKAGES_USERNAME` / `GH_PACKAGES_TOKEN`: GitHub Packages access
- `SONAR_URL` / `SONAR_TOKEN`: SonarQube integration
- `DEPENDENCYTRACK_APIKEY`: SBOM processing
- Various service-specific tokens (TestRail, PagerDuty, Slack, etc.)

### Best Practices
- Never commit secrets or credentials
- Use GitHub secrets or repository secrets
- Pass secrets as inputs to actions, not hardcoded
- Use `required: true` for sensitive inputs
- Validate inputs before use

## Quick Reference Commands

```bash
# Clone repository
git clone https://github.com/Jahia/jahia-modules-action.git
cd jahia-modules-action

# Work on TypeScript action
cd helper  # or integration-tests
yarn install
yarn run all  # Build, lint, test, package

# Create feature branch
git checkout -b feature/my-changes

# Test action from branch
# In another repo's workflow:
uses: jahia/jahia-modules-action/build@feature/my-changes

# Commit changes
git add .
git commit -m "feat: description of change"
git push origin feature/my-changes

# Create PR and eventually release via GitHub UI
```

## Summary

This repository is a **collection of reusable GitHub Actions** for Jahia module lifecycle management. Actions are either:

1. **Composite actions** (YAML-based, shell scripts) - edit `action.yml` directly
2. **TypeScript actions** (compiled) - edit in `src/`, build, package, commit `dist/`
3. **Reusable workflows** (YAML-based) - edit workflow files

**Key principle**: Actions are meant to be composed and reused across multiple Jahia module repositories. Changes should be backward compatible and well-tested before release.
