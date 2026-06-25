#!/bin/bash

# log reboot
echo '-- Reboot Triggered (in 15s) --' >> /mnt/user-data/outputs/command.log
sleep 10

# stop services
pkill runsvdir || true
sleep 3

# shutdown
echo s > /proc/sysrq-trigger
sleep 1
echo u > /proc/sysrq-trigger
sleep 1
echo b > /proc/sysrq-trigger
