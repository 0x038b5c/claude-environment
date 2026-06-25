# sourced every invocation of bash_tool by shell_wrapper

# environment binaries
export PATH="/opt/setup/bin:$PATH"

# GitHub authentication
if [[ -f /opt/github_token ]]; then
    # gh authentication
    export GH_TOKEN=$(cat /opt/github_token)

    # git authentication
    export GIT_ASKPASS=/opt/setup/scripts/git_askpass.sh
    export GIT_TERMINAL_PROMPT=0
fi
