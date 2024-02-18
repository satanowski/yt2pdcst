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


class Source(Model):  # pylint:disable=too-few-public-methods
    source_id = CharField(primary_key=True)
    is_playlist = BooleanField(default=False)
    name = CharField()
    min_length = SmallIntegerField()
    title_must_contain = CharField(default=None)
    epi_title_remove = CharField(default="")


class Episode(Model):  # pylint:disable=too-few-public-methods
    vid_id = CharField(primary_key=True)
    source = ForeignKeyField(Source, backref="source")
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

        Source.bind(self._db)
        Episode.bind(self._db)

        self._db.connect()
        self._db.create_tables([Source, Episode])

    def add_source(
        self,
        source_id: str,
        name: str,
        is_playlist: bool,
        title_remove: str,
        min_length: int,
        must_contain: str,
    ):
        log.debug(
            f"Adding new source ({'playlist' if is_playlist else 'channel'}): {name}"
        )
        src = Source(
            source_id=source_id,
            is_playlist=is_playlist,
            name=name,
            epi_title_remove=title_remove,
            min_length=min_length,
            title_must_contain=must_contain,
        )
        try:
            row_count = src.save(force_insert=True)
            log.debug(f"Source {name} {'not' if row_count!=1 else ''} added!")
        except IntegrityError:
            log.debug(f"Source {name} already exists!")

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
        source: Source,
    ):
        if self.epi_exists(episode_id):
            log.debug(f"Episode '{title}' already exists!")
            return

        if source.epi_title_remove:
            title = re.sub(
                re.compile(source.epi_title_remove, re.IGNORECASE), "", title
            )
        title = title.strip()

        epi = Episode(
            vid_id=episode_id,
            source=source,
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

    def get_sources(self) -> Iterable[Source]:
        return Source.select()

    def mark_missing(self, present_files: Iterable[str]):
        for epi in Episode.select().where(Episode.present == True):
            if f"{epi.vid_id}.m4a" not in present_files:
                epi.mark_as_missing()

    def close(self):
        self._db.close()
