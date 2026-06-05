#!/usr/bin/env bash
#
# Obsidian LiveSync LXC Bootstrap
# Runs on the Proxmox host — creates a container and installs CouchDB + LiveSync.
#
# Usage:
#   bash bootstrap.sh
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${CYAN}[STEP]${NC} $1"; }

# ── Checks ──────────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root on the Proxmox host."
    exit 1
fi

if ! command -v pveversion &>/dev/null; then
    log_error "This script must be run on a Proxmox VE host."
    exit 1
fi

# ── Interactive configuration ───────────────────────────────────────────

echo ""
log_step "Container Configuration"
echo ""

# Find next available VMID
DEFAULT_CT_ID=100
while pct status "$DEFAULT_CT_ID" &>/dev/null || qm status "$DEFAULT_CT_ID" &>/dev/null; do
    ((DEFAULT_CT_ID++))
done
read -p "Container ID [${DEFAULT_CT_ID}]: " CT_ID
CT_ID=${CT_ID:-$DEFAULT_CT_ID}

read -p "Hostname [obsidian-livesync]: " HOSTNAME
HOSTNAME=${HOSTNAME:-obsidian-livesync}

while true; do
    read -s -p "Container root password: " PASSWORD
    echo ""
    if [[ -z "$PASSWORD" ]]; then
        log_warn "Password cannot be empty."
        continue
    fi
    read -s -p "Confirm password: " PASSWORD_CONFIRM
    echo ""
    if [[ "$PASSWORD" == "$PASSWORD_CONFIRM" ]]; then
        break
    fi
    log_warn "Passwords do not match."
done

echo ""
log_step "Resource Configuration"
echo ""

read -p "Disk size in GB [4]: " DISK_SIZE
DISK_SIZE=${DISK_SIZE:-4}

read -p "RAM in MB [512]: " RAM
RAM=${RAM:-512}

read -p "CPU cores [1]: " CORES
CORES=${CORES:-1}

# Storage
echo ""
echo "Available storage for containers:"
STORAGES=$(pvesm status -content rootdir | awk 'NR>1 {print $1}')
echo "$STORAGES" | nl -w2 -s") "
DEFAULT_STORAGE="local-lvm"
echo "$STORAGES" | grep -q "local-lvm" || DEFAULT_STORAGE=$(echo "$STORAGES" | head -1)
read -p "Select storage number [${DEFAULT_STORAGE}]: " STORAGE_NUM
if [[ -n "$STORAGE_NUM" ]]; then
    STORAGE=$(echo "$STORAGES" | sed -n "${STORAGE_NUM}p")
fi
STORAGE=${STORAGE:-$DEFAULT_STORAGE}

# Network
echo ""
echo "Available bridges:"
BRIDGES=$(ip -o link show type bridge | awk -F': ' '{print $2}')
echo "$BRIDGES" | nl -w2 -s") "
DEFAULT_BRIDGE="vmbr0"
echo "$BRIDGES" | grep -q "vmbr0" || DEFAULT_BRIDGE=$(echo "$BRIDGES" | head -1)
read -p "Select bridge number [${DEFAULT_BRIDGE}]: " BRIDGE_NUM
if [[ -n "$BRIDGE_NUM" ]]; then
    BRIDGE=$(echo "$BRIDGES" | sed -n "${BRIDGE_NUM}p")
fi
BRIDGE=${BRIDGE:-$DEFAULT_BRIDGE}

# Network — static IP by default, last octet = container ID
echo ""
HOST_IP=$(hostname -I | awk '{print $1}')
HOST_PREFIX="${HOST_IP%.*}."

echo ""
echo "IP Configuration:"
echo "1) Static IP — ${HOST_PREFIX}${CT_ID} (recommended)"
echo "2) DHCP"
read -p "Select [1]: " IP_CONFIG
IP_CONFIG=${IP_CONFIG:-1}

if [[ "$IP_CONFIG" == "2" ]]; then
    NET_CONFIG="name=eth0,bridge=${BRIDGE},ip=dhcp"
else
    DEFAULT_STATIC_IP="${HOST_PREFIX}${CT_ID}/24"
    read -p "IP Address [${DEFAULT_STATIC_IP}]: " STATIC_IP
    STATIC_IP=${STATIC_IP:-$DEFAULT_STATIC_IP}
    read -p "Gateway [$(ip route | grep default | awk '{print $3}')]: " GATEWAY
    GATEWAY=${GATEWAY:-$(ip route | grep default | awk '{print $3}')}
    NET_CONFIG="name=eth0,bridge=${BRIDGE},ip=${STATIC_IP},gw=${GATEWAY}"
fi

# CouchDB credentials
echo ""
log_step "CouchDB Configuration"
echo ""

read -p "CouchDB admin username [admin]: " COUCHDB_USER
COUCHDB_USER=${COUCHDB_USER:-admin}

while true; do
    read -s -p "CouchDB admin password: " COUCHDB_PASSWORD
    echo ""
    if [[ -z "$COUCHDB_PASSWORD" ]]; then
        log_warn "Password cannot be empty."
        continue
    fi
    read -s -p "Confirm password: " COUCHDB_PASSWORD_CONFIRM
    echo ""
    if [[ "$COUCHDB_PASSWORD" == "$COUCHDB_PASSWORD_CONFIRM" ]]; then
        break
    fi
    log_warn "Passwords do not match."
done

