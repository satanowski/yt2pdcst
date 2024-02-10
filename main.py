#!/usr/bin/env python3
import atexit
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
#    atexit.register(db.close)


@cli.command(help="Add YT channel to watch list")
@click.argument("channel_id", required=True)
@click.argument("channel_name", required=True)
@click.option(
    "--title-remove", default="", help="String (rgxp) to be removed from episode title"
)
@click.option(
    "--min-length", default=0, help="Minimal length (in minutes) of episode to be downloaded"
)
def add_channel(channel_id, channel_name, title_remove, min_length=0):
    log.debug(f"Adding channell {channel_id}:{channel_name}")
    db.add_channel(channel_id, channel_name, title_remove, min_length)


@cli.command(help="Check and register new episodes")
def get_episodes():
    log.debug("Getting new episodes from YT...")
    for channel in db.get_channels():
        log.debug(f"Checking channel: {channel.name}...")
        for epi in get_channel_episodes(str(channel.channel_id)):
            db.add_new_episode(
                episode_id=epi.epi_id,
                title=epi.title,
                description=epi.description,
                channel=channel,
                pub_date=epi.pub_date,
                thumb=epi.thumb,
            )


@cli.command(help="Download eepisodes")
def download_episodes():
    log.debug("Download new episodes from YT...")
    for epi in db.get_episodes2download():  # pylint:disable=not-an-iterable
        log.debug(f"Downloading episode {epi.title}...")
        if not get_audio(str(epi.vid_id), download_dir=config["downlad_dir"]):
            continue
        tmp_file = f"{config['downlad_dir']}/{epi.vid_id}.m4a"

        if not Path(tmp_file).exists():  # probably skipped downlaod (live stream)
            log.debug("No file downloaded - probably skipped")
            continue

        dst_file = f"{config['host_dir']}/{epi.vid_id}.m4a"
        log.info(f"Entry '{epi.title}' downloaded succesfully")
        
        muu = mutagen.File(tmp_file)
        duration = int(muu.info.length) if muu else 0
        if duration < epi.channel.min_length*60:  # skipp this episone if to short
            Path(tmp_file).unlink()  # remove file
            epi.mark_as_missing()
            log.debug(f"Skipping '{epi.title}' - To short!")
            continue
        shutil.move(tmp_file, dst_file)
        epi.mark_as_processed(duration)


@cli.command(help="List registered channels")
def list_channels():
    log.debug('listing channels')
    for ch in db.get_channels():  # pylint:disable=not-an-iterable
        print(f"{ch.channel_id}: {ch.name}")


@cli.command(help="List registered episodes")
def list_episodes():
    print("Registered episodes:")
    for epi in db.get_episodes(
        processed=None, present=None
    ):  # pylint:disable=not-an-iterable
        print(
            f"{epi.vid_id}: [{epi.channel}][{'+' if epi.processed else '-'}/{'+' if epi.present else '-'}] {epi.title} [{epi.duration}]"
        )


@cli.command(help="Generate RSS")
def write_rss():
    log.debug("Preparing rss...")
    meta = config["RSS_META"]
    base_url = f"{config['RSS_SETTINGS']['base_url']}/{config['RSS_SETTINGS']['index']}"
    meta["podcast_url"] = base_url
    rss_file = Path(f"{config['host_dir']}/{config['RSS_SETTINGS']['index']}")
    with rss_file.open("w", encoding="utf-8") as rss:
        rss.write(
            make_rss(
                context=meta, entries=db.get_episodes(processed=True, present=True)
            )
        )
        log.debug(f"rss file written ({rss_file.name})")


@cli.command(help="Mark missing files")
def mark_missing():
    log.debug("Check if any file is missing....")
    present_files = map(lambda p: p.name, Path(config["host_dir"]).glob("*.m4a"))
    db.mark_missing(present_files=list(present_files))


@cli.command(help="Refresh RSS")
@click.pass_context
def refresh(ctx):
    ctx.invoke(get_episodes)
    ctx.invoke(download_episodes)
    ctx.invoke(mark_missing)
    ctx.invoke(write_rss)


if __name__ == "__main__":
    cli()
