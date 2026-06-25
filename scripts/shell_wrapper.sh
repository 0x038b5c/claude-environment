#!/bin/bash

# Source bash_profile
if [[ -f /opt/bash_profile ]]; then
    source /opt/bash_profile
fi

exec /bin/bash "$@"
