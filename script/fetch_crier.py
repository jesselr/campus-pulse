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
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def main():
    html = fetch(URL)
    text = normalize_text(html)

    # Try to pull the visible page title, fall back to "The Crier"
    title = "The Crier"
    m = re.search(r"(The Latest Crier for .+)", text)
    if m:
        title = m.group(1).strip()

    # Remove obvious boilerplate if it appears (optional)
    text = re.sub(r"Central College Mission Statement.*?(?=\n\n|$)", "", text, flags=re.DOTALL).strip()

    # Keep it signage-friendly: truncate to ~1500 chars
    body = text
    if len(body) > 1500:
        body = body[:1500].rsplit(" ", 1)[0] + "…"

    payload = {
        "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": URL,
        "title": title,
        "items": [body] if body else []
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
