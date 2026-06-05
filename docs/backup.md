# Backup

## Full Container Backup (Proxmox)

From the Proxmox host:

```bash
vzdump CT_ID --compress zstd --dumpdir /path/to/backups
```

Restore later:

```bash
pct restore NEW_CT_ID /path/to/backups/vzdump-lxc-CT_ID-*.tar.zst
pct start NEW_CT_ID
```

## Database-Only Backup

Export a CouchDB database as JSON. From the Proxmox host:

```bash
pct exec CT_ID -- bash -c "
source /root/.obsidian-livesync-credentials
curl -s http://\${COUCHDB_USER}:\${COUCHDB_PASSWORD}@localhost:5984/obsidian/_all_docs?include_docs=true > /root/obsidian-backup.json
"
```

Or from inside the container:

```bash
source /root/.obsidian-livesync-credentials
curl -s "http://${COUCHDB_USER}:${COUCHDB_PASSWORD}@localhost:5984/${DATABASE_NAME}/_all_docs?include_docs=true" > ~/obsidian-backup.json
```

## Automated Backups (Cron)

Add a nightly cron job inside the container:

```bash
cat > /etc/cron.d/obsidian-backup << 'EOF'
0 3 * * * root source /root/.obsidian-livesync-credentials && curl -s "http://${COUCHDB_USER}:${COUCHDB_PASSWORD}@localhost:5984/${DATABASE_NAME}/_all_docs?include_docs=true" > /root/backups/obsidian-$(date +\%Y\%m\%d).json
EOF

mkdir -p /root/backups
```

> Note: the `%` signs must be escaped as `\%` inside a crontab file.

## Restore

CouchDB does not have a built-in bulk restore for `_all_docs` exports. The simplest approach is to restore the entire container from a `vzdump` backup.

If you need to restore individual notes, install the [obsidian-livesync-backup](https://github.com/vrtmrz/obsidian-livesync-backup) plugin in Obsidian.
