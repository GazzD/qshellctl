import subprocess
from pathlib import Path
from typing import Optional

import utils.rich_helper as rich
from models.exceptions import ProcessError


def run(
    description: str,
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    ok_codes: tuple[int, ...] = (0,),
) -> int:
    """Print a step label and run a command synchronously.

    Returns the exit code on success.
    Raises ProcessError if the exit code is not in *ok_codes*.
    """
    rich.print(f"[bold cyan]→[/bold cyan] {description}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode not in ok_codes:
        raise ProcessError(
            f"Command failed: {' '.join(str(c) for c in cmd)} "
            f"(exit code {result.returncode}, expected one of {ok_codes})",
            cmd=cmd,
            returncode=result.returncode,
        )
    return result.returncode


def launch(description: str, cmd: list[str]) -> None:
    """Print a step label and spawn a long-running detached process.

    Uses Popen with start_new_session=True so the child keeps running
    after qshellctl exits.
    """
    rich.print(f"[bold cyan]→[/bold cyan] {description}")
    subprocess.Popen(cmd, start_new_session=True)
