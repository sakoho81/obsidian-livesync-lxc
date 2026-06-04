"""CLI entry point for obsidian-livesync."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from obsidian_livesync.config import Credentials
from obsidian_livesync.container import ContainerManager, connect_proxmox
from obsidian_livesync.couchdb import (
    check_config,
    configure_livesync,
    create_database,
    delete_database,
    generate_install_script,
    get_server_ip,
    list_databases,
    wait_for_couchdb,
)
from obsidian_livesync.setup_uri import generate_setup_uri

app = typer.Typer(help="Obsidian LiveSync LXC manager for Proxmox")
console = Console()


def _creds_from_container(ct_id: int) -> Credentials | None:
    """Attempt to read credentials from a container."""
    try:
        result = subprocess.run(
            ["pct", "exec", str(ct_id), "--", "cat", "/root/.obsidian-livesync-credentials"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        values: dict[str, str] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
        if values:
            return Credentials(
                couchdb_user=values.get("COUCHDB_USER", ""),
                couchdb_password=values.get("COUCHDB_PASSWORD", ""),
                database_name=values.get("DATABASE_NAME", "obsidian"),
                couchdb_port=int(values.get("COUCHDB_PORT", "5984")),
            )
    except Exception:
        pass
    return None


def _get_creds(ct_id: int | None) -> Credentials:
    """Get credentials from container or local file."""
    if ct_id is not None:
        creds = _creds_from_container(ct_id)
        if creds and creds.couchdb_user:
            return creds
    return Credentials.load()


@app.command()
def create(
    ct_id: int = typer.Option(None, "--ct-id", "-c", help="Container ID (auto-detected if omitted)", min=100),
    hostname: str = typer.Option("obsidian-livesync", "--hostname", "-n", help="Container hostname"),
    disk: int = typer.Option(4, "--disk", "-d", help="Disk size in GB"),
    ram: int = typer.Option(512, "--ram", "-m", help="RAM in MB"),
    cores: int = typer.Option(1, "--cores", help="CPU cores"),
    storage: Optional[str] = typer.Option(None, "--storage", "-s", help="Storage pool for the container"),
    bridge: Optional[str] = typer.Option(None, "--bridge", "-b", help="Network bridge"),
    dhcp: bool = typer.Option(True, "--dhcp/--static", help="Use DHCP (default) or static IP"),
    static_ip: Optional[str] = typer.Option(None, "--ip", help="Static IP with CIDR (e.g., 192.168.1.100/24)"),
    gateway: Optional[str] = typer.Option(None, "--gateway", "-g", help="Gateway IP for static config"),
    couchdb_user: str = typer.Option("admin", "--couchdb-user", help="CouchDB admin username"),
    couchdb_password: Optional[str] = typer.Option(None, "--couchdb-password", help="CouchDB admin password"),
    database: str = typer.Option("obsidian", "--database", "--db", help="Database name for Obsidian"),
    root_password: Optional[str] = typer.Option(None, "--root-password", help="Container root password"),
    proxmox_password: Optional[str] = typer.Option(None, "--proxmox-password", help="Proxmox root password"),
    proxmox_host: str = typer.Option("localhost", "--proxmox-host", help="Proxmox host address"),
    template_storage: str = typer.Option("local", "--template-storage", help="Storage for templates"),
    no_setup_uri: bool = typer.Option(False, "--no-setup-uri", help="Skip setup URI generation"),
):
    """Create a new Obsidian LiveSync LXC container on Proxmox."""

    # --- Proxmox auth ---
    if proxmox_password is None:
        proxmox_password = typer.prompt(
            "Proxmox root password",
            hide_input=True,
        )
    try:
        proxmox, node = connect_proxmox(host=proxmox_host, password=proxmox_password)
    except Exception as e:
        console.print(f"[red]Failed to connect to Proxmox: {e}[/red]")
        raise typer.Exit(1)

    mgr = ContainerManager(proxmox, node)

    # --- Container ID ---
    if ct_id is None:
        ct_id = mgr.get_next_ct_id()
        console.print(f"[dim]Auto-detected next free Container ID: {ct_id}[/dim]")

    # --- Template selection ---
    templates = mgr.list_templates()
    if not templates:
        console.print("[red]No Debian templates found. Run 'pveam update' first.[/red]")
        raise typer.Exit(1)

    default_template = templates[0]["template"]
    console.print("\n[bold]Available Debian templates:[/bold]")
    for i, t in enumerate(templates, 1):
        console.print(f"  {i}) {t['template']}")
    choice = typer.prompt("Select template number", default="1")
    try:
        selected = templates[int(choice) - 1]["template"]
    except (IndexError, ValueError):
        selected = default_template
    console.print(f"[dim]Selected: {selected}[/dim]")

    mgr.download_template(template_storage, selected)
    ostemplate = f"{template_storage}:vztmpl/{selected}"

    # --- Storage ---
    if storage is None:
        storages = mgr.list_storage("rootdir")
        if not storages:
            console.print("[red]No storage available for containers.[/red]")
            raise typer.Exit(1)
        default_storage = "local-lvm" if "local-lvm" in storages else storages[0]
        console.print("\n[bold]Available storage:[/bold]")
        for i, s in enumerate(storages, 1):
            console.print(f"  {i}) {s}")
        choice = typer.prompt("Select storage number", default="1")
        try:
            storage = storages[int(choice) - 1]
        except (IndexError, ValueError):
            storage = default_storage
        console.print(f"[dim]Selected: {storage}[/dim]")

    # --- Network ---
    if bridge is None:
        bridges = mgr.list_bridges()
        if not bridges:
            console.print("[red]No network bridges found.[/red]")
            raise typer.Exit(1)
        default_bridge = "vmbr0" if "vmbr0" in bridges else bridges[0]
        console.print("\n[bold]Available bridges:[/bold]")
        for i, b in enumerate(bridges, 1):
            console.print(f"  {i}) {b}")
        choice = typer.prompt("Select bridge number", default="1")
        try:
            bridge = bridges[int(choice) - 1]
        except (IndexError, ValueError):
            bridge = default_bridge
        console.print(f"[dim]Selected: {bridge}[/dim]")

    if not dhcp:
        if static_ip is None:
            static_ip = typer.prompt("IP Address (e.g., 192.168.1.100/24)")
        if gateway is None:
            gateway = typer.prompt("Gateway (e.g., 192.168.1.1)")
        net_config = f"name=eth0,bridge={bridge},ip={static_ip},gw={gateway}"
    else:
        net_config = f"name=eth0,bridge={bridge},ip=dhcp"

    # --- Credentials ---
    if root_password is None:
        root_password = typer.prompt(
            "Container root password",
            hide_input=True,
            confirmation_prompt=True,
        )
    if couchdb_password is None:
        couchdb_password = typer.prompt(
            "CouchDB admin password",
            hide_input=True,
            confirmation_prompt=True,
        )

    creds = Credentials(
        couchdb_user=couchdb_user,
        couchdb_password=couchdb_password,
        database_name=database,
    )

    # --- Confirmation ---
    console.print("\n")
    console.print(Panel.fit(
        f"Container ID: {ct_id}\n"
        f"Hostname: {hostname}\n"
        f"Disk: {disk}GB  RAM: {ram}MB  CPU: {cores} core(s)\n"
        f"Storage: {storage}  Bridge: {bridge}\n"
        f"Network: {'DHCP' if dhcp else f'{static_ip} via {gateway}'}\n"
        f"CouchDB user: {couchdb_user}\n"
        f"Database: {database}",
        title="Configuration Summary",
        border_style="cyan",
    ))
    confirm = typer.confirm("Create container with these settings?")
    if not confirm:
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)

    # --- Create container ---
    with console.status("[bold green]Creating container...[/bold green]"):
        mgr.create_container(
            vmid=ct_id,
            hostname=hostname,
            root_password=root_password,
            template=ostemplate,
            storage=storage,
            disk=disk,
            ram=ram,
            cores=cores,
            net_config=net_config,
        )
    console.print(f"[green]Container {ct_id} created.[/green]")

    # --- Start container ---
    with console.status("[bold green]Starting container...[/bold green]"):
        mgr.start_container(ct_id)
    container_ip = mgr.get_container_ip(ct_id)
    console.print(f"[green]Container {ct_id} started. IP: {container_ip}[/green]")

    # --- Install CouchDB ---
    with console.status("[bold green]Installing CouchDB in container...[/bold green]"):
        script = generate_install_script(creds)
        script_path = Path("/tmp/obsidian-livesync-install.sh")
        script_path.write_text(script)
        script_path.chmod(0o755)
        mgr.push_file(ct_id, script_path, "/tmp/install-couchdb.sh")
        result = mgr.exec_in_container(ct_id, "bash /tmp/install-couchdb.sh")
        if result.returncode != 0:
            console.print(f"[red]CouchDB install failed:[/red]\n{result.stderr}")
            raise typer.Exit(1)
        script_path.unlink()
    console.print("[green]CouchDB installed.[/green]")

    # --- Configure CouchDB ---
    with console.status("[bold green]Configuring CouchDB for LiveSync...[/bold green]"):
        if not wait_for_couchdb(creds):
            console.print("[red]CouchDB did not become ready in time.[/red]")
            raise typer.Exit(1)
        configure_livesync(creds)
    console.print("[green]LiveSync configuration applied.[/green]")

    # --- Create database ---
    with console.status("[bold green]Creating database...[/bold green]"):
        create_database(creds)
    console.print(f"[green]Database '{creds.database_name}' ready.[/green]")

    # --- Save credentials inside container ---
    mgr.exec_in_container(
        ct_id,
        f"mkdir -p /root && cat > /root/.obsidian-livesync-credentials << 'EOF'\n"
        f"COUCHDB_USER={creds.couchdb_user}\n"
        f"COUCHDB_PASSWORD={creds.couchdb_password}\n"
        f"DATABASE_NAME={creds.database_name}\n"
        f"COUCHDB_PORT=5984\n"
        f"EOF\nchmod 600 /root/.obsidian-livesync-credentials",
    )

    # --- Success ---
    console.print("\n")
    console.print(Panel(
        Text.assemble(
            ("Container Details:\n", "bold cyan"),
            (f"ID:       {ct_id}\n", ""),
            (f"Hostname: {hostname}\n", ""),
            (f"IP:       {container_ip}\n\n", ""),
            ("CouchDB Admin:\n", "bold cyan"),
            (f"URL:      http://{container_ip}:5984/_utils\n\n", ""),
            ("LiveSync Settings:\n", "bold cyan"),
            (f"URI:      http://{container_ip}:5984\n", ""),
            (f"Username: {creds.couchdb_user}\n", ""),
            (f"Password: (as configured)\n", ""),
            (f"Database: {creds.database_name}\n", ""),
        ),
        title="Installation Complete",
        border_style="green",
    ))

    # --- Setup URI hint ---
    if not no_setup_uri:
        console.print("\n[bold]Setup URI (for one-click device config):[/bold]")
        console.print("[dim]Run this from any machine with Deno installed:[/dim]")
        console.print(
            Panel(
                textwrap.dedent(f"""\
                export hostname="http://{container_ip}:5984"
                export database="{creds.database_name}"
                export username="{creds.couchdb_user}"
                export password="{creds.couchdb_password}"
                export passphrase=""  # choose your E2E passphrase

                deno run -A \\
                  https://raw.githubusercontent.com/vrtmrz/obsidian-livesync/main/utils/flyio/generate_setupuri.ts
                """),
                border_style="dim",
            )
        )

    console.print(f"\n[dim]Access container: pct enter {ct_id}[/dim]\n")


@app.command()
def setup_uri(
    hostname: str = typer.Option(..., "--hostname", help="CouchDB server URL (e.g., http://192.168.1.100:5984)"),
    database: str = typer.Option(..., "--database", "--db", help="CouchDB database name"),
    username: str = typer.Option(..., "--username", "-u", help="CouchDB admin username"),
    password: str = typer.Option(..., "--password", "-p", help="CouchDB admin password"),
    passphrase: str = typer.Option("", "--passphrase", help="E2E encryption passphrase (empty = auto-generate URI passphrase)"),
):
    """Generate an obsidian://setuplivesync setup URI."""
    try:
        uri, uri_passphrase = generate_setup_uri(
            hostname=hostname,
            database=database,
            username=username,
            password=password,
            passphrase=passphrase,
        )
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        console.print("[dim]Install Deno: curl -fsSL https://deno.land/install.sh | sh[/dim]")
        raise typer.Exit(1)

    if uri_passphrase:
        console.print(f"[bold yellow]Setup URI passphrase:[/bold yellow] {uri_passphrase}")
        console.print("[dim]Save this passphrase! You'll need it to import the URI on new devices.[/dim]")
    console.print(f"\n[green]{uri}[/green]")


