from __future__ import annotations

import typer

app = typer.Typer(help="FinApp command‑line interface")

@app.command()
def run():
    """Placeholder command to start the application."""
    typer.echo("FinApp CLI started – feature under construction.")

if __name__ == "__main__":
    app()
