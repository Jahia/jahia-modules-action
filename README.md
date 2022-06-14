<a href="https://www.jahia.com/">
    <img src="https://www.jahia.com/modules/jahiacom-templates/images/jahia-3x.png" alt="Jahia logo" title="Jahia" align="right" height="60" />
</a>

# jahia-modules-action

A set of commands and jobs to perform CI operations with GitHub Actions as part of a Jahia module lifecycle

## Development

Some resources for developing github actions:

- https://github.com/sdras/awesome-actions
- https://github.com/github/codeql-action
- https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions

Complex actions can be found here:

## Use the Action

This repository contains multiple actions, each located in its own folder in this repository.

For example, the build action can be called using this code:

```yaml
    - uses: jahia/jahia-modules-action/build@v2
    with:
        module_id: sitemap
```

In the above example, we're referring to the `v2` branch, but `v2` could be replaced by any branch or tag. You could very well directly call a development branch to validate the proper operation of your action. `uses: jahia/jahia-modules-action/build@My-Dev-Branch`.

## Releasing the Action

Since a large portion of our repositories are using the action, we're using a particular branch as an alias to the latest changes (`v1`, `v2`). Releasing consists in updating this branch with the changes you want to make available.

To release changes, proceed as follow:

- Create a tag, with your desired version (for example: `v2.1.0`).
- Delete branch `v2`
- Move into the tag `v2.1.0` and create a `v2` branch from that tag.

Any runs triggered between the time the `v2` branch is deleted and re-created will FAIL. Deleting and creating a new branch shouldn't take more than a couple of seconds.

## Open-Source

This is an Open-Source module, you can find more details about Open-Source @ Jahia [in this repository](https://github.com/Jahia/open-source).
