#!/bin/bash
echo "-- Boot $(cat /proc/sys/kernel/random/boot_id) --" >> /mnt/user-data/outputs/command.log
runsvdir -P /opt/service
