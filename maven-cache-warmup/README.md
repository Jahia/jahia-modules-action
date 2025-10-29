This action is provided as an alternative to running maven commands within the `jahia/jahia-docker-mvn-cache` [images](https://github.com/Jahia/jahia-docker-mvn-cache).

The primary purposes of such images was to preload a maven cache with the most common dependencies used when building Jahia modules.

```yaml
    runs-on: ubuntu-latest 
    container:
      image: ghcr.io/jahia/jahia-docker-mvn-cache:11-jdk-noble-mvn-loaded
      credentials:
        username: ${{ secrets.GH_PACKAGES_USERNAME }}
        password: ${{ secrets.GH_PACKAGES_TOKEN }}
```

When using GitHub container' command, we cannot perform operations such as setting up a VPN to access some of the internal resources (such as for running jahia-cloud-modules unit tests).

The cache warmup achieves a similar objective but without this constraint.

And use this instead:
```yaml
    runs-on: ubuntu-latest   
    steps:
      - uses: jahia/jahia-modules-action/maven-cache-warmup@create-maven-cache-warmup
        with:
          docker-image: ghcr.io/jahia/jahia-docker-mvn-cache:11-jdk-noble-mvn-loaded
          username: ${{ secrets.GH_PACKAGES_USERNAME }}
          password: ${{ secrets.GH_PACKAGES_TOKEN }}
```

