# About the fork

This is a fork of v1.0.6 of the ssh-port-forward-action available at https://github.com/selfagency/ssh-port-forward-action/tree/v1.0.6

The original action was not compatible with establishing the tunnel from inside a docker container, for example the one we use for caching maven artifacts such as in the example below:

```yaml
  build:
    name: Build Module
    needs: [ update-signature, static-analysis ]
    runs-on: self-hosted
    env:
      NEXUS_INTERNAL_URL: ${{ secrets.NEXUS_INTERNAL_URL }}
    container:
      image: jahia/cimg-mvn-cache:ga_cimg_openjdk_11.0.20-node
      credentials:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_PASSWORD }}
    steps:
      - uses: actions/checkout@v4
      - uses: jahia/jahia-modules-action/build@v2
        with:
          mvn_settings_filepath: '.github/maven.settings.xml'
          nexus_username: ${{ secrets.NEXUS_USERNAME }}
          nexus_password: ${{ secrets.NEXUS_PASSWORD }}
```

A new parameter was added `run-in-container` to indicate if the action is expected to run within a docker container/

## Sample usage

```yaml
name: SSH Tunnel

on:
  workflow_dispatch:

jobs:
  ssh-tunnel:
    runs-on: ubuntu-latest
    container:
      image: jahia/cimg-mvn-cache:ga_cimg_openjdk_11.0.20-node
      credentials:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_PASSWORD }}    
    steps:
      - uses: jahia/jahia-modules-action/ssh-port-forward@ssh-port-forward
        with:
          ssh-key: ${{ secrets.BASTION_SSH_PRIVATE_KEY_JAHIACI }}
          ssh-host: circleci-bastion-prod.jahia.com
          ssh-port: 220
          ssh-user: jahia-ci
          local-port: 8443
          remote-host: app.dev.j.jahia.com
          remote-port: 443     
          run-in-container: true     

      - name: Add entry to /etc/hosts
        run: |
          echo "127.0.0.1 app.dev.j.jahia.com" | sudo tee -a /etc/hosts

      - run: 'curl -v -k https://app.dev.j.jahia.com:8443'
```



# SSH port forwarding action

GitHub action to forward a remote connection to a local port over SSH. 

## Prerequisites

You must have a passwordless SSH key set up on the remote server.


## Github Action Inputs

| Variable      | Description     |
|---------------|-----------------|
| `ssh-key`     | SSH private key |
| `ssh-host`    | SSH host        |
| `ssh-port`    | SSH port        |
| `ssh-user`    | SSH user        |
| `local-port`  | Local port      |
| `remote-host` | Remote host     |
| `remote-port` | Remote port     |
| `run-in-container` | Does the action run inside a docker container (default: false)     |

## Example Usage

```
jobs:
  job_id:
    steps:
    - uses: 'actions/checkout@v3'

    - uses: selfagency/ssh-port-forward-action@v1.0.5
      with:
        ssh-key: ${{ secrets.SSH_KEY }}
        ssh-host: your-host.com
        ssh-port: 22
        ssh-user: username
        local-port: 6379
        remote-host: localhost
        remote-port: 6379
        
    - run: 'redis-cli -p 6379 ping'
```

