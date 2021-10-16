# raspberry-pi-downtime-monitor

Uses Python packages available on `Raspbian GNU/Linux 10 (buster)` by default.

To run the script automatically add a line similar to the one below (change paths match your setup) to crontab.

```
@reboot python3 /code/downtime_monitor.py --data-dir /logs/downtime --heartbeat-interval 30
```

## Limitations

Please note that if your Rpi is **not equipped with an RTC** the logged timestamps will be rather chaotic. For example you can get a log entry like

```
2021-01-01T10:00:10 down between 2021-01-01T10:30:00 and 2021-01-01T10:00:00
```

Refer to [How accurate is Raspberry Pi's timekeeping?](https://raspberrypi.stackexchange.com/q/1397/137415) for more details.
