from datetime import datetime, timezone
from pathlib import Path

import logging
import subprocess
import tomllib

def read_without_frontmatter(f):
    lines = open(f).readlines()
    lines.reverse()
    lines.pop()
    while lines.pop() != "---\n":
        pass

    return "".join(reversed(lines))

def run(command, *, text=True, check=True, capture_output=True, **kwargs):
    return subprocess.run(
        command,
        text=text,
        check=check,
        capture_output=capture_output,
        **kwargs,
    )

def log_run_error(logger, msg, e):
    logger.error(
        f"{msg} (exit code %d):\nSTDERR:\n%s\nSTDOUT:\n%s",
        e.returncode,
        e.stderr,
        e.stdout,
    )

def deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result

def merge_settings(logger, config_dir, account_uuid, local_settings):
    settings = {}

    if config_dir:
        config_dir_path = Path(config_dir)
        if not config_dir_path.exists():
            logger.error("Missing config directory: %s", config_dir)
            raise FileNotFoundError(config_dir)

        global_config_path = config_dir_path / "config.toml"
        if global_config_path.exists():
            try:
                settings = tomllib.load(global_config_path.open("rb"))
            except tomllib.TOMLDecodeError as e:
                logger.error("Invalid TOML in global settings: %s", e)
                raise

        account_config_path = config_dir_path / f"accounts/{account_uuid}.toml"
        if account_config_path.exists():
            try:
                account_settings = tomllib.load(account_config_path.open("rb"))
            except tomllib.TOMLDecodeError as e:
                logger.error("Invalid TOML in account settings: %s", e)
                raise

            settings = deep_merge(settings, account_settings)

    return deep_merge(settings, local_settings)

class LogFormatter(logging.Formatter):
    def format(self, record) -> str:
        ts = datetime.fromtimestamp(
            record.created,
            tz=timezone.utc,
        ).isoformat(timespec="milliseconds")
        return f"{ts} {record.levelname} {record.name}: {record.getMessage()}"

def init_logger(log_file, level = logging.INFO):
    handler = logging.FileHandler(log_file)
    handler.setFormatter(LogFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(level)