db_app = typer.Typer(help="Database management")
app.add_typer(db_app, name="db")


@db_app.command("create")
def db_create(
    name: str = typer.Argument(..., help="Database name"),
    ct_id: Optional[int] = typer.Option(None, "--ct-id", "-c", help="Container ID (for in-container operations)"),
):
    """Create a CouchDB database."""
    creds = _get_creds(ct_id)
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    if create_database(creds, name):
        console.print(f"[green]Database '{name}' created (or already exists).[/green]")
    else:
        console.print(f"[red]Failed to create database '{name}'.[/red]")
        raise typer.Exit(1)


@db_app.command("list")
def db_list(
    ct_id: Optional[int] = typer.Option(None, "--ct-id", "-c", help="Container ID (for in-container operations)"),
):
    """List all CouchDB databases."""
    creds = _get_creds(ct_id)
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    try:
        dbs = list_databases(creds)
    except Exception as e:
        console.print(f"[red]Failed to list databases: {e}[/red]")
        raise typer.Exit(1)

    table = Table(title="CouchDB Databases")
    table.add_column("Name", style="cyan")
    for db in sorted(dbs):
        if not db.startswith("_"):
            table.add_row(db)
    console.print(table)


@db_app.command("delete")
def db_delete(
    name: str = typer.Argument(..., help="Database name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    ct_id: Optional[int] = typer.Option(None, "--ct-id", "-c", help="Container ID"),
):
    """Delete a CouchDB database."""
    if not force:
        confirm = typer.confirm(f"Delete database '{name}'? This cannot be undone.")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)
    creds = _get_creds(ct_id)
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    if delete_database(creds, name):
        console.print(f"[green]Database '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Failed to delete database '{name}'.[/red]")
        raise typer.Exit(1)


@app.command()
def check(
    ct_id: Optional[int] = typer.Option(None, "--ct-id", "-c", help="Container ID"),
):
    """Check CouchDB configuration for LiveSync compatibility."""
    creds = _get_creds(ct_id)
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    try:
        config = check_config(creds)
    except Exception as e:
        console.print(f"[red]Cannot connect to CouchDB: {e}[/red]")
        raise typer.Exit(1)

    console.print(Panel(f"Connected to CouchDB at {creds.couchdb_url}", border_style="green"))

    required = {
        ("chttpd", "require_valid_user"): "true",
        ("chttpd", "enable_cors"): "true",
        ("chttpd", "max_http_request_size"): "4294967296",
        ("chttpd_auth", "require_valid_user"): "true",
        ("httpd", "enable_cors"): "true",
        ("couchdb", "max_document_size"): "50000000",
        ("cors", "credentials"): "true",
    }

    table = Table(title="LiveSync Configuration Check")
    table.add_column("Setting", style="cyan")
    table.add_column("Current", style="yellow")
    table.add_column("Expected", style="dim")
    table.add_column("Status")

    all_ok = True
    for (section, key), expected in required.items():
        current = config.get(section, {}).get(key, "MISSING")
        ok = current.strip('"') == expected
        if not ok:
            all_ok = False
        table.add_row(
            f"{section}/{key}",
            current,
            expected,
            "[green]OK[/green]" if ok else "[red]FIX[/red]",
        )

    console.print(table)

    if all_ok:
        console.print("\n[green]All settings correct![/green]")
    else:
        console.print("\n[yellow]Some settings need fixing. Run 'obsidian-livesync create' to reconfigure.[/yellow]")
