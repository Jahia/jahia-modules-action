# Install Jahia from its distribution installer

Four actions install a Jahia distribution directly on a runner, without Docker, and run it there. They work on Linux and Windows runners.

| Action | What it does |
| --- | --- |
| `install-jahia` | Replays an unattended IzPack descriptor against a `Jahia-EnterpriseDistribution-*.jar` installer and installs the licence. |
| `jahia-boot-check` | Starts the instance, waits for it, and fails when the webapp does not serve, the Spring context failed, `jahia.log` carries errors or Jahia wrote error dumps. With `start: 'false'` it only runs the checks. |
| `jahia-wait-patches` | Waits until a node has run the patch scripts left under `digital-factory-data/patches`, so the next node does not join too early. |
| `jahia-stop` | Stops the instance and waits for the JVM to exit. |

The actions write what they find in `verdict_dir` (`evidence.txt`, `boot-errors`, `patches-pending`, …), and they copy their logs to `lane-output/` in the workspace. The caller uploads that folder once, at the end of the job.

## A two-node cluster on one runner

Both nodes use the same database. The processing node creates the tables and starts first. The browsing node gets its own ports.

```yaml
      - id: processing
        uses: jahia/jahia-modules-action/install-jahia@v2
        with:
          installer_path: installers/Jahia-EnterpriseDistribution-8.2.3.2-r1.jar
          jahia_version: 8.2.3.2
          install_root: /tmp/jahia
          license_file: /tmp/license.xml
          db_mode: standalone
          db_type: mariadb
          db_url: jdbc:mariadb://localhost:3306/jahia?useUnicode=true&characterEncoding=UTF-8
          db_driver_class: org.mariadb.jdbc.Driver
          db_user: jahia
          db_password: ${{ secrets.DB_PASSWORD }}
          db_driver_jar: drivers/mariadb-java-client.jar
          cluster: 'true'
          processing_server: 'true'
          cluster_server_id: processing
          label: processing
      - id: browsing
        uses: jahia/jahia-modules-action/install-jahia@v2
        with:
          # ...the same installer and database...
          install_root: /tmp/jahia-browsing
          jahia_tomcat_port: '8081'
          cluster: 'true'
          processing_server: 'false'
          cluster_node_port: '7871'
          cluster_hazelcast_port: '7861'
          cluster_server_id: browsing
          create_tables: 'false'
          label: browsing

      - uses: jahia/jahia-modules-action/jahia-boot-check@v2
        with:
          install_root: ${{ steps.processing.outputs.install_root }}
          licensed: ${{ steps.processing.outputs.licensed }}
          label: processing
      - uses: jahia/jahia-modules-action/jahia-wait-patches@v2
        with:
          install_root: ${{ steps.processing.outputs.install_root }}
      - uses: jahia/jahia-modules-action/jahia-boot-check@v2
        with:
          install_root: ${{ steps.browsing.outputs.install_root }}
          jahia_tomcat_port: '8081'
          licensed: ${{ steps.browsing.outputs.licensed }}
          label: browsing

      # ... the job's own tests ...

      - uses: jahia/jahia-modules-action/jahia-stop@v2
        if: always()
        with:
          install_root: ${{ steps.browsing.outputs.install_root }}
      - uses: jahia/jahia-modules-action/jahia-stop@v2
        if: always()
        with:
          install_root: ${{ steps.processing.outputs.install_root }}
```

A Windows runner installs from the `.exe` beside the jar for versions below 8.2.3.2, because the jar installer there cannot validate the files it writes. `jahia_version` selects the installer, so set it.

See each `action.yml` for the full list of inputs.
