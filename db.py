from collections import namedtuple
from pathlib import Path

import pickledb

DB_FILE = Path(__file__).parent / "feeds.db"

DB_L_DOWN = "downloaded"
DB_L_PUB = "published"

DB_D_TITLES = "titles"
DB_D_THUMBS = "thumbs"
DB_D_DESCS = "descriptions"
DB_D_DATES = "dates"
DB_D_CHANNELS = "channels"
DB_D_DURATIONS = "durations"

Episode = namedtuple("episode", "id,num,title,date,thumb,desc,channel,duration")


class FeedDB:
    def __init__(self, db_file=DB_FILE):
        self._db = pickledb.load(DB_FILE, True)
        self.setup()

    def setup(self):
        for alist in (DB_L_DOWN, DB_L_PUB):
            if not self._db.exists(alist):
                self._db.lcreate(alist)

        for adict in (
            DB_D_TITLES,
            DB_D_THUMBS,
            DB_D_DESCS,
            DB_D_DATES,
            DB_D_CHANNELS,
            DB_D_DURATIONS,
        ):
            if not self._db.exists(adict):
                self._db.dcreate(adict)

    def is_downloaded(self, vid_id: str) -> bool:
        return self._db.lexists(DB_L_DOWN, vid_id)

    def is_published(self, vid_id: str) -> bool:
        return self._db.lexists(DB_L_PUB, vid_id)

    def add_vid(
        self,
        vid_id: str,
        title: str,
        created: str,
        thumb: str,
        desc: str,
        channel: str,
        duration: int,
    ):
        if self.is_downloaded(vid_id):
            return
        self._db.ladd(DB_L_DOWN, vid_id)
        self._db.dadd(DB_D_TITLES, (vid_id, title))
        self._db.dadd(DB_D_THUMBS, (vid_id, thumb))
        self._db.dadd(DB_D_DESCS, (vid_id, desc))
        self._db.dadd(DB_D_DATES, (vid_id, created))
        self._db.dadd(DB_D_CHANNELS, (vid_id, channel))
        self._db.dadd(DB_D_DURATIONS, (vid_id, duration))

    def get_episodes(self):
        for idx, ep_id in enumerate(self._db.lgetall(DB_L_DOWN)):
            yield Episode(
                id=ep_id,
                num=idx,
                title=self._db.dget(DB_D_TITLES, ep_id),
                date=self._db.dget(DB_D_DATES, ep_id),
                thumb=self._db.dget(DB_D_THUMBS, ep_id),
                desc=self._db.dget(DB_D_DESCS, ep_id),
                channel=self._db.dget(DB_D_CHANNELS, ep_id),
                duration=self._db.dget(DB_D_DURATIONS, ep_id),
            )
