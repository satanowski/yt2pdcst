from collections import namedtuple

import feedparser
import yt_dlp
from loguru import logger as log

YT_RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"

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
