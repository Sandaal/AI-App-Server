# Confidential apps

A confidential app runs only on servers that prove, with hardware attestation, what they are running on: an AMD SEV-SNP or Intel TDX confidential VM. With a key broker, the app's data key is released only to such servers, so a copy of the data folder, or a server outside a confidential VM, can't read the app's data. Audit records carry the attestation, so an auditor can check where the data was processed.

## Mark an app confidential

```yaml
app: payroll
confidential: {}
```

To accept only specific VM images, list their launch measurements (hex, from your cloud's attestation tooling or `aiapp audit --type node_attestation --json`):

```yaml
confidential:
  measurements: [9f2c…e1, 4ab0…77]
```

A server that can't attest refuses to run the app:

```text
$ aiapp deploy
payroll: confidential app: this node can't prove what it runs on (not a confidential VM (no SEV-SNP or TDX guest))
```

In a cluster, the app is placed only on nodes whose attestation meets its policy. Other nodes forward its requests to them.

## How a server attests

The server uses Linux's configfs-tsm interface (Linux 6.7 or later, inside an SEV-SNP or TDX guest, with configfs mounted). For each confidential app it:

1. creates a fresh report that carries a challenge;
2. checks that the report answers that challenge;
3. checks that the launch measurement is on the app's list.

`aiapp hardware` shows whether the server can attest:

```text
Attestation: sev-snp (configfs-tsm); key broker on; confidential apps: [payroll]
```

## Release keys only to attested servers

Start the server with a key broker:

```bash
AIAPP_KEY_BROKER_TOKEN=… aiapp serve --key-broker https://kbs.example.com
```

For each confidential app, the server:

1. gets a challenge from the broker;
2. answers it with a fresh attestation report;
3. receives a 32-byte key, if the broker's policy accepts the report;
4. wraps the app's data key with that key instead of the server's master key.

From then on, the app's data can be read only by a server the broker has released the key to. Apps already holding data are rewrapped in place.

Failures are refusals:

- **The broker refuses:** the app doesn't start.
- **A server starts without `--key-broker`:** it doesn't start the app either. The app's data key is held by the broker, so the data stays sealed even to someone with the master key.

The broker protocol is two JSON calls:

| Call | Body | Answer |
|---|---|---|
| `POST /challenge` | `{"app": "payroll"}` | `{"nonce": "<base64>"}` |
| `POST /release` | `{"app": "payroll", "evidence": {"platform", "nonce", "report", "measurement", …}}` | `{"key": "<base64, 32 bytes>"}`, or 401/403 to refuse |

The broker must verify the report's signature chain (AMD's VCEK certificates for SEV-SNP, Intel's PCK certificates for TDX), the challenge it issued, and its policy for the app. The server checks the challenge and the measurement, but not the vendor signature chain. Adapters for Azure Key Vault secure key release and HashiCorp Vault are planned; meanwhile a small service in front of them can speak this protocol.

## Audit

- **At startup:** an attested server records its evidence once (`type: node_attestation`, with the report). Every later audit record carries `attestation: <platform>:<evidence digest>` pointing at it.
- **Per app:** each confidential app's admission is recorded (`type: attestation`), with the report it was admitted with and whether the broker released its key.

## Limits in this version

- **What the released key protects:** the app's key-value data, memory and data structures. Vectors and files use the server's own keys.
- **Untested on hardware:** SEV-SNP and TDX have been tested with an emulated platform only (`AIAPP_ATTESTATION=emulated-sev-snp`). The report formats follow the vendors' specifications.
- **Evidence between cluster nodes:** nodes show each other standing evidence bound to their address, not a fresh challenge. Key release always uses a fresh challenge.
- **Emulated platforms prove nothing:** their signing key is public. A server accepts emulated evidence only when it is itself emulated (tests and demos).
