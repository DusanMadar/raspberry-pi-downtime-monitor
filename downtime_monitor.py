import argparse
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import random
import subprocess
from time import sleep
from typing import Optional

import psutil


logger = logging.getLogger(__name__)


class DowntimeMonitor:
    TARGET = ""

    def __init__(self, data_dir: str) -> None:
        self.heartbeat_path = Path(data_dir).joinpath(f"heartbeat-{self.TARGET}.txt")

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
    def following_heartbeat(self) -> datetime:
        return datetime.now()

    def heartbeat(self) -> None:
        with open(self.heartbeat_path, "w+") as fd:
            fd.write(datetime.now().isoformat(timespec="seconds"))

    def log_downtime(self) -> None:
        logger.warning(
            f"{self.TARGET} down between "
            f"{self.last_heartbeat.isoformat(timespec='seconds')} and "
            f"{self.following_heartbeat.isoformat(timespec='seconds')}"
        )


class SystemDowntimeMonitor(DowntimeMonitor):
    TARGET = "system"

    @property
    def following_heartbeat(self) -> datetime:
        return datetime.fromtimestamp(psutil.boot_time())


class InternetDowntimeMonitor(DowntimeMonitor):
    TARGET = "internet"

    def __init__(self, data_dir: str) -> None:
        super().__init__(data_dir)
        self.internet_previously_down = True

    def heartbeat(self) -> None:
        if self.is_internet_up():
            if self.internet_previously_down and self.last_heartbeat:
                self.log_downtime()

            super().heartbeat()
            self.internet_previously_down = False
        else:
            self.internet_previously_down = True

    def is_internet_up(self) -> bool:
        host = random.choice(("1.1.1.1", "8.8.8.8"))
        return not bool(subprocess.run(["ping", host, "-c1", "-w1"]).returncode)


def prepare_logger(path: str) -> None:
    handler = TimedRotatingFileHandler(path, when="midnight", interval=1)
    handler.suffix = "%Y-%m-%d"
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    )
    logger.addHandler(handler)


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="absolute path")
    parser.add_argument(
        "--heartbeat-interval", type=int, required=True, help="in seconds"
    )
    return parser


def main() -> None:
    parser = get_arg_parser()
    args = parser.parse_args()

    Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    prepare_logger(Path(args.data_dir).joinpath("downtime.log"))

    system_downtime_monitor = SystemDowntimeMonitor(args.data_dir)
    if system_downtime_monitor.last_heartbeat:
        system_downtime_monitor.log_downtime()

    internet_downtime_monitor = InternetDowntimeMonitor(args.data_dir)

    while True:
        system_downtime_monitor.heartbeat()
        internet_downtime_monitor.heartbeat()

        sleep(args.heartbeat_interval)


if __name__ == "__main__":
    main()
