# yt2pdcst

Turn YT channels into Podcast

## Installation

### Create virtual env
```bash
python3 -m venv .env
source .env/bin/activate
```

### Install required packages
```bash
pip install -U pip
pip install -r requirements
```

## Configuration
Update configuration file `config.toml`:
```ini
downlad_dir = "/tmp"         # where to download files before audio extraction
host_dir = "/var/www/pdcsts" # destination of processed files


[RSS_SETTINGS]
base_url = "http://podcasts.mydoamin.foo" # address accessible for your podcast client
index = "index.xml"

[RSS_META]
copyright = "something @ 2024"
podcast_author = "Some author"
podcast_categories = ["other"]
podcast_description = "Lorem ipsum"
podcast_email = "fake@email.com"
podcast_image_url = "https://some.image.link"
podcast_name = "YT2Podcast"
podcast_subtitle = "something something"
podcast_summary = "Lorem ipsum"
podcast_item_base_url = "http://podcasts.mydoamin.foo/files"
```

## Usage

### Add channel
```bash
$ python main.py add-channel <ChannelID> "Channel name"
```

We can clean episode titles from unwanted strings:
```bash
$ python main.py add-channel --title-remove "\| (?:NEWSY BEZ WIRUSA)|(?:[#|@]\d+)|\| Karol Modzelewski"  UC4RkUl120K4nct7dYrk19_A "Karol Modzelewski"
```

### Retrieve newest episodes
```bash
$ python main.py get-episodes
```

### Download and extract audio tracks
```bash
$ python main.py download-episodes
```

### Generate rss file
```bash
$ python main.py write-rss
```

## Hosting and automation...
... is up to you.

## To do:
- removing old files
- ...