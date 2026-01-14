import json, re, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

URL = "https://web.central.edu/MyCentral/thecrier/full.php"
OUT = "data/crier.json"

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        t = data.strip()
        if t:
            self.parts.append(t)

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def normalize_text(html: str) -> str:
    p = TextExtractor()
    p.feed(html)
    text = "\n".join(p.parts)
    text = text.replace("\u00a0", " ")
    # collapse junk whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def main():
    html = fetch(URL)
    text = normalize_text(html)

    # Split into chunks using the Crier divider (often appears as "* * *")
    chunks = [c.strip() for c in re.split(r"\*\s*\*\s*\*", text) if c.strip()]

    # Pull a title-ish line if present
    title = None
    if chunks:
        first_line = chunks[0].splitlines()[0].strip()
        if "Crier" in first_line:
            title = first_line

    # Filter out mission statement chunk if present (keeps announcements cleaner)
    filtered = []
    for c in chunks:
        if "Central College Mission Statement" in c:
            continue
        filtered.append(c)

    # Keep top N chunks and shorten each for signage
    items = []
    for c in filtered[:12]:
        c = re.sub(r"\s+\n", "\n", c)
        c = re.sub(r"\n\s+", "\n", c).strip()
        # trim overly long blocks
        if len(c) > 500:
            c = c[:500].rsplit(" ", 1)[0] + "…"
        items.append(c)

    payload = {
        "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": URL,
        "title": title or "The Crier",
        "items": items
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
