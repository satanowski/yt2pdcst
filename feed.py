from collections import namedtuple
from datetime import datetime

import feedparser
import yt_dlp
from loguru import logger as log

YT_RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
YT_PLS_BASE = "https://www.youtube.com/playlist?list={}"

RawEpisode = namedtuple("RawEpisode", "epi_id,title,pub_date,thumb,description")


def get_channel_episodes(channel_id: str, must_contain=None):
    url = YT_RSS_BASE.format(channel_id)
    log.debug(f"Getting and parsing Feed: {url}")
    feed = feedparser.parse(url)
    for entry in feed["entries"]:
        if must_contain:  # skip episode if does not match"must_contain"
            if must_contain.lower() not in entry["title"].lower():
                continue
        yield RawEpisode(
            epi_id=entry["yt_videoid"],
            title=entry["title"],
            pub_date=entry["published"],
            thumb=entry["media_thumbnail"][0]["url"],
            description=entry["summary_detail"]["value"],
        )


def get_playlist_episodes(playlist_id: str, must_contain=None):
    url = YT_PLS_BASE.format(playlist_id)
    log.debug(f"Getting and parsing Playlist: {url}")
    with yt_dlp.YoutubeDL() as yt:
        meta = yt.extract_info(url, process=False)
        for entry in meta["entries"]:
            if must_contain:  # skip episode if does not match"must_contain"
                if must_contain.lower() not in entry["title"].lower():
                    continue
            yield RawEpisode(
                epi_id=entry["id"],
                title=entry["title"],
                pub_date=datetime.now(),
                thumb=entry["thumbnails"][0]["url"],
                description=entry["description"] or "",
            )


def get_source_episodes(source_id: str, is_playlist: bool, must_contain=None):
    return (
        get_playlist_episodes(source_id, must_contain) if is_playlist else get_channel_episodes(source_id, must_contain)
    )


def get_audio(vid_id: str, download_dir: str):
    ydl_opts = {
        "format": "m4a/bestaudio/best",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
        "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
        "match_filter": yt_dlp.utils.match_filter_func("!is_live"),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            return ydl.download([f"https://www.youtube.com/watch?v={vid_id}"]) == 0
        except yt_dlp.utils.ExtractorError:
            log.error(f"Cannot extract audio from stream {vid_id}")
        except yt_dlp.utils.DownloadError:
            log.error(f"Cannot downlaod stream {vid_id}")
        return False
