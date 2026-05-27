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

# Package (also auto-patches dist/index.js with signal support)
yarn run package
```

## Note about signal support in child.spawn

We are currently waiting for both https://github.com/actions/toolkit/issues/1534 and https://github.com/actions/toolkit/pull/1469 to be included into the action toolkit to support step cancellation.

In the meantime, the `postpackage` script (`scripts/patch-signal.js`) automatically patches `dist/index.js` to add signal support after each packaging run. No manual intervention is needed.

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
