# HTTPS for Mobile Devices

Obsidian on iOS and Android requires **HTTPS** to connect to the LiveSync server. Desktop Obsidian (Electron) works fine with plain HTTP, but if you want to sync to a phone or tablet, you need a reverse proxy with SSL.

## Option 1: Nginx Proxy Manager (Easiest)

1. Install [Nginx Proxy Manager](https://nginxproxymanager.com/) on Proxmox or another host
2. Add a **Proxy Host**:
   - Domain: `obsidian.yourdomain.com`
   - Forward IP: your CouchDB container IP
   - Forward Port: `5984`
   - Enable **SSL** with Let's Encrypt
3. Point your domain's DNS A record at the NPM host
4. In Obsidian, use `https://obsidian.yourdomain.com` as the URI

No path needed — NPM forwards the root directly to CouchDB.

## Option 2: Cloudflare Tunnel

No open ports needed. Cloudflare handles SSL automatically.

```bash
# In the LXC container
pct enter CT_ID

# Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared.deb

# Create and configure tunnel
cloudflared tunnel login     # opens browser, pick your domain
cloudflared tunnel create obsidian
cloudflared tunnel route dns obsidian obsidian.yourdomain.com
cloudflared tunnel run --url http://localhost:5984 obsidian
```

Use `https://obsidian.yourdomain.com` as the URI in Obsidian.

## Option 3: Caddy (Auto HTTPS)

Install Caddy directly in the container. It fetches Let's Encrypt certificates automatically.

```bash
# In the LXC container
apt install -y caddy
cat > /etc/caddy/Caddyfile << 'EOF'
obsidian.yourdomain.com {
    reverse_proxy localhost:5984
}
EOF
systemctl restart caddy
```

Point your domain's DNS at the container's public IP (or internal IP if on your LAN — you can use split DNS or a local DNS resolver).

## Option 4: Tailscale

If you use Tailscale, Caddy can use Tailscale's HTTPS certificates with zero public exposure:

```bash
apt install -y caddy
cat > /etc/caddy/Caddyfile << 'EOF'
<container-tailscale-ip>.ts.net {
    reverse_proxy localhost:5984
}
EOF
systemctl restart caddy
```

## Testing HTTPS

After setting up any option, verify from a browser:

```
https://obsidian.yourdomain.com
```

You should see CouchDB's welcome JSON: `{"couchdb":"Welcome","version":"...","vendor":{"name":"..."}}`

Then use this HTTPS URL in both desktop and mobile Obsidian clients.
