# The provisioning script of the modules of a Jahia release

`modules-provisioning` writes, for one Jahia release, the provisioning script that installs the modules it ships, as one `installOrUpgradeBundle` block that Jahia's provisioning reads. Each module comes at the version the release ships, or at the version the module manager of that release offers from the Store. The matrix the script is built from is written beside it as JSON.

The action reads Nexus and the Store only, never a Jahia.

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
# Jahia 8.2.2.1: the 52 modules it ships, each at the version its module manager offers from the Store.
# 20 of them are newer than shipped. Store: https://store.jahia.com/en/sites/private-app-store
# Generated on 2026-11-24T14:12:31Z by jahia-modules-action/modules-provisioning.
- installOrUpgradeBundle:
    - url: 'mvn:org.jahia.modules/app-shell/3.3.0'  # mandatory: the module manager does not offer 4.0.0
    - url: 'mvn:org.jahia.modules/assets/8.3.0'  # shipped 8.2.0
    - url: 'mvn:org.jahia.modules/graphql-dxm-provider/3.4.0'  # mandatory: the module manager does not offer 3.10.0
      startLevel: 85
    - url: 'mvn:org.jahia.modules/jcontent/3.8.1'  # shipped 3.2.0
    - url: 'mvn:org.jahia.modules/tags/8.2.0'
  autoStart: true
```

The `startLevel` of a module comes from the pack of the release. A JavaScript module is a `js:mvn:` url, as in the packs.

## Which version the Store mode names

The script names the version that the "Installed modules" page of the release shows as an available update. The rules are those of [module-manager](https://github.com/Jahia/module-manager/tree/main/core/src/main):

1. **The offer of the Store.** For a module the Store lists, the offer is its newest version whose required Jahia version is at most the release, on the same major (`ForgeService`).
2. **Never an older version.** The page offers an update only when no same or newer version is installed (`ModuleManagementFlowHandler.getAvailableUpdates`). The Store lists some modules at an older version than a release ships, and the script keeps the shipped one.
3. **Never a mandatory module.** The page offers no update of a module it marks "mandatory system dependency". These are the modules Jahia core names in `nonManageableModules` (`templates-system`, `serverSettings`, `serverSettings-ee`, `siteSettings`, `app-shell`, `jahia-ui-root`, `jahia-administration`), and each module they depend on through `Jahia-Depends`, at every level. The script keeps their shipped version and names the offer it withholds.

A module the Store does not list, such as `default` or `module-manager`, keeps its shipped version.

The action does not read the operation constraints of a Jahia (`OperationConstraintsService`), which an administrator may configure to forbid a deployment.

## Inputs

| Input | Default | What it does |
| --- | --- | --- |
| `jahia_version` | required | The release, such as `8.2.3.2`. |
| `versions` | `store` | `store`: the version the module manager offers, per module. `shipped`: the versions the release ships, and the Store is not read. |
| `store_url` | the Jahia Store | The Store the `store` mode reads. |
| `nexus_username`, `nexus_password` | empty | Read the EE pack of the release. Without them the script lists the public packs only. The credentials go to Nexus only. |
| `provisioning_path` | `modules-provisioning.yml` | The script. |
| `matrix_path` | `compat-matrix.json` | The matrix. |

## Outputs

`provisioning_path` and `matrix_path` name the files written. `modules` counts the modules of the script, and `upgraded` those whose version is newer than shipped.

## The matrix

`compat-matrix.json` holds, under `jahia`, the release with the modules of its packs, the version the Store offers it of each shipped module (`storeOffers`) and its mandatory modules (`mandatoryModules`). Under `modules`, each shipped module carries its shipped version, and the offered one when the script names it, with `jahiaRequiredVersion`, `jahiaDepends`, `moduleType` and `packaging`. Under `store`, the Store's module list with the required version of each version.

Only the manifest of a jar is downloaded, through HTTP ranges.

## Development

The action is TypeScript, bundled into `dist/index.js`, which is committed. Each file of `src/` exports one arrow function, and its test sits beside it.

```bash
npm ci
npm run all       # type check, format check, tests with coverage, bundle
```

`src/modulePages.test.ts` holds the reference of the rules above. Each file of `src/testing/pages/` is the "Installed modules" page of a standalone Jahia (8.1.9.6, 8.2.1.0, 8.2.2.1 and 8.2.3.7), read row by row on 2026-11-24, with the packs, the `Jahia-Depends` and the Store of that day. The test fails when the script names another version than the page for a module the page lists.

Commit `dist/` with each change of `src/`: the `Test modules-provisioning` workflow fails when the bundle is not the one the sources build.
