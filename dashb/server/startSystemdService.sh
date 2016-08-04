#!/bin/bash

echo "hello"
cd /data/gangamon/dashboard/server/monitoringsite
nohup python manage.py runcollector production > /data/gangamon/dashboard/service/logs/nohup.out 2>&1  &
echo $! > /var/run/collector.pid
#echo $! > /data/gangamon/dashboard/service/logs/service_pid

