#!/bin/bash
echo "-- Boot $(cat /proc/sys/kernel/random/boot_id) --" >> /var/log/command.log
runsvdir -P /opt/service
