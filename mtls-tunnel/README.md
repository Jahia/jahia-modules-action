# mTLS Tunnel Action

A composite GitHub Action that lets a CI job reach internal Jahia services using a short-lived client certificate minted from the run's own GitHub OIDC token.

The tunnel carries **raw TCP**, so it is not limited to HTTPS: `ssh` on port 22 goes through it the same way `curl` does on 443.

It replaces the WireGuard [`vpn-tunnel`](../vpn-tunnel) action for access to those services:

| | `vpn-tunnel` (WireGuard) | `mtls-tunnel` |
|---|---|---|
| Credential | long-lived VPN configuration in a secret | the run's OIDC token, exchanged for a 1-hour certificate |
| Concurrency | one shared peer, concurrent runs conflict | one identity per run |
| Containers | not supported (kernel interface) | supported (userspace) |
| Scope | whatever the VPN routes | only the hostnames allowlisted on the bastion |

## Description

The action installs `stunnel`, exchanges the run's OIDC token for a client certificate at the step-ca broker, then opens one mTLS tunnel per target `host:port` and maps each host to a loopback address in `/etc/hosts`.

```
local client  --plain traffic-->  127.0.0.x:<port>   (local stunnel client)
                                  --mTLS, SNI=host-->  bastion
                                  --raw TCP-->  <host>  (real service, real certificate)
```

The bastion routes on the outer SNI, then forwards raw TCP, which is why the payload is free. For a TLS payload, the client's own handshake travels *inside* the mTLS tunnel: there is no man-in-the-middle at the bastion, and tools keep verifying the real service certificate. No `-k`, no `--resolve`, no proxy variable, no per-tool configuration.

Only hostnames present in the bastion's target map are forwarded; anything else is refused.

## Requirements

The calling job **must** declare the OIDC permission, since a composite action cannot grant it to itself:

```yaml
permissions:
  id-token: write
```

The job also needs root (binding the loopback addresses and writing `/etc/hosts`): `sudo` on a GitHub-hosted runner, or running as root in a container job.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `hosts` | Hosts to tunnel, **one `host` or `host:port` per line**. Port defaults to 443. | ✅ | — |
| `ca-url` | step-ca broker URL that signs the CSR, e.g. `https://<broker>:8444` | ✅ | — |
| `bastion` | mTLS entry point of the bastion, `host:port` | ✅ | — |
| `step-root` | step-ca root CA certificate, PEM. Public value. | ✅ | — |
| `server-ca` | CA certificate of the bastion's server certificate, PEM. Public value. | ✅ | — |
| `server-name` | Expected CN/SAN on the bastion certificate, pinned via `checkHost` | ✅ | — |
| `audience` | `aud` claim requested for the OIDC token, the value the broker expects | ✅ | — |
| `canary-url` | URLs fetched through the tunnels once they are up, **one per line**. Empty skips the check. | ❌ | `''` |
| `canary-http-response` | Status code every canary URL must return. Empty accepts any HTTP response. | ❌ | `''` |
| `canary-retries` | Attempts per canary URL before the check fails the job | ❌ | `5` |

**No input describing the broker has a default.** `ca-url`, `bastion`, `server-name` and `audience` all identify one specific deployment, and baking any of them into the action would force a new release the day it moves. Pass them as organization variables. Only the canary inputs have defaults, and those are behaviour choices rather than environment values.

`step-root` and `server-ca` are **public** CA certificates, not secrets; they sit in organization secrets for convenience only.

### `hosts` and ports

The port is the one your **local** tools connect to, and you rarely get to choose it: `ssh <host>` dials port 22 on its own, `curl https://<host>` dials 443. So it must be the target protocol's port, otherwise the tunnel listens somewhere the client never knocks and the connection is refused.

### `audience`

The `aud` claim of the OIDC token: who the token is meant for. GitHub signs a JWT saying "this run is `Jahia/<repo>` on such a ref", and the audience says "and it was minted for that broker". A token carrying anything else is refused, which is what stops a token obtained for another service (AWS, Vault...) from being replayed here, and vice versa.

### `canary-url` and `canary-http-response`

List one canary URL per tunnelled host: validating a single host would leave the other tunnels unproven, which is exactly what the canary exists to prevent.

By default **any HTTP response counts as a success**, because what the canary proves is that the tunnel carried the request; only the absence of a response (`000`) means a broken tunnel. Set `canary-http-response` when you do want a strict code, and it then applies to every URL.

Pick an endpoint that needs no authentication and has no side effect. Prefer a service's health endpoint, and prefer its shallowest form: a health check that also probes a database would fail your job for something the tunnel does perfectly well. This is the other reason the default accepts any response.

Note that this differs from [`vpn-tunnel`](../vpn-tunnel), whose `canary-http-response` defaults to `200`.

## Usage

An HTTPS example, reaching two internal services in the same job:

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # required: the action cannot grant this to itself
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Open the mTLS tunnel
        uses: jahia/jahia-modules-action/mtls-tunnel@v2
        with:
          hosts: |
            registry.internal.example.com
            api.internal.example.com
          ca-url: ${{ vars.CI_MTLS_CA_URL }}
          bastion: ${{ vars.CI_MTLS_BASTION }}
          server-name: ${{ vars.CI_MTLS_SERVER_NAME }}
          audience: ${{ vars.CI_MTLS_AUDIENCE }}
          step-root: ${{ secrets.CI_STEP_ROOT }}
          server-ca: ${{ secrets.CI_SERVER_CA }}
          # optional: fail here rather than in the middle of the job
          canary-url: |
            https://registry.internal.example.com/health
            https://api.internal.example.com/health

      # From here on nothing is tunnel-specific: both hosts resolve to the tunnel.
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform plan
```

An SSH host works the same way. Only the port changes, and the canary does not apply:

```yaml
      - uses: jahia/jahia-modules-action/mtls-tunnel@v2
        with:
          hosts: build-host.internal.example.com:22
          ca-url: ${{ vars.CI_MTLS_CA_URL }}
          bastion: ${{ vars.CI_MTLS_BASTION }}
          server-name: ${{ vars.CI_MTLS_SERVER_NAME }}
          audience: ${{ vars.CI_MTLS_AUDIENCE }}
          step-root: ${{ secrets.CI_STEP_ROOT }}
          server-ca: ${{ secrets.CI_SERVER_CA }}

      - run: ssh ci@build-host.internal.example.com 'uptime'
```

The tunnel only carries the connection: authenticating the SSH session itself (key, `known_hosts`) remains the caller's business.

Two things to keep in mind:

- **One call per job.** The tunnels live in the runner, not in the workflow: another job needing the same hosts calls the action again.
- **The action can be called several times in one job**, for instance to add a host later on. Loopback addresses come from a job-wide counter, a host already tunnelled on that port is skipped, and a host reached on a second port reuses its address.

## Testing

A test workflow lives at `.github/workflows/test-mtls-tunnel.yml`, triggered manually from **Actions → Test mTLS tunnel → Run workflow**. As for [`vpn-tunnel`](../vpn-tunnel), some jobs are meant to fail: what matters is that each behaves as its column says.

| Job | Expected | Covers |
|-----|----------|--------|
| `two-hosts` | ✅ Pass | Two hosts in one job, one canary each |
| `container` | ✅ Pass | The same inside a bare container image, which `vpn-tunnel` cannot do |
| `called-twice` | ✅ Pass | Second call skipping a tunnelled host, and a second port reusing its address |
| `no-oidc-permission` | ❌ Fail | The job forgets `id-token: write`, and gets the action's own error |
| `invalid-host` | ❌ Fail | A malformed entry, rejected before `/etc/hosts` is touched |
| `denied-host` | ❌ Fail | A host outside the target map: the tunnel opens, no traffic passes |

**It cannot run yet.** The broker allowlists the **calling** repository's OIDC claims, and `jahia-modules-action` is not on that list; asking IT for it is still to be done. Until then, the action is validated from a consumer repository that is already allowlisted, calling it by ref:

```yaml
- uses: jahia/jahia-modules-action/mtls-tunnel@<branch-or-tag>
```

Calling an external action does not change the claims presented to the broker, which is what makes both arrangements equivalent from its point of view.

The workflow expects two variables (the broker's coordinates, which move) and the two CA certificates as secrets. The hosts it targets are written in plain in the file.

## Limitations

- **Hosts must be allowlisted on the bastion.** Adding a new host to a workflow requires an IT change on the target map first; until then the connection fails closed.
- **The certificate lasts one hour and is not renewed in flight.** Jobs shorter than that are unaffected; a longer job would need a background renewal and a `stunnel` reload.
- **No teardown.** Composite actions have no `post` step, so `stunnel` keeps running and the `/etc/hosts` entries remain until the runner is discarded. Fine on ephemeral runners; on a persistent self-hosted runner, clean up explicitly at the end of the job.
- **The OIDC claims must match the broker's allowlist** (repository, and depending on the configuration the event and the ref). The action prints the claims it presents, so a rejection can be read directly against the allowlist.
