import json, re, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

URL = "https://web.central.edu/MyCentral/thecrier/full.php"
OUT = "data/crier.json"

BLOCK_TAGS = {"br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr", "hr"}

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00a0", " ")  # nbsp
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def has_class(attrs, class_name: str) -> bool:
    for k, v in attrs:
        if k.lower() == "class" and v:
            # class attribute may contain multiple classes
            classes = set(v.split())
            return class_name in classes
    return False

class CrierParser(HTMLParser):
    """
    Extracts:
      - issue title from <div class="crierdate">
      - section headings from <div class="heading">
      - announcements from tables containing:
          <td class="listing">TITLE</td>
          <td class="content">BODY...</td>
    Produces items as strings that your index.js can already rotate.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.issue_title = None

        self.current_section = None

        self.in_date = False
        self.date_parts = []

        self.in_heading = False
        self.heading_parts = []

        self.in_listing = False
        self.listing_parts = []

        self.in_content = False
        self.content_parts = []

        self.pending_title = None

        self.items = []

        self._skip_depth = 0  # script/style

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag in ("script", "style"):
            self._skip_depth += 1
            return

        # Enter issue title
        if tag == "div" and has_class(attrs, "crierdate"):
            self.in_date = True
            self.date_parts = []

        # Enter section heading
        if tag == "div" and has_class(attrs, "heading"):
            self.in_heading = True
            self.heading_parts = []

        # Enter announcement title
        if tag == "td" and has_class(attrs, "listing"):
            self.in_listing = True
            self.listing_parts = []

        # Enter announcement content
        if tag == "td" and has_class(attrs, "content"):
            self.in_content = True
            self.content_parts = []

        # While in content, preserve basic paragraph-ish structure
        if self.in_content and tag in BLOCK_TAGS:
            self.content_parts.append("\n")

        # Also add breaks inside headings if needed
        if self.in_heading and tag in ("br",):
            self.heading_parts.append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
            return

        # Exit issue title
        if tag == "div" and self.in_date:
            raw = clean_text(" ".join(self.date_parts))
            # Your page text is like: "The Latest Crier for Jan 21, 2026"
            self.issue_title = raw if raw else self.issue_title
            self.in_date = False
            self.date_parts = []

        # Exit section heading
        if tag == "div" and self.in_heading:
            sec = clean_text(" ".join(self.heading_parts))
            self.current_section = sec if sec else self.current_section
            self.in_heading = False
            self.heading_parts = []

        # Exit announcement title td
        if tag == "td" and self.in_listing:
            title = clean_text(" ".join(self.listing_parts))
            self.pending_title = title if title else self.pending_title
            self.in_listing = False
            self.listing_parts = []

        # Exit announcement content td -> finalize announcement
        if tag == "td" and self.in_content:
            body = clean_text("".join(self.content_parts))

            title = self.pending_title or ""
            section = self.current_section or ""

            # Build a single string item that your index already understands:
            # first line becomes slide heading; body becomes slide body
            # we put section at top of body so it shows under the title.
            if title or body:
                if section:
                    item = f"{title}\n{section}\n\n{body}".strip()
                else:
                    item = f"{title}\n\n{body}".strip()

                self.items.append(item)

            # reset for next announcement
            self.pending_title = None
            self.in_content = False
            self.content_parts = []

        # Add line breaks in content at closing block tags
        if self.in_content and tag in BLOCK_TAGS:
            self.content_parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        t = data.strip()
        if not t:
            return

        if self.in_date:
            self.date_parts.append(t)
        elif self.in_heading:
            self.heading_parts.append(t)
        elif self.in_listing:
            self.listing_parts.append(t)
        elif self.in_content:
            # Keep words separated; we already inject \n around blocks
            self.content_parts.append(t + " ")

def main():
    html = fetch(URL)

    p = CrierParser()
    p.feed(html)

    title = p.issue_title or "The Crier"

    # If the page ever fails to match structure, fall back to old behavior lightly
    items = [i for i in p.items if i.strip()]

    payload = {
        "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": URL,
        "title": title,
        "items": items
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
