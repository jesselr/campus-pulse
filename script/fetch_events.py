import json
import urllib.request
from datetime import datetime

ICS_URL = "https://central.edu/events/list/?ical=1"
OUT_PATH = "data/events.json"

def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8", errors="replace")

def unfold_ical(text: str) -> list[str]:
    lines = text.splitlines()
    out = []
    for line in lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out

def parse_dt(value: str) -> str:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1]
    if len(v) == 8:
        dt = datetime.strptime(v, "%Y%m%d")
        return dt.strftime("%Y-%m-%dT00:00:00")
    if "T" in v:
        fmt = "%Y%m%dT%H%M%S" if len(v) >= 15 else "%Y%m%dT%H%M"
        dt = datetime.strptime(v, fmt)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    return v

def parse_ics_events(text: str) -> list[dict]:
    lines = unfold_ical(text)
    events = []
    ev = None

    for line in lines:
        if line == "BEGIN:VEVENT":
            ev = {}
            continue
        if line == "END:VEVENT":
            if ev:
                events.append(ev)
            ev = None
            continue
        if ev is None or ":" not in line:
            continue

        key, val = line.split(":", 1)
        key = key.split(";", 1)[0].upper()

        if key in ("DTSTART", "DTEND"):
            ev[key] = parse_dt(val)
        elif key in ("SUMMARY", "LOCATION", "URL", "DESCRIPTION"):
            ev[key] = val.strip()

    return events

def main():
    ics = fetch_text(ICS_URL)
    raw = parse_ics_events(ics)

    out = []
    for e in raw:
        out.append({
            "title": e.get("SUMMARY", "Event"),
            "start": e.get("DTSTART"),
            "end": e.get("DTEND"),
            "location": e.get("LOCATION", ""),
            "url": e.get("URL", ""),
            "description": e.get("DESCRIPTION", "")
        })

    # sort by start time
    out.sort(key=lambda x: x["start"] or "")

    payload = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "source": ICS_URL,
        "events": out
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

if __name__ == "__main__":
    main()
