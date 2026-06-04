"""LXC container management via proxmoxer and pct."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from proxmoxer import ProxmoxAPI  # type: ignore


class ContainerManager:
    def __init__(self, proxmox: ProxmoxAPI, node: str):
        self.proxmox = proxmox
        self.node = node

    def get_next_ct_id(self) -> int:
        """Find the next available VMID (>= 100)."""
        used = set()
        for vm in self.proxmox.nodes(self.node).qemu.get():
            used.add(int(vm["vmid"]))
        for ct in self.proxmox.nodes(self.node).lxc.get():
            used.add(int(ct["vmid"]))
        vmid = 100
        while vmid in used:
            vmid += 1
        return vmid

    def list_templates(self) -> list[dict[str, str]]:
        """List available Debian 11/12 container templates."""
        templates = self.proxmox.nodes(self.node).aplinfo.get()
        debian_templates = []
        for t in templates:
            if "debian-1" in (t.get("template", "")):
                debian_templates.append(t)
        debian_templates.sort(
            key=lambda t: t.get("template", ""), reverse=True
        )
        return debian_templates

    def list_storage(self, content_type: str = "rootdir") -> list[str]:
        """List available storage pools for a given content type."""
        storages = self.proxmox.nodes(self.node).storage.get()
        available = []
        for s in storages:
            if content_type in (s.get("content", "")):
                available.append(s["storage"])
        return available

    def list_bridges(self) -> list[str]:
        """List available network bridges on the host."""
        result = subprocess.run(
            ["ip", "-o", "link", "show", "type", "bridge"],
            capture_output=True,
            text=True,
        )
        bridges = []
        for line in result.stdout.splitlines():
            parts = line.split(": ")
            if len(parts) >= 2:
                bridges.append(parts[1])
        return bridges

    def create_container(
        self,
        vmid: int,
        hostname: str,
        root_password: str,
        template: str,
        storage: str,
        disk: int,
        ram: int,
        cores: int,
        net_config: str,
    ) -> None:
        """Create and configure an LXC container."""
        self.proxmox.nodes(self.node).lxc.post(
            vmid=vmid,
            hostname=hostname,
            password=root_password,
            ostemplate=template,
            storage=storage,
            rootfs=f"{storage}:{disk}",
            memory=ram,
            cores=cores,
            net0=net_config,
            unprivileged=1,
            features="nesting=1",
            onboot=1,
            start=0,
        )

    def start_container(self, vmid: int) -> None:
        """Start a container and wait for networking."""
        subprocess.run(
            ["pct", "start", str(vmid)],
            capture_output=True,
            text=True,
            check=True,
        )
        for _ in range(30):
            time.sleep(2)
            try:
                ip = self.get_container_ip(vmid)
                if ip:
                    return
            except Exception:
                pass
        raise RuntimeError(f"Container {vmid} failed to get an IP address")

    def stop_container(self, vmid: int) -> None:
        """Stop a container."""
        subprocess.run(
            ["pct", "stop", str(vmid)],
            capture_output=True,
            text=True,
            check=True,
        )

    def get_container_ip(self, vmid: int) -> str:
        """Get the primary IP address of a container."""
        result = subprocess.run(
            ["pct", "exec", str(vmid), "--", "hostname", "-I"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split()[0]

    def exec_in_container(self, vmid: int, command: str) -> subprocess.CompletedProcess[str]:
        """Execute a command inside a container."""
        return subprocess.run(
            ["pct", "exec", str(vmid), "--", "bash", "-c", command],
            capture_output=True,
            text=True,
        )

    def push_file(self, vmid: int, local: Path, remote: str) -> None:
        """Copy a file into a container."""
        subprocess.run(
            ["pct", "push", str(vmid), str(local), remote],
            capture_output=True,
            text=True,
            check=True,
        )

    def download_template(self, template_storage: str, template: str) -> None:
        """Download a container template if not already cached."""
        result = subprocess.run(
            ["pveam", "list", template_storage],
            capture_output=True,
            text=True,
        )
        if template not in result.stdout:
            subprocess.run(
                ["pveam", "download", template_storage, template],
                capture_output=True,
                text=True,
                check=True,
            )


def connect_proxmox(
    host: str = "localhost",
    password: str | None = None,
    verify_ssl: bool = False,
) -> tuple[ProxmoxAPI, str]:
    """Create a proxmoxer connection. Returns (proxmox, node_name)."""
    proxmox = ProxmoxAPI(
        host,
        user="root@pam",
        password=password or "",
        verify_ssl=verify_ssl,
    )
    nodes = proxmox.nodes.get()
    if not nodes:
        raise RuntimeError("No Proxmox nodes found")
    node = nodes[0]["node"]
    return proxmox, node
