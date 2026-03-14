"""Freehold CLI entry point."""

from pathlib import Path

import typer
from dotenv import load_dotenv

app = typer.Typer(help="Freehold — self-hosted knowledge base tools.")


@app.command()
def export(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace slug to export"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output path (file or directory; defaults to cwd)"
    ),
    database_url: str | None = typer.Option(
        None, "--database-url", envvar="DATABASE_URL", help="PostgreSQL connection URL"
    ),
    storage_path: str | None = typer.Option(
        None, "--storage-path", envvar="STORAGE_PATH", help="Path to attachment storage directory"
    ),
) -> None:
    """Export a workspace to a portable zip bundle."""
    load_dotenv()

    import os

    from .db import get_session
    from .export import export_workspace
    from .storage import LocalFilesystemAdapter

    storage_root = storage_path or os.getenv("STORAGE_PATH", "/var/lib/freehold/attachments")
    storage = LocalFilesystemAdapter(storage_root)

    try:
        with get_session(database_url) as session:
            result = export_workspace(
                slug=workspace,
                session=session,
                storage=storage,
                output_path=output,
            )
        typer.echo(f"Exported to {result}")
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except (RuntimeError, FileNotFoundError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
