import argparse
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from time import sleep
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


class DowntimeMonitor:
    def __init__(self, data_dir: str, heartbeat_interval: int) -> None:
        self.data_dir = data_dir
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_path = Path(self.data_dir).joinpath("heartbeat.txt")
        self.downtime_log_path = Path(self.data_dir).joinpath("downtime.log")

    def prepare(self):
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        self.prepare_logger()

    def prepare_logger(self):
        handler = TimedRotatingFileHandler(
            self.downtime_log_path, when="midnight", interval=1
        )
        handler.suffix = "%Y-%m-%d"
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
        )
        logger.addHandler(handler)

    def heartbeat(self):
        with open(self.heartbeat_path, "w+") as fd:
            fd.write(datetime.now().isoformat(timespec="seconds"))

    @property
    def last_heartbeat(self) -> Optional[datetime]:
        try:
            with open(self.heartbeat_path) as fd:
                last_heartbeat = fd.read().strip()
        except FileNotFoundError:
            return None

        if not last_heartbeat:
            return None

        return datetime.fromisoformat(last_heartbeat)

    @property
    def boot_time(self) -> datetime:
        return datetime.fromtimestamp(psutil.boot_time())

    def log_downtime(self):
        if self.last_heartbeat:
            logger.warning(
                f"down between {self.last_heartbeat.isoformat()} "
                f"and {self.boot_time.isoformat()}"
            )

    def watch_uptime(self) -> None:
        while True:
            self.heartbeat()
            sleep(self.heartbeat_interval)


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="absolute path")
    parser.add_argument(
        "--heartbeat-interval", type=int, required=True, help="in seconds"
    )
    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    downtime_monitor = DowntimeMonitor(args.data_dir, args.heartbeat_interval)
    downtime_monitor.prepare()
    downtime_monitor.log_downtime()
    downtime_monitor.watch_uptime()


if __name__ == "__main__":
    main()
