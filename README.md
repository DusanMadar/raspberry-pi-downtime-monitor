# raspberry-pi-downtime-monitor

Uses Python packages available on `Raspbian GNU/Linux 10 (buster)` by default.

To run the script automatically add a line similar to the one below (change paths match your setup) to crontab.

```
@reboot python3 /code/downtime_monitor.py --data-dir /logs/downtime --heartbeat-interval 30
```
