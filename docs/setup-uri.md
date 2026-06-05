# Setup URIs

A setup URI is an encrypted snapshot of your LiveSync configuration — database address, credentials, sync mode, and encryption settings — all packed into a single `obsidian://setuplivesync?settings=...` link. Paste it into the Setup Wizard on any device for one-click configuration.

## Method 1: From Obsidian GUI (Recommended)

Use this after you have configured your first device.

1. Open Command Palette (`Ctrl+P` / `Cmd+P`)
2. Run **"Self-hosted LiveSync: Copy current settings as a new setup URI"**
3. Enter a **passphrase** to encrypt the URI — this can be anything memorable (a short phrase like "blue-frog-42" works)
4. The setup URI is copied to your clipboard

> **Important:** Save this passphrase somewhere safe. You will need it on every new device to decrypt and import the URI.

On a new device:

1. Install the plugin, open Settings → Self-hosted LiveSync → Setup wizard
2. Click **Use** (or run "Use the copied setup URI" from the Command Palette)
3. Paste the `obsidian://setuplivesync...` URI
4. Enter the passphrase you set when creating the URI
5. Choose **"Set it up as secondary or subsequent device"**
6. Wait for initialisation, then **Reload app without saving**

## Method 2: From CLI

Generate a setup URI from inside the container — no Obsidian GUI needed.

```bash
pct enter CT_ID
obsidian-livesync setup-uri \
  --hostname http://CONTAINER_IP:5984 \
  --database obsidian \
  --username admin \
  --password YOUR_PASSWORD
```

The command outputs:

```
Setup URI passphrase: patient-haze
Save this passphrase! You'll need it to import the URI on new devices.

obsidian://setuplivesync?settings=...
```

To set a custom E2E passphrase for the vault, add `--passphrase`:

```bash
obsidian-livesync setup-uri --hostname ... --database ... --password ... --passphrase "my-secret"
```

## Passphrase types explained

There are **three** passphrases in play. Do not confuse them:

| Passphrase | Where used | Purpose |
|-----------|-----------|---------|
| **URI passphrase** | Auto-generated (or set via `--passphrase`) | Encrypts/decrypts the setup URI itself. You type this when importing. |
| **E2E passphrase** | Set in the Obsidian plugin | Encrypts your vault contents before upload. Must be identical on ALL devices. |
| **CouchDB admin password** | Set during server install | Authenticates HTTP requests to CouchDB. Never leaves the config form. |

> When `--passphrase` is empty, the CLI auto-generates a readable one (e.g. `patient-haze`). The Obsidian GUI method prompts you to choose one yourself.
