This action is provided as an alternative to running maven commands within the `jahia/cimg-mvn-cache` [images](https://github.com/Jahia/cimg-mvn-cache).

The primary purposes of such images was to preload a maven cache with the most common dependencies used when building Jahia modules.

```yaml
    runs-on: ubuntu-latest 
    container:
      image: jahia/cimg-mvn-cache:ga_cimg_openjdk_11.0.20-node
      credentials:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_PASSWORD }}
```

When using GitHub container' command, we cannot perform operations such as setting up a VPN to access some of the internal resources (such as for running jahia-cloud-modules unit tests).

The cache warmup achieves a similar objective but without this constraint.

And use this instead:
```yaml
    runs-on: ubuntu-latest   
    steps:
      - uses: jahia/jahia-modules-action/maven-cache-warmup@create-maven-cache-warmup
        with:
          docker-image: jahia/cimg-mvn-cache:ga_cimg_openjdk_11.0.20-node
          docker-username: ${{ secrets.DOCKERHUB_USERNAME }}
          docker-password: ${{ secrets.DOCKERHUB_PASSWORD }}
```

