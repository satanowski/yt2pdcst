import shutil
import sys
from pathlib import Path

import click
import mutagen
import toml
from loguru import logger as log
from toml.decoder import TomlDecodeError

from db import PDCTSDB
from feed import get_audio, get_channel_episodes
from rss import make_rss

CFG_FILE = Path(__file__).parent / "config.toml"


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

db = PDCTSDB()


@click.group()
def cli():
    pass


@cli.command(help="Add YT channel to watch list")
@click.argument("channel_id", required=True)
@click.argument("channel_name", required=True)
@click.option(
    "--title-remove", default="", help="String (rgxp) to be removed from episode title"
)
def add_channel(channel_id, channel_name, title_remove):
    log.debug(f"Adding channell {channel_id}:{channel_name}")
    db.add_channel(channel_id, channel_name, title_remove)


@cli.command(help="Check and register new episodes")
def get_episodes():
    log.debug("Getting new episodes from YT...")
    for channel in db.get_channels():  # pylint:disable=not-an-iterable
        log.debug(f"Checking channel: {channel.name}...")
        for epi in get_channel_episodes(channel.channel_id):
            db.add_new_episode(
                epi.epi_id, epi.title, epi.pub_date, epi.thumb, epi.description, channel
            )


@cli.command(help="Download eepisodes")
def download_episodes():
    log.debug("Download new episodes from YT...")
    for epi in db.get_episodes2download():  # pylint:disable=not-an-iterable
        log.debug(f"Downloading episode {epi.title}...")
        if not get_audio(epi.vid_id, download_dir=config["downlad_dir"]):
            continue

        log.info(f"Entry '{epi.title}' downloaded succesfully")
        shutil.move(
            f"{config['downlad_dir']}/{epi.vid_id}.m4a",
            f"{config['host_dir']}/{epi.vid_id}.m4a",
        )
        duration = int(
            mutagen.File(f"{config['host_dir']}/{epi.vid_id}.m4a").info.length
        )
        epi.mark_as_processed(duration)


@cli.command(help="List registered channels")
def list_channels():
    for ch in db.get_channels():  # pylint:disable=not-an-iterable
        print(f"{ch.channel_id}: {ch.name}")


@cli.command(help="List registered episodes")
def list_episodes():
    for epi in db.get_episodes():  # pylint:disable=not-an-iterable
        print(
            f"{epi.vid_id}: [{epi.channel}][{'+' if epi.processed else '-'}] {epi.title}"
        )


@cli.command(help="Generate RSS")
def write_rss():
    log.debug("Preparing rss...")
    meta = config["RSS_META"]
    base_url = f"{config['RSS_SETTINGS']['base_url']}/{config['RSS_SETTINGS']['index']}"
    meta["podcast_url"] = base_url
    rss_file = Path(f"{config['host_dir']}/{config['RSS_SETTINGS']['index']}")
    with rss_file.open("w", encoding="utf-8") as rss:
        rss.write(make_rss(context=meta, entries=db.get_episodes()))
        log.debug(f"rss file written ({rss_file.name})")


if __name__ == "__main__":
    cli()
