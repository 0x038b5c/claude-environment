#!/bin/bash

# symlink init script for init_hook.so
ln -fs /opt/setup/scripts/init.sh /opt/init

# start init script
/opt/setup/scripts/init.sh & disown
