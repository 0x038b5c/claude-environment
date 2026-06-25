#!/bin/bash
sleep 10

# stop services
pkill runsvdir
sleep 2

# shutdown
echo s > /proc/sysrq-trigger
sleep 1
echo u > /proc/sysrq-trigger
sleep 1
echo b > /proc/sysrq-trigger
