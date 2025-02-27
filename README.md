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

## Documentation

For the dependencies checks, here's a blog post explaining how they've been built: https://medium.com/jahia-techblog/why-and-how-to-automate-dependency-checks-73649d42cf87

## Releasing the Action

IMPORTANT: Do not create `v2` branches anymore, this alias is now a Git tag, and is generated automatically

To release the action, create a new release via the GitHub UI: https://github.com/Jahia/jahia-modules-action/releases

Click on:
- Draft a new release
- Select a tag (please follow SemVer) using this pattern v2.5.6
- Enter a title (the version number)
- Select "Set as the latest release"
- Click on Publish release

If your version was v2.5.6, this will create two tags: v2.5.6 and v2

## Open-Source

This is an Open-Source module, you can find more details about Open-Source @ Jahia [in this repository](https://github.com/Jahia/open-source).
