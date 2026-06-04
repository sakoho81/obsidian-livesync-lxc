# Obsidian LiveSync LXC for Proxmox

One-command deployment of self-hosted Obsidian sync using CouchDB in a Proxmox LXC container.

Sync your Obsidian notes across all devices instantly with end-to-end encryption — completely self-hosted on your own server.

Based on the [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync) plugin by vrtmrz.

## Features

- **Instant sync** between all your Obsidian devices
- **End-to-end encryption** — your notes stay private
- **Self-hosted** — no cloud services, your data stays on your server
- **Lightweight** — runs in a small LXC container (512MB RAM)
- **Easy setup** — interactive script handles everything

## Quick Start

Run this command on your **Proxmox host**:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ril3y/obsidian-livesync-lxc/main/obsidian-livesync-lxc.sh)"
```

The script will:

1. Create an LXC container
2. Install and configure CouchDB
3. Apply all LiveSync-compatible settings
4. Create your Obsidian database

After completion, you'll see:

```
Container Details:
  ID:       102
  Hostname: obsidian-livesync
  IP:       192.168.1.110

CouchDB Admin Interface:
  URL: http://192.168.1.110:5984/_utils

Obsidian LiveSync Settings:
  URI:      http://192.168.1.110:5984
  Username: admin
  Database: obsidian
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Client Setup](docs/client-setup.md) | Install the plugin, configure the remote database, enable encryption and sync |
| [Setup URIs](docs/setup-uri.md) | One-click device setup with `obsidian://setuplivesync` URIs (GUI or CLI) |
| [Multiple Databases](docs/multiple-databases.md) | One vault = one CouchDB database. Create via Fauxton web UI or CLI |
| [HTTPS Reverse Proxy](docs/https-reverse-proxy.md) | Required for mobile (iOS/Android). NPM, Cloudflare Tunnel, Caddy, Tailscale |
| [Backup](docs/backup.md) | Full container backup with `vzdump`, database-only export, cron automation |
| [Troubleshooting](docs/troubleshooting.md) | Common issues, logs, configuration dumps, reset |

## Container Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM      | 256MB   | 512MB        |
| Disk     | 2GB     | 4-8GB        |
| CPU      | 1 core  | 1 core       |

## Alternative Installation Methods

### Install on Existing LXC

If you have an existing Debian/Ubuntu LXC container:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ril3y/obsidian-livesync-lxc/main/scripts/install.sh)"
```

### Use Pre-built Template

1. Download from [Releases](https://github.com/ril3y/obsidian-livesync-lxc/releases)
2. Copy to Proxmox:
   ```bash
   scp obsidian-livesync-*.tar.zst root@proxmox:/var/lib/vz/template/cache/
   ```
3. Restore:
   ```bash
   pct restore 102 /var/lib/vz/template/cache/obsidian-livesync-*.tar.zst
   pct start 102
   pct enter 102
   /root/setup-couchdb.sh
   ```

## Files

```
obsidian-livesync-lxc/
├── obsidian-livesync-lxc.sh    # Main Proxmox installer
├── scripts/
│   ├── install.sh              # Standalone CouchDB installer
│   ├── create-database.sh      # Add databases for more vaults
│   └── create-template.sh      # Export as shareable template
├── docs/
│   ├── client-setup.md
│   ├── setup-uri.md
│   ├── multiple-databases.md
│   ├── https-reverse-proxy.md
│   ├── backup.md
│   └── troubleshooting.md
├── README.md
└── LICENSE
```

## Credits

- [Obsidian](https://obsidian.md/) — The note-taking app
- [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync) by vrtmrz
- [CouchDB](https://couchdb.apache.org/) — The database
- Original guide from r/selfhosted community

## License

MIT License — See [LICENSE](LICENSE) for details.

## Contributing

Issues and pull requests welcome!

1. Fork the repo
2. Create a feature branch
3. Submit a PR
