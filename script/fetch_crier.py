import json, re, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

URL = "https://web.central.edu/MyCentral/thecrier/full.php"
OUT = "data/crier.json"

class VisibleTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0  # inside <script> or <style>

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1
        # add line breaks around common block-ish elements to keep structure
        if tag in ("br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr", "hr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        t = data.strip()
        if t:
            self.parts.append(t)

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def normalize_text(html: str) -> str:
    p = VisibleTextExtractor()
    p.feed(html)
    text = "\n".join(p.parts)
    text = text.replace("\u00a0", " ")

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text

def main():
    html = fetch(URL)
    text = normalize_text(html)

    # Find title if present
    title = "The Crier"
    m = re.search(r"(The Latest Crier for [A-Za-z]{3,} \d{1,2}, \d{4})", text)
    if m:
        title = m.group(1).strip()

    # Optional: remove the mission statement block if it’s included
    #text = re.sub(r"Central College Mission Statement.*?(?=\n\n|$)", "", text, flags=re.DOTALL).strip()

    # Signage-friendly trim
    if len(text) > 8000:
        text = text[:8000].rsplit(" ", 1)[0] + "…"

    payload = {
        "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": URL,
        "title": title,
        "items": [text] if text else []
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
