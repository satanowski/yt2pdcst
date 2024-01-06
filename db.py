import re
from pathlib import Path
from typing import Iterable

from loguru import logger as log
from peewee import (
    BooleanField,
    CharField,
    DateField,
    ForeignKeyField,
    IntegrityError,
    Model,
    SmallIntegerField,
    SqliteDatabase,
)

DB_FILE = Path(__file__).parent / "feeds.sqlite"

db = SqliteDatabase(DB_FILE, pragmas={"journal_mode": "wal", "foreign_keys": 1})


class Channel(Model):  # pylint:disable=too-few-public-methods
    channel_id = CharField(primary_key=True)
    name = CharField()
    epi_title_remove = CharField(default="")

    class Meta:  # pylint:disable=too-few-public-methods
        database = db


class Episode(Model):  # pylint:disable=too-few-public-methods
    vid_id = CharField(primary_key=True)
    channel = ForeignKeyField(Channel, backref="channel")
    title = CharField()
    description = CharField()
    pub_date = DateField()
    thumbnail = CharField()
    duration = SmallIntegerField()
    processed = BooleanField(default=False)

    class Meta:  # pylint:disable=too-few-public-methods
        database = db

    def mark_as_processed(self, duration: int) -> bool:
        self.processed = True
        self.duration = duration
        return self.save() == 1


class PDCTSDB:
    def __init__(self):
        db.connect()
        db.create_tables([Channel, Episode])

    def add_channel(self, channel_id: str, name: str, title_remove: str):
        log.debug(f"Adding new channel: {name}")
        ch = Channel(channel_id=channel_id, name=name, epi_title_remove=title_remove)
        try:
            row_count = ch.save(force_insert=True)
            log.debug(f"Channel {name} {'not' if row_count!=1 else ''} added!")
        except IntegrityError:
            log.debug(f"Channel {name} already exists!")

    def is_downloaded(self, episode_id: str) -> bool:
        log.debug(f"Checking if episode {episode_id} is already downloaded")
        return Episode.get(Episode.vid_id == episode_id) is not None

    def add_new_episode(
        self,
        episode_id: str,
        title: str,
        pub_date: str,
        thumb: str,
        description: str,
        channel: Channel,
    ):
        if channel.epi_title_remove:
            title = re.sub(
                re.compile(channel.epi_title_remove, re.IGNORECASE), "", title
            )
        title = title.strip()

        epi = Episode(
            vid_id=episode_id,
            channel=channel,
            title=title,
            description=description.strip(),
            thumbnail=thumb,
            pub_date=pub_date,
            duration=0,
        )
        try:
            row_count = epi.save(force_insert=True)
            log.debug(f"Episode '{title}' {'not' if row_count!=1 else ''} added!")
        except IntegrityError:
            log.debug(f"Episode '{title}' already exists!")

    def get_episodes(self, processed=None) -> Iterable[Episode]:
        if processed is None:
            return Episode.select().order_by(Episode.pub_date)
        else:
            return (
                Episode.select()
                .where(Episode.processed == processed)  # pylint:disable=singleton-comparison
                .order_by(Episode.pub_date)
            )
            

    def get_episodes2download(self) -> Iterable[Episode]:
        return self.get_episodes(processed=False)

    def get_channels(self) -> Iterable[Channel]:
        return Channel.select().order_by(Channel.channel_id)
