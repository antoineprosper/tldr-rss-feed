import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import formatdate
from html.parser import HTMLParser
import os
import urllib.request
import sys

ET.register_namespace("media", "http://search.yahoo.com/mrss/")

BASE_URL = "https://tldr.tech/crypto"
FEED_FILE = "feed.xml"
MAX_ITEMS = 30

class OGParser(HTMLParser):
    """Scrapes og:title and og:image from page <head>."""
    def __init__(self):
        super().__init__()
        self.og_title = None
        self.og_image = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs = dict(attrs)
            if attrs.get("property") == "og:title":
                self.og_title = attrs.get("content")
            elif attrs.get("property") == "og:image":
                self.og_image = attrs.get("content")

def fetch_og_data(url: str) -> tuple[str | None, str | None]:
    """Returns (og_title, og_image) or (None, None) on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        parser = OGParser()
        parser.feed(html)
        return parser.og_title, parser.og_image
    except Exception:
        return None, None

def make_pub_date(dt: datetime) -> str:
    return formatdate(dt.timestamp(), usegmt=True)

def url_is_live(url: str) -> bool:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if method == "HEAD":
                continue
            return False
        except Exception:
            return False
    return False

def build_new_item(date: datetime, title: str | None, image_url: str | None) -> ET.Element:
    date_str = date.strftime("%Y-%m-%d")
    url = f"{BASE_URL}/{date_str}"
    display_title = title if title else f"TLDR Crypto – {date_str}"  # fallback if scrape fails

    item = ET.Element("item")
    ET.SubElement(item, "title").text = display_title
    ET.SubElement(item, "link").text = url
    ET.SubElement(item, "guid", isPermaLink="true").text = url
    ET.SubElement(item, "pubDate").text = make_pub_date(date)

    if image_url:
        ET.SubElement(
            item,
            "{http://search.yahoo.com/mrss/}content",
            url=image_url,
            medium="image"
        )

    return item

def load_or_create_feed() -> ET.ElementTree:
    if os.path.exists(FEED_FILE):
        return ET.parse(FEED_FILE)
    rss = ET.Element("rss", version="2.0", attrib={
        "xmlns:media": "http://search.yahoo.com/mrss/"
    })
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "TLDR Crypto Daily"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Auto-generated daily links to TLDR Crypto"
    return ET.ElementTree(rss)

def main():
    today = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    date_str = today.strftime("%Y-%m-%d")
    url = f"{BASE_URL}/{date_str}"

    tree = load_or_create_feed()
    channel = tree.find("channel")

    if channel is None:
        rss = tree.getroot()
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "TLDR Crypto Daily"
        ET.SubElement(channel, "link").text = BASE_URL
        ET.SubElement(channel, "description").text = "Auto-generated daily links to TLDR Crypto"

    existing_guids = {el.text for el in channel.findall("item/guid")}

    if url in existing_guids:
        print(f"Already have {date_str}, nothing to do.")
        sys.exit(0)

    if not url_is_live(url):
        print(f"Not live yet: {url} — will retry in 30 min.")
        sys.exit(0)

    og_title, og_image = fetch_og_data(url)
    print(f"Title: {og_title}, Image: {og_image}")

    new_item = build_new_item(today, og_title, og_image)
    first_item_idx = next(
        (i for i, child in enumerate(channel) if child.tag == "item"),
        len(channel)
    )
    channel.insert(first_item_idx, new_item)

    for old_item in channel.findall("item")[MAX_ITEMS:]:
        channel.remove(old_item)

    ET.indent(tree, space="  ")
    tree.write(FEED_FILE, encoding="unicode", xml_declaration=True)
    print(f"Feed updated: {url}")

if __name__ == "__main__":
    main()
