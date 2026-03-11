from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def print(message: str) -> None:
    console.print(message)


def success_message(message: str) -> None:
    console.print(f"[green]✓ {message}[/green]")


def error_message(message: str) -> None:
    err_console.print(f"[red]✗ {message}[/red]")


def warning_message(message: str) -> None:
    console.print(f"[yellow]⚠ {message}[/yellow]")
