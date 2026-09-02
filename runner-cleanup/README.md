# Runner Cleanup

Reclaims disk space on GitHub-hosted runners by removing SDKs, caches and (optionally) browsers and Docker data that Jahia builds do not need. Typically frees around 30 GB on a standard `ubuntu-latest` runner.

## Why is this action vendored here?

This action is a local copy of [mathio/gha-cleanup](https://github.com/mathio/gha-cleanup) (MIT licensed, by Matej Lednicky), which several Jahia repositories were using directly. It was imported into `jahia-modules-action` for two reasons:

1. **The upstream action unconditionally prunes Docker.** Its `docker system prune -af` deletes every Docker image present on the runner, which conflicts with workflows that pre-pull images needed by later steps (Jahia images, Maven cache images, ...). This copy adds a `remove-docker-images` input so the Docker prune can be skipped while still reclaiming all the other space.
2. **Supply-chain control.** Keeping the code in a Jahia-owned repository means it is reviewed, versioned and released alongside our other actions, instead of executing third-party code that could change under us.

## Differences from upstream

- New `remove-docker-images` input (default `true`, matching upstream behavior). Set it to `false` to keep the Docker images already present on the runner.
- After each element is cleaned up, the action logs the amount of disk space reclaimed by that element.
- Before the Docker prune (or its skip), the action logs a detailed inventory of the Docker cache: overall usage per category (`docker system df`), images by name:tag sorted by size, containers with the image they were created from, volumes, and the build cache total.
- The upstream `verbose` input was removed: the per-element reclaimed-space log replaces it and is always on.

## Usage

```yaml
    runs-on: ubuntu-latest
    steps:
      - uses: jahia/jahia-modules-action/runner-cleanup@v2
        with:
          remove-browsers: true
          # Keep Docker images pulled before this step
          remove-docker-images: false
```

## Inputs

| Name | Default | Description |
| --- | --- | --- |
| `remove-browsers` | `false` | If `true`, also remove browser caches and binaries (Chromium, Chrome, Edge, Firefox). |
| `remove-docker-images` | `true` | If `false`, skip the Docker system/builder prune so Docker images already on the runner are kept. |
