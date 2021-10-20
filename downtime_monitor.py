import argparse
import asyncio
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import random
from typing import Optional

import psutil


logger = logging.getLogger(__name__)


class DowntimeMonitor:
    TARGET = ""

    def __init__(self, heartbeat_interval: int, data_dir: str) -> None:
        self.heartbeat_interval = heartbeat_interval
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

    async def heartbeat(self) -> None:
        with open(self.heartbeat_path, "w+") as fd:
            fd.write(datetime.now().isoformat(timespec="seconds"))

    def log_downtime(self) -> None:
        logger.warning(
            f"{self.TARGET} down between "
            f"{self.last_heartbeat.isoformat(timespec='seconds')} and "
            f"{self.following_heartbeat.isoformat(timespec='seconds')}"
        )

    async def run(self):
        while True:
            await self.heartbeat()
            await asyncio.sleep(self.heartbeat_interval)


class SystemDowntimeMonitor(DowntimeMonitor):
    TARGET = "system"

    @property
    def following_heartbeat(self) -> datetime:
        return datetime.fromtimestamp(psutil.boot_time())


class InternetDowntimeMonitor(DowntimeMonitor):
    TARGET = "internet"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.internet_previously_down = True

    async def heartbeat(self) -> None:
        """
        Internet can go down while Rpi continues to carry on and thus we need to log
        downtime as soon as it's over.
        """
        if await self.is_internet_up():
            if self.internet_previously_down and self.last_heartbeat:
                self.log_downtime()

            await super().heartbeat()
            self.internet_previously_down = False
        else:
            self.internet_previously_down = True

    async def is_internet_up(self) -> bool:
        for _ in range(5):
            ping = await self.ping()
            if ping.returncode == 0:
                return True

        return False

    async def ping(self) -> asyncio.subprocess.Process:
        host = random.choice(("1.1.1.1", "8.8.8.8"))
        proc = await asyncio.create_subprocess_shell(
            f"ping {host} -c1 -w1",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        return proc


def prepare_logger(path: str) -> None:
    handler = TimedRotatingFileHandler(path, when="midnight", interval=1)
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


async def main() -> None:
    parser = get_arg_parser()
    args = parser.parse_args()

    Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    prepare_logger(Path(args.data_dir).joinpath("downtime.log"))

    system_downtime_monitor = SystemDowntimeMonitor(
        args.heartbeat_interval, args.data_dir
    )
    if system_downtime_monitor.last_heartbeat:
        system_downtime_monitor.log_downtime()

    internet_downtime_monitor = InternetDowntimeMonitor(
        args.heartbeat_interval, args.data_dir
    )

    await asyncio.gather(system_downtime_monitor.run(), internet_downtime_monitor.run())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
