# Multiple Databases

Each Obsidian **vault** needs its own CouchDB database. If you have separate vaults for work, personal, study, etc., create a database for each one.

> **For multiple people:** Create a separate LXC container per person for real credential isolation. See [note below](#multiple-people).

## Default: Use Fauxton Web UI

The easiest way. Open a browser, go to `http://<your-container-ip>:5984/_utils`:

1. Log in with your admin username and password
2. Click **Create Database** in the left sidebar
3. Type a name (e.g. `obsidian-work`, `obsidian-study`)
4. Click **Create**

Done. No SSH, no Proxmox access needed.

## Alternative: CLI

From the Proxmox host:

```bash
pct enter YOUR_CT_ID
/root/obsidian-livesync/scripts/create-database.sh
```

You will be prompted for a database name. CouchDB naming rules: must start with a lowercase letter, and can contain `a-z`, `0-9`, `_`, `$`, `(`, `)`, `+`, `-`, `/`.

## Connect a Vault to the New Database

1. Open Obsidian with the vault you want to connect
2. Go to Settings → Self-hosted LiveSync → Setup wizard
3. Enter the **same** URI, username, and password as your other vault
4. Enter the **new database name** (e.g., `obsidian-work`)
5. Test connection, Check and Fix, Apply
6. Enable E2E encryption — set a passphrase (can be the same or different from other vaults)
7. Enable LiveSync

## Propagating Settings with Setup URIs

If you already have a working vault configured, you do not need to manually enter everything again:

1. In your configured vault, open Command Palette → **"Copy current settings as a new setup URI"**
2. Enter a passphrase to encrypt the URI
3. In the new vault, go to Setup wizard → **Use**
4. Paste the URI, enter the passphrase
5. When prompted **"How would you like to set it up?"**, choose **"Set it up as secondary or subsequent device"**

## Multiple People

The CouchDB instance uses a single admin account for all databases. Anyone with the admin credentials can access every database through Fauxton.

If different people will use the server, create a **separate LXC container** for each person. Run `obsidian-livesync-lxc.sh` again with a new container ID — each person gets their own CouchDB instance with their own admin username and password.

Do **not** share the same CouchDB instance between different people — the end-to-end encryption passphrase is the only privacy boundary, and sharing an admin account removes database-level isolation.
