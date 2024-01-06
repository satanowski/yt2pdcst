import shutil
import sys
from pathlib import Path

import mutagen
import toml
from loguru import logger as log
from toml.decoder import TomlDecodeError

from db import FeedDB
from feed import get_audio, get_feed_entries, load_feed_list
from rss import make_rss

CFG_FILE = Path(__file__).parent / "config.toml"

db = FeedDB()


def load_config(cfg_file=CFG_FILE) -> dict:
    if not cfg_file.exists():
        log.error(f"No config file ({cfg_file})!")
        return {}
    try:
        return toml.load(cfg_file.open("r", encoding="utf-8"))
    except TomlDecodeError as err:
        log.error(f"Cannot parse config file {cfg_file}: {err}")
        sys.exit(1)


config = load_config()


def get_episode_and_store(
    vid_id: str, title: str, date: str, thumb: str, desc: str, channel: str
):
    log.debug(f"Getting VID:{vid_id}: {title}")
    if db.is_downloaded(vid_id):
        return

    if get_audio(vid_id, download_dir=config["downlad_dir"]):
        log.info(f"Entry '{title}' downloaded succesfully")
        shutil.move(
            f"{config['downlad_dir']}/{vid_id}.m4a",
            f"{config['host_dir']}/{vid_id}.m4a",
        )
        duration = int(mutagen.File(f"{config['host_dir']}/{vid_id}.m4a").info.length)

        db.add_vid(vid_id, title, date, thumb, desc, channel, duration)


def get_new_episodes():
    for channel, feed_data in load_feed_list().items():
        log.debug(f"Checking channel: {channel}...")

        for idx, data in enumerate(get_feed_entries(feed_data["channel_id"])):
            if idx >= feed_data["recent"]:
                break
            get_episode_and_store(*data, channel)


def prepare_rss():
    log.debug("Preparing rss...")
    meta = config["RSS_META"]
    meta[
        "podcast_url"
    ] = f"{config['RSS_SETTINGS']['base_url']}/{config['RSS_SETTINGS']['index']}"
    return make_rss(context=meta, entries=db.get_episodes())


if __name__ == "__main__":
    get_new_episodes()
    with Path(f"{config['host_dir']}/{config['RSS_SETTINGS']['index']}").open(
        "w", encoding="utf-8"
    ) as rss:
        rss.write(prepare_rss())