read -p "Database name [obsidian]: " DATABASE_NAME
DATABASE_NAME=${DATABASE_NAME:-obsidian}

# Template
echo ""
echo "Updating template list..."
pveam update &>/dev/null || true

TEMPLATE_STORAGE="local"
TEMPLATES=$(pveam available -section system | grep -E "debian-1[12]" | awk '{print $2}' | sort -V | tail -5)
if [[ -z "$TEMPLATES" ]]; then
    log_error "No Debian templates found. Please download one first."
    exit 1
fi

echo ""
echo "Available templates:"
echo "$TEMPLATES" | nl -w2 -s") "
DEFAULT_TEMPLATE=$(echo "$TEMPLATES" | tail -1)
read -p "Select template number [${DEFAULT_TEMPLATE}]: " TEMPLATE_NUM
if [[ -z "$TEMPLATE_NUM" ]]; then
    TEMPLATE="$DEFAULT_TEMPLATE"
else
    TEMPLATE=$(echo "$TEMPLATES" | sed -n "${TEMPLATE_NUM}p")
fi

# Download template if needed
if ! pveam list "$TEMPLATE_STORAGE" | grep -q "$TEMPLATE"; then
    log_info "Downloading template..."
    pveam download "$TEMPLATE_STORAGE" "$TEMPLATE"
fi

# ── Confirmation ────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${CYAN}           Configuration Summary              ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo ""
echo "Container:"
echo "  ID:        $CT_ID"
echo "  Hostname:  $HOSTNAME"
echo "  Disk:      ${DISK_SIZE}GB"
echo "  RAM:       ${RAM}MB"
echo "  CPU:       ${CORES} core(s)"
echo "  Storage:   $STORAGE"
echo "  Network:   $NET_CONFIG"
echo ""
echo "CouchDB:"
echo "  Username:  $COUCHDB_USER"
echo "  Database:  $DATABASE_NAME"
echo ""

read -p "Create container with these settings? [Y/n]: " CONFIRM
CONFIRM=${CONFIRM:-Y}
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    log_info "Aborted."
    exit 0
fi

# ── Create and start the container ──────────────────────────────────────

log_step "Creating container..."
pct create "$CT_ID" "${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE}" \
    --hostname "$HOSTNAME" \
    --password "$PASSWORD" \
    --rootfs "${STORAGE}:${DISK_SIZE}" \
    --memory "$RAM" \
    --cores "$CORES" \
    --net0 "$NET_CONFIG" \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1 \
    --start 0

log_info "Container $CT_ID created."

log_step "Starting container..."
pct start "$CT_ID"

log_info "Waiting for container to boot..."
for i in $(seq 1 30); do
    sleep 2
    CT_IP=$(pct exec "$CT_ID" -- hostname -I 2>/dev/null | awk '{print $1}' || true)
    if [[ -n "$CT_IP" ]]; then
        break
    fi
done

if [[ -z "${CT_IP:-}" ]]; then
    log_error "Container did not get an IP address."
    exit 1
fi

log_info "Container IP: $CT_IP"

# ── Push the repo and install script ────────────────────────────────────

log_step "Pushing repo and install script to container..."

SCRIPT_DIR="$(dirname "$0")"
IN_CONTAINER_SCRIPT="${SCRIPT_DIR}/scripts/install-in-container.sh"

# Push the entire repo as a tarball (exclude .git)
REPO_TARBALL="/tmp/obsidian-livesync-repo.tar.gz"
tar czf "$REPO_TARBALL" -C "$SCRIPT_DIR" --exclude .git .
pct push "$CT_ID" "$REPO_TARBALL" /tmp/repo.tar.gz
pct exec "$CT_ID" -- mkdir -p /opt/obsidian-livesync
pct exec "$CT_ID" -- tar xzf /tmp/repo.tar.gz -C /opt/obsidian-livesync
rm -f "$REPO_TARBALL"

# Push the install script
pct push "$CT_ID" "$IN_CONTAINER_SCRIPT" /tmp/install.sh

pct exec "$CT_ID" -- bash -c "
    mkdir -p /root
    cat > /root/.obsidian-livesync-credentials << 'EOF'
COUCHDB_USER=${COUCHDB_USER}
COUCHDB_PASSWORD=${COUCHDB_PASSWORD}
DATABASE_NAME=${DATABASE_NAME}
COUCHDB_PORT=5984
EOF
    chmod 600 /root/.obsidian-livesync-credentials
"

log_step "Running install script in container..."
pct exec "$CT_ID" -- bash /tmp/install.sh

# ── Success ─────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "Container Details:"
echo "  ID:       $CT_ID"
echo "  Hostname: $HOSTNAME"
echo "  IP:       $CT_IP"
echo ""
echo "CouchDB Admin Interface:"
echo "  URL: http://${CT_IP}:5984/_utils"
echo ""
echo -e "${CYAN}Obsidian LiveSync Settings:${NC}"
echo "  URI:      http://${CT_IP}:5984"
echo "  Username: ${COUCHDB_USER}"
echo "  Password: (as configured)"
echo "  Database: ${DATABASE_NAME}"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  1. For mobile devices, set up HTTPS via reverse proxy"
echo "  2. Enable End-to-End Encryption in the LiveSync plugin"
echo ""
echo "Access container: pct enter $CT_ID"
echo "Manage databases: pct exec $CT_ID -- uv --project /opt/obsidian-livesync run obsidian-livesync db --help"
echo ""
