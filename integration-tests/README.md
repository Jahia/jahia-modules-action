# About the action

This action was created using: https://github.com/actions/typescript-action/actions

# How to update

This is a regular typescript project, after checkout of the codebase:

```bash
# Install all the dependencies
yarn
```

The codebase need to be built for the changes to be taken into account:

```bash
# Create branch
git checkout -b YOUR_BRANCH

# Build
yarn run build

# Package
NODE_OPTIONS=--openssl-legacy-provider yarn run package
```

# Fix issue with child.spawn
We are currently waiting for both https://github.com/actions/toolkit/issues/1534 and https://github.com/actions/toolkit/pull/1469 to be included into the action toolkit to support step cancellation.

In the meantime, after building/packaging, modify the `dist/index.js` search for `_getSpawnOptions(options, toolPath)` and update it as follow (simply adding the signal option):

Before:
```
const result = {};
result.cwd = options.cwd;
result.env = options.env;
```

After:
```
const result = {};
result.cwd = options.cwd;
result.signal = options.signal;
result.env = options.env;
```

# Add, commit and push the changes
```bash
git add .
git commit -m "Your Commit Message"
git push --set-upstream origin YOUR_BRANCH
```

# How to try

Once your changes are pushed (incl. the built assets), you can try it out by pointing a workflow to your branch

```yaml
- uses: jahia/jahia-modules-action/integration-tests@YOUR_BRANCH
  with:
    module_id: jexperience
```
