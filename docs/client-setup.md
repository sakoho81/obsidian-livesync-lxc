# Client Setup

Connecting Obsidian to your self-hosted CouchDB server.

> You need the following from your server setup:
> - **URI**: `http://<container-ip>:5984`
> - **Username**: `admin` (or whatever you configured)
> - **Password**: your configured password
> - **Database**: `obsidian` (or your database name)

## 1. Install the Plugin

1. Open Obsidian, go to **Settings** (bottom left gear icon)
2. Click **Community plugins**
3. Click **Turn on community plugins** (if not already enabled)
4. Click **Browse**, search for **Self-hosted LiveSync**
5. Click **Install**, then **Enable**

## 2. Open the Setup Wizard

1. In Settings, find **Self-hosted LiveSync** in the sidebar
2. Click the **Setup wizard** tab, then click **Start**

## 3. Configure Remote Database

| Setting | Value |
|---------|-------|
| Remote Type | `CouchDB` |
| URI | `http://YOUR_SERVER_IP:5984` |
| Username | `admin` (or your configured username) |
| Password | Your configured password |
| Database | `obsidian` (or your database name) |

Click **Test Database Connection** — you should see "Connected successfully."

## 4. Check and Fix

Click **Check and Fix** — this verifies CouchDB is configured correctly for LiveSync. Press all **Fix** buttons that appear. When everything shows green checkmarks, click **Apply**.

## 5. Enable End-to-End Encryption

> **Do this on your FIRST device before connecting any other device.**
> If you connect a second device without encryption, unencrypted data will sync and remain on the server.

1. On the **Confidentiality** step of the wizard, toggle **End-to-end Encryption** ON
2. Enter a **strong passphrase** — memorise it or store it in a password manager
3. Toggle **Path Obfuscation** ON (recommended — hides filenames on the server)
4. Click **Apply**

## 6. Enable Sync

1. In the **Sync Settings** tab, set **Sync Mode** to `LiveSync`
2. Click **Apply**
3. The status bar should show **Sync: ⚡** or **Sync: 💤**

## 7. First Sync

- Initial sync may take a while — the status bar shows progress indicators
- Wait for all indicators to clear before closing Obsidian
- Do **not** close Obsidian or put your device to sleep during the first sync

## 8. Subsequent Devices

Once your first device is configured, use a **Setup URI** to configure other devices in one click. See [Setup URI](./setup-uri.md).

For mobile devices (iOS/Android), you need HTTPS — see [HTTPS Reverse Proxy](./https-reverse-proxy.md).

## Status Bar Indicators

| Icon | Meaning |
|------|---------|
| ⚡ | Sync in progress |
| 💤 | LiveSync enabled, waiting for changes |
| ⏹️ | Sync stopped |
| ⚠️ | An error occurred |
| 📥 | Incoming items being processed |
| 📄 | Database operations in progress |
| 🧩 | Waiting for chunks |
