# The provisioning script of the modules of a Jahia release

`modules-provisioning` writes, for one Jahia release, the provisioning script that installs the modules it ships, as one `installOrUpgradeBundle` block that Jahia's provisioning reads. Each module comes at the version the release ships, or at the newest version the Store offers that release, which is the version its module manager would show. The compatibility matrix the script is built from is written beside it as JSON.

The action is standard-library Python, run from the action's folder, so it needs no setup step. It reads Nexus and the Store only, never a Jahia.

```yaml
      - id: modules
        uses: jahia/jahia-modules-action/modules-provisioning@v2
        with:
          jahia_version: 8.2.3.2
          versions: store
          nexus_username: ${{ secrets.NEXUS_USERNAME }}
          nexus_password: ${{ secrets.NEXUS_PASSWORD }}
      - run: cat "${{ steps.modules.outputs.provisioning_path }}"
```

The script reads, for `versions: store`:

```yaml
# Jahia 8.2.3.2: the 53 modules it ships, each at the newest version the Store offers that release.
# 14 of them are newer than shipped. Store: https://store.jahia.com/en/sites/private-app-store
# Generated on 2026-10-27T14:02:11Z by jahia-modules-action/modules-provisioning.
- installOrUpgradeBundle:
    - url: 'mvn:org.jahia.modules/app-shell/3.4.0'  # shipped 3.3.0
    - url: 'mvn:org.jahia.modules/assets/8.3.0'
    - url: 'mvn:org.jahia.modules/graphql-dxm-provider/3.9.1'  # shipped 3.7.0
      startLevel: 85
    - url: 'js:mvn:org.jahia.modules.javascript/luxe-jahia-demo/1.1.0/tgz'  # shipped 1.0.1
  autoStart: true
```

A module the Store does not list, such as `default` or `module-manager`, keeps its shipped version. The `startLevel` of a module comes from the pack of the release. A JavaScript module is a `js:mvn:` url, as in the packs.

## Inputs

| Input | Default | What it does |
| --- | --- | --- |
| `jahia_version` | required | The release, such as `8.2.3.2`. |
| `versions` | `store` | `store`: the newest version the Store offers the release, per module. `shipped`: the versions the release ships. |
| `store_url` | the Jahia Store | The Store the `store` mode reads. |
| `nexus_username`, `nexus_password` | empty | Read the EE pack of the release. Without them the script lists the public packs only. The credentials go to Nexus only. |
| `provisioning_path` | `modules-provisioning.yml` | The script. |
| `matrix_path` | `compat-matrix.json` | The matrix. |
| `cache_path` | `compat-matrix-cache.json` | The versions already read. Restore it with `actions/cache` and the run only reads what was published since. |
| `release_modules` | `shipped` | `all` reads every released version of each shipped module into the matrix, which takes minutes; `shipped` reads what the script needs. |

## Outputs

`provisioning_path` and `matrix_path` name the files written. `modules` counts the modules of the script, and `upgraded` those whose version is newer than shipped.

## The matrix

`compat-matrix.json` holds, under `jahia`, each release read with the modules of its packs and the version the Store offers it of each Store module. Under `modules`, each module read carries every version read, with `jahiaRequiredVersion`, `jahiaDepends`, the `org.jahia` Maven dependencies with their versions resolved, `moduleType` and `packaging`, and `system: true` when the module is a system module. Under `store`, the Store's module list with the required version of each version.

The same script answers wider questions from a workstation, with `NEXUS_USERNAME` and `NEXUS_PASSWORD` in the environment:

```bash
python3 src/compat-matrix.py --jahia --store --cache compat-matrix-cache.json   # every release, every module
python3 src/compat-matrix.py --module jcontent                                 # every release of one module
```
