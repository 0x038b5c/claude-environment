from pathlib import Path

import json
import logging
import shutil
import subprocess
import tomllib

from src.utils import (
    merge_settings,
    read_without_frontmatter,
    run,
    log_run_error,
    init_logger,
)

LOG_FILE = "/mnt/user-data/outputs/setup.log"
SETTINGS_FILE = "/mnt/skills/user/settings/SKILL.md"
AGE_KEY = "/mnt/skills/user/setup/keys/age.key"
SETUP_DIR = Path(__file__).parent.parent

logger = logging.getLogger(__name__)
init_logger(LOG_FILE)

def main():
    try:
        local_settings = tomllib.loads(read_without_frontmatter(SETTINGS_FILE))
    except tomllib.TOMLDecodeError as e:
        logger.error("Invalid TOML in local settings: %s", e)
        raise

    local_accounts_settings: dict | None = local_settings.get("account")
    if not local_accounts_settings:
        logger.error("Missing `[account]` in settings")
        raise KeyError("account")

    account_uuid = local_accounts_settings.get("uuid")
    if not account_uuid:
        logger.error("Missing `uuid` in `[account]` in settings")
        raise KeyError("uuid")

    config_dir = local_accounts_settings.get("config_dir", "/opt/setup/config")
    config_repo = local_accounts_settings.get("config_repo")

    # clone config repo
    if config_repo:
        if not config_dir:
            logger.error("`account.config_repo` is set, but `account.config_dir` is missing")
            raise KeyError("config_dir")

        try:
            run(["git", "clone", config_repo, config_dir, "--depth=1"])
            logger.info("Cloned config repo: %s", config_dir)
        except subprocess.CalledProcessError as e:
            log_run_error(logger, "Failed to clone config repo", e)
            raise

    settings = merge_settings(
        logger,
        config_dir,
        account_uuid,
        local_settings,
    )

    # write final settings
    Path("/mnt/user-data/outputs/settings.json").write_text(json.dumps(
        settings,
        indent=4,
        sort_keys=True,
    ))

    # update the system
    run(["apt", "update"], check=False)
    logger.info("System updated")

    package_settings = settings.get("environment", {}).get("packages", {})
    system_packages = package_settings.get("system", [])
    python_packages = package_settings.get("python", [])

    # install system packages
    if system_packages:
        try:
            run(["apt", "install", "-y"] + system_packages)
            logger.info("Installed system packages: %s", ", ".join(system_packages))
        except subprocess.CalledProcessError as e:
            log_run_error(logger, "Failed to install system packages", e)
            raise

    # install python packages
    if python_packages:
        try:
            run(["pip", "install", "--break-system-packages"] + python_packages)
            logger.info("Installed python packages: %s", ", ".join(python_packages))
        except subprocess.CalledProcessError as e:
            log_run_error(logger, "Failed to install python packages", e)
            raise

    env_settings = settings.get("environment", {})
    env_creds_settings = env_settings.get("credentials", {})
    secrets_dir = Path(env_creds_settings.get("secrets_dir", SETUP_DIR / "creds"))
    creds_dir = Path(env_creds_settings.get("creds_dir", Path("/opt/creds")))

    # decrypt credentials
    if secrets_dir.exists():
        logger.info("Decrypting secrets")
        creds_dir.mkdir(parents=True, exist_ok=True)
        for secret in secrets_dir.iterdir():
            try:
                secret_abs = str(secret.absolute())
                cred_abs = str((creds_dir / secret.stem).absolute())
                run([ "age", "-d", "-i", AGE_KEY, "-o", cred_abs, secret_abs ])
                logger.info("Decrypted secret '%s' -> '%s'", secret_abs, cred_abs)
            except subprocess.CalledProcessError as e:
                logger.warning(
                    "Failed to decrypt secret '%s': %s",
                    str(secret.absolute()),
                    e
                )

    # install shell wrapper
    shell_wrapper = Path("/bin/.shell_wrapper")
    shutil.copy(SETUP_DIR / "scripts/shell_wrapper.sh", shell_wrapper)
    shell_wrapper.rename("/bin/sh")
    logger.info("Wrapping /bin/sh to use /opt/bash_profile")

    env_runtime_settings = env_settings.get("runtime", {})
    bash_profile = env_runtime_settings.get("bash_profile")

    # install bash profile
    if bash_profile:
        shutil.copy(bash_profile, "/opt/bash_profile")
        logger.info("Installing bash profile: %s", bash_profile)

    # install ld.so.preload hooks
    ld_so_preload = env_runtime_settings.get("ld_so_preload", [])
    if ld_so_preload:
        Path("/etc/ld.so.preload").write_text("\n".join(ld_so_preload))
        logger.info(
            "Added following libraries to LD_PRELOAD: %s",
            ", ".join(ld_so_preload),
        )

    services = env_runtime_settings.get("services", [])

    # install services
    service_dir = Path("/opt/service")
    service_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Created service directory /opt/service")

    if services:
        for service_path in services:
            service_name = Path(service_path).name
            service_link = service_dir / service_name
            service_link.unlink(missing_ok=True)
            service_link.symlink_to(service_path)
            logger.info("Installed service %s at %s", service_name, service_link.absolute())

    env_git_settings = env_settings.get("git", {})
    git_username = env_git_settings.get("name", "Claude")
    git_email = env_git_settings.get("email", "claude@anthropic.com")

    # configure git
    run(["git", "config", "--global", "user.name", git_username])
    run(["git", "config", "--global", "user.email", git_email])
    logger.info("Configured git author: %s <%s>", git_username, git_email)

    # configure GitHub
    github_token = Path(env_creds_settings.get("github_token", creds_dir / "github_token"))
    if github_token.exists():
        github_token_link = Path("/opt/github_token")
        github_token_link.unlink(missing_ok=True)
        github_token_link.symlink_to(github_token)
        logger.info("Symlinked github token to /opt/github_token")

    env_state_settings = env_settings.get("state", {})
    state_repo = env_state_settings.get("repo")
    state_dir = env_state_settings.get("state_dir", "/opt/state")

    # clone state repo
    if state_repo:
        try:
            run(f"git clone {state_repo} {state_dir} --depth=1", shell=True)
            logger.info("Cloned state repo: %s", state_dir)
        except subprocess.CalledProcessError as e:
            log_run_error(logger, "Failed to clone state repo", e)
            raise

    finish_exe = env_runtime_settings.get("finish")

    # run finish script
    if finish_exe:
        logger.info("Starting finish script")
        subprocess.Popen(
            [finish_exe],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

if __name__ == "__main__":
    main()
