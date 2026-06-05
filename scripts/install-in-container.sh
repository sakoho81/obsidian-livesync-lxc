#!/bin/bash
#
# In-container install script for Obsidian LiveSync.
# Run inside a Debian LXC container or standalone Debian/Ubuntu machine.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/sakoho81/obsidian-livesync-lxc/main/scripts/install-in-container.sh | bash
#
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

log_info "Installing prerequisites..."
apt-get update -qq
apt-get install -y -qq curl git

log_info "Installing uv..."
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

log_info "Cloning obsidian-livesync-lxc..."
if [[ ! -d /opt/obsidian-livesync ]]; then
    git clone https://github.com/sakoho81/obsidian-livesync-lxc /opt/obsidian-livesync
fi

log_info "Installing obsidian-livesync tool..."
uv tool install /opt/obsidian-livesync

log_info "Installing CouchDB and LiveSync..."
obsidian-livesync install
