from pathlib import Path

import feedparser
import toml
import yt_dlp
from loguru import logger as log

YT_RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
FEEDS_FILE = Path(__file__).parent / "feeds.toml"


def load_feed_list(feed_file=FEEDS_FILE) -> dict:
    if not feed_file.exists():
        log.error(f"No feed file {feed_file.name}")
        return {}

    return toml.load(feed_file.open("r", encoding="utf-8"))


def get_feed_entries(channel_id: str):
    url = YT_RSS_BASE.format(channel_id)
    log.debug(f"Getting and parsing Feed: {url}")
    feed = feedparser.parse(url)
    for entry in feed["entries"]:
        yield (
            entry["yt_videoid"],
            entry["title"],
            entry["published"],
            entry["media_thumbnail"][0]["url"],
            entry["summary_detail"]["value"],
        )


def get_audio(vid_id: str, download_dir: str):
    ydl_opts = {
        "format": "m4a/bestaudio/best",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
        "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.download([f"https://www.youtube.com/watch?v={vid_id}"]) == 0
