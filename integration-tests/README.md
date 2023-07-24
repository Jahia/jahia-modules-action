# About the action

This action was created using: https://github.com/actions/typescript-action/actions

# How to update

This is a regular typescript project, after checkout of the codebase:

```bash
# Install all the dependencies
yarn set version stable
yarn
```

The codebase need to be built for the changes to be taken into account:

```bash
# Create branch
git checkout -b YOUR_BRANCH

# Build
yarn run build

# Package
yarn run package

# Add, commit and push the changes
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
