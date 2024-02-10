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


class Channel(Model):  # pylint:disable=too-few-public-methods
    channel_id = CharField(primary_key=True)
    name = CharField()
    min_length = SmallIntegerField()
    epi_title_remove = CharField(default="")


class Episode(Model):  # pylint:disable=too-few-public-methods
    vid_id = CharField(primary_key=True)
    channel = ForeignKeyField(Channel, backref="channel")
    title = CharField()
    description = CharField()
    pub_date = DateField()
    thumbnail = CharField()
    duration = SmallIntegerField()
    processed = BooleanField(default=False)
    present = BooleanField(default=False)

    def mark_as_processed(self, duration: int) -> bool:
        self.processed = True
        self.present = True
        self.duration = duration
        return self.save() == 1

    def mark_as_missing(self) -> bool:
        self.present = False
        log.debug(f"Mark {self.vid_id} as not present")
        return self.save() == 1


class PDCTSDB:
    def __init__(self):
        self._db = SqliteDatabase(
            DB_FILE,
            pragmas=(
                ("journal_mode", "wal"),
                ("foreign_keys", 1),
                ("cache_size", -1024 * 64),
            ),
        )

        Channel.bind(self._db)
        Episode.bind(self._db)

        self._db.connect()
        self._db.create_tables([Channel, Episode])

    def add_channel(self, channel_id: str, name: str, title_remove: str, min_length: int):
        log.debug(f"Adding new channel: {name}")
        ch = Channel(channel_id=channel_id, name=name, epi_title_remove=title_remove, min_length=min_length)
        try:
            row_count = ch.save(force_insert=True)
            log.debug(f"Channel {name} {'not' if row_count!=1 else ''} added!")
        except IntegrityError:
            log.debug(f"Channel {name} already exists!")

    def is_downloaded(self, episode_id: str) -> bool:
        log.debug(f"Checking if episode {episode_id} is already downloaded")
        return Episode.get(Episode.vid_id == episode_id) is not None

    def epi_exists(self, epi_id: str) -> bool:
        return Episode.get_or_none(Episode.vid_id == epi_id) is not None

    def add_new_episode(
        self,
        episode_id: str,
        title: str,
        pub_date: str,
        thumb: str,
        description: str,
        channel: Channel,
    ):
        if self.epi_exists(episode_id):
            log.debug(f"Episode '{title}' already exists!")
            return

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
            present=False,
            processed=False,
        )
        try:
            row_count = epi.save(force_insert=True)
            log.debug(f"Episode '{title}' {'not' if row_count!=1 else ''} added!")
        except IntegrityError:
            log.debug(f"Episode '{title}' already exists!")

    def get_episodes(
        self, processed: bool | None, present: bool | None
    ) -> Iterable[Episode]:
        q = Episode.select()
        if processed is not None:
            q = q.where(Episode.processed == processed)
        if present is not None:
            q = q.where(Episode.present == present)

        return q.order_by(Episode.pub_date)

    def get_episodes2download(self) -> Iterable[Episode]:
        return self.get_episodes(processed=False, present=False).limit(5)

    def get_channels(self) -> Iterable[Channel]:
        return Channel.select()

    def mark_missing(self, present_files: Iterable[str]):
        for epi in Episode.select().where(Episode.present == True):
            if f"{epi.vid_id}.m4a" not in present_files:
                epi.mark_as_missing()

    def close(self):
        self._db.close()
