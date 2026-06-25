from pathlib import Path

import click
import subprocess

SETUP_DIR = Path(__file__).parent.parent

@click.group("tool")
def main():
    ...

@main.command()
def restart():
    subprocess.Popen(
        [SETUP_DIR / "scripts/restart.sh"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
