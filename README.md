# Obsidian LiveSync LXC for Proxmox

Self-hosted Obsidian sync using CouchDB in a Proxmox LXC container.

Sync your Obsidian notes across all devices instantly with end-to-end encryption — completely self-hosted on your own server.

Based on the [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync) plugin by vrtmrz.

## Features

- **Instant sync** between all your Obsidian devices
- **End-to-end encryption** — your notes stay private
- **Self-hosted** — no cloud services, your data stays on your server
- **Lightweight** — runs in a small LXC container (512MB RAM)
- **Easy setup** — interactive bootstrap script handles everything

## Quick Start

On your **Proxmox host**:

```bash
git clone https://github.com/sakoho81/obsidian-livesync-lxc.git
cd obsidian-livesync-lxc
bash bootstrap.sh
```

The script will prompt for container configuration, create the LXC, and install CouchDB with LiveSync settings.

After completion, you'll see:

```
Container Details:
  ID:       102
  Hostname: obsidian-livesync
  IP:       192.168.1.102

CouchDB Admin Interface:
  URL: http://192.168.1.102:5984/_utils

Obsidian LiveSync Settings:
  URI:      http://192.168.1.102:5984
  Username: admin
  Database: obsidian
```

Next: [Set up the Obsidian client](docs/client-setup.md).

## CLI Reference

The `obsidian-livesync` tool runs inside the container (after `pct enter` or via `pct exec`):

```
obsidian-livesync install      # Install CouchDB + configure LiveSync
obsidian-livesync setup-uri    # Generate an obsidian://setuplivesync URI
obsidian-livesync db create/delete/list  # Manage databases
obsidian-livesync check        # Verify CouchDB LiveSync config
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Client Setup](docs/client-setup.md) | Install the plugin, configure the remote database, enable encryption and sync |
| [Setup URIs](docs/setup-uri.md) | One-click device setup with `obsidian://setuplivesync` URIs |
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

### Manual in-container install

If you have an existing Debian LXC container:

```bash
git clone https://github.com/sakoho81/obsidian-livesync-lxc.git /opt/obsidian-livesync
cd /opt/obsidian-livesync
uv tool install .
obsidian-livesync install
```

### Development

```bash
git clone https://github.com/sakoho81/obsidian-livesync-lxc.git
cd obsidian-livesync-lxc
uv sync --group dev
uv run pytest
uv run pre-commit run --all-files
```

## Files

```
obsidian-livesync-lxc/
├── bootstrap.sh                # Proxmox host entry point
├── pyproject.toml              # Python project definition
├── src/obsidian_livesync/      # Python package
│   ├── cli.py                  # CLI (install, db, setup-uri, check)
│   ├── config.py               # Credential management
│   ├── couchdb.py              # CouchDB operations
│   └── setup_uri.py            # Setup URI generation
├── tests/                      # pytest test suite
├── docs/                       # Documentation
└── .github/workflows/          # CI
```

## Credits

- [Obsidian](https://obsidian.md/) — The note-taking app
- [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync) by vrtmrz
- [CouchDB](https://couchdb.apache.org/) — The database

## License

MIT License — See [LICENSE](LICENSE) for details.

## Contributing

Issues and pull requests welcome!

1. Fork the repo
2. Create a feature branch
3. Submit a PR
