import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import formatdate
import os

BASE_URL = "https://tldr.tech/crypto"
FEED_FILE = "feed.xml"
MAX_ITEMS = 30  # keep a rolling window

def make_pub_date(dt: datetime) -> str:
    """RFC 2822 date string required by RSS spec."""
    return formatdate(dt.timestamp(), usegmt=True)

def build_new_item(date: datetime) -> ET.Element:
    date_str = date.strftime("%Y-%m-%d")
    url = f"{BASE_URL}/{date_str}"

    item = ET.Element("item")
    ET.SubElement(item, "title").text = f"TLDR Crypto – {date_str}"
    ET.SubElement(item, "link").text = url
    ET.SubElement(item, "guid", isPermaLink="true").text = url
    ET.SubElement(item, "pubDate").text = make_pub_date(date)
    return item

def load_or_create_feed() -> ET.ElementTree:
    if os.path.exists(FEED_FILE):
        return ET.parse(FEED_FILE)

    # Bootstrap a fresh feed
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "TLDR Crypto Daily"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Auto-generated daily links to TLDR Crypto"
    return ET.ElementTree(rss)

def main():
    today = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    tree = load_or_create_feed()
    channel = tree.find("channel")

    # Avoid duplicate entries
    existing_guids = {el.text for el in channel.findall("item/guid")}
    new_url = f"{BASE_URL}/{today.strftime('%Y-%m-%d')}"

    if new_url not in existing_guids:
        new_item = build_new_item(today)
        # Insert after channel metadata (before existing items)
        first_item_idx = next(
            (i for i, child in enumerate(channel) if child.tag == "item"),
            len(channel)
        )
        channel.insert(first_item_idx, new_item)

    # Prune to MAX_ITEMS
    items = channel.findall("item")
    for old_item in items[MAX_ITEMS:]:
        channel.remove(old_item)

    ET.indent(tree, space="  ")
    tree.write(FEED_FILE, encoding="unicode", xml_declaration=True)
    print(f"Feed updated. Items: {len(channel.findall('item'))}")

if __name__ == "__main__":
    main()
