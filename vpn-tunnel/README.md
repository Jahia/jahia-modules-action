# VPN Tunnel Action

A composite GitHub Action to establish a WireGuard VPN tunnel on a runner.

## Description

This action sets up a WireGuard VPN tunnel using a base64-encoded configuration file. It supports both `ubuntu-latest` and `self-hosted` runners (but **not** containerized jobs).

The action will:
1. Verify it is **not** running inside a container (WireGuard requires kernel-level access)
2. Install WireGuard and its dependencies
3. Configure and bring up the VPN interface
4. Optionally validate connectivity by calling a canary URL

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `config-base64` | A base64-encoded WireGuard configuration. Generate with `base64 -i wg0.conf -o -` | ✅ | — |
| `canary-url` | A URL to validate the VPN connection. The action fails if the response code doesn't match `canary-http-response`. | ❌ | `''` |
| `canary-http-response` | The expected HTTP status code when calling the canary URL | ❌ | `200` |
| `canary-retries` | Number of retry attempts if the canary check fails | ❌ | `5` |

## Usage

```yaml
steps:
  - uses: jahia/jahia-modules-action/vpn-tunnel@v2
    with:
      config-base64: ${{ secrets.JC_WIREGUARD_VPN }}
      canary-url: https://app.dev.j.jahia.com
```

## Limitations

- **Cannot run inside a container.** The action requires direct access to the host's network stack to configure WireGuard interfaces. If it detects a container environment (Docker, LXC, containerd, etc.), it will exit with an error.

## Testing

A test workflow is available at `.github/workflows/test-vpn-tunnel.yml`. It can be **triggered manually** via `workflow_dispatch` from the Actions tab.

The workflow contains multiple jobs covering different scenarios:

| Job | Runner | Expected Result | Description |
|-----|--------|-----------------|-------------|
| `direct-ul-good-url` | `ubuntu-latest` | ✅ Pass | VPN up, validates against a public URL |
| `vpn-ul-wrong-url` | `ubuntu-latest` | ❌ Fail | VPN up, canary points to an invalid URL |
| `vpn-ul-good-url` | `ubuntu-latest` | ✅ Pass | VPN up, validates against an internal URL |
| `vpn-sh-wrong-url` | `self-hosted` | ❌ Fail | VPN up on self-hosted, invalid canary URL |
| `vpn-sh-good-url` | `self-hosted` | ✅ Pass | VPN up on self-hosted, valid canary URL |
| `vpn-sh-good-url-container` | `self-hosted` (container) | ❌ Fail | Demonstrates that containerized runs are not supported |

To trigger the test workflow, navigate to **Actions → Test VPN tunnel → Run workflow**.