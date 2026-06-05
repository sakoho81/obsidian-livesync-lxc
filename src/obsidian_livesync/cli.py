"""CLI entry point for obsidian-livesync."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from obsidian_livesync.config import Credentials
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

app = typer.Typer(help="Obsidian LiveSync server manager")
console = Console()


def _get_creds() -> Credentials:
    """Get credentials from local file."""
    return Credentials.load()


@app.command()
def install():
    """Install and configure CouchDB for Obsidian LiveSync on this machine."""
    creds = _get_creds()
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)
        creds.database_name = typer.prompt("Database name", default="obsidian")

    with console.status("[bold green]Installing CouchDB...[/bold green]"):
        import subprocess

        result = subprocess.run(
            ["bash", "-c", generate_install_script(creds)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]Install failed:[/red]\n{result.stderr}")
            raise typer.Exit(1)
    console.print("[green]CouchDB installed.[/green]")

    with console.status("[bold green]Configuring CouchDB for LiveSync...[/bold green]"):
        if not wait_for_couchdb(creds):
            console.print("[red]CouchDB did not become ready.[/red]")
            raise typer.Exit(1)
    configure_livesync(creds)
    console.print("[green]LiveSync configuration applied.[/green]")

    with console.status("[bold green]Creating database...[/bold green]"):
        create_database(creds)
    console.print(f"[green]Database '{creds.database_name}' ready.[/green]")

    creds.save()
    console.print(f"[dim]Credentials saved to {creds.couchdb_url}[/dim]")

    ip = get_server_ip()
    console.print("\n")
    console.print(
        Panel(
            f"CouchDB Admin: http://{ip}:5984/_utils\n"
            f"LiveSync URI:  http://{ip}:5984\n"
            f"Username:      {creds.couchdb_user}\n"
            f"Database:      {creds.database_name}",
            title="Installation Complete",
            border_style="green",
        )
    )


@app.command()
def setup_uri(
    hostname: str = typer.Option(
        ...,
        "--hostname",
        help="CouchDB server URL (e.g., http://192.168.1.100:5984)",
    ),
    database: str = typer.Option(
        ..., "--database", "--db", help="CouchDB database name"
    ),
    username: str = typer.Option(
        ..., "--username", "-u", help="CouchDB admin username"
    ),
    password: str = typer.Option(
        ..., "--password", "-p", help="CouchDB admin password"
    ),
    passphrase: str = typer.Option(
        "",
        "--passphrase",
        help="E2E encryption passphrase (empty = auto-generate URI passphrase)",
    ),
):
    """Generate an obsidian://setuplivesync setup URI."""
    uri, uri_passphrase = generate_setup_uri(
        hostname=hostname,
        database=database,
        username=username,
        password=password,
        passphrase=passphrase,
    )

    if uri_passphrase:
        console.print(
            f"[bold yellow]Setup URI passphrase:[/bold yellow] {uri_passphrase}"
        )
        console.print(
            "[dim]Save this passphrase! You'll need it"
            " to import the URI on new devices.[/dim]"
        )
    console.print(f"\n[green]{uri}[/green]")


db_app = typer.Typer(help="Database management")
app.add_typer(db_app, name="db")


@db_app.command("create")
def db_create(
    name: str = typer.Argument(..., help="Database name"),
):
    """Create a CouchDB database."""
    creds = _get_creds()
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    if create_database(creds, name):
        console.print(f"[green]Database '{name}' created (or already exists).[/green]")
    else:
        console.print(f"[red]Failed to create database '{name}'.[/red]")
        raise typer.Exit(1)


@db_app.command("list")
def db_list():
    """List all CouchDB databases."""
    creds = _get_creds()
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    try:
        dbs = list_databases(creds)
    except Exception as e:
        console.print(f"[red]Failed to list databases: {e}[/red]")
        raise typer.Exit(1) from e

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
):
    """Delete a CouchDB database."""
    if not force:
        confirm = typer.confirm(f"Delete database '{name}'? This cannot be undone.")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)
    creds = _get_creds()
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    if delete_database(creds, name):
        console.print(f"[green]Database '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Failed to delete database '{name}'.[/red]")
        raise typer.Exit(1)


@app.command()
def check():
    """Check CouchDB configuration for LiveSync compatibility."""
    creds = _get_creds()
    if not creds.couchdb_password:
        creds.couchdb_user = typer.prompt("CouchDB username", default="admin")
        creds.couchdb_password = typer.prompt("CouchDB password", hide_input=True)

    try:
        config = check_config(creds)
    except Exception as e:
        console.print(f"[red]Cannot connect to CouchDB: {e}[/red]")
        raise typer.Exit(1) from e

    console.print(
        Panel(
            f"Connected to CouchDB at {creds.couchdb_url}",
            border_style="green",
        )
    )

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
        console.print(
            "\n[yellow]Some settings need fixing."
            " Re-run the installer or adjust CouchDB config manually.[/yellow]"
        )
