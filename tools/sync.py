#!/usr/bin/env python3
"""Airtable -> GitHub Pages data sync (runs in GitHub Actions).

Reads AIRTABLE_PAT from the environment, fetches all records from the
configured base/table/view, converts to the archive format, splits into
small chunk files under data/, and rewrites manifest.json.

Env vars:
    AIRTABLE_PAT      (required) Personal Access Token with data.records:read
    AIRTABLE_BASE     (default: appGwL6PPsIsZIS9a)
    AIRTABLE_TABLE    (default: tbljINNeF0EmAMPJg)
    AIRTABLE_VIEW     (default: viw4626Nu6AswCSzy)
    DATA_DIR          (default: data)
    TRANSCRIPT_LIMIT  (default: 2000)
    TARGET_BYTES      (default: 112640)
"""
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = os.environ.get("AIRTABLE_BASE", "appGwL6PPsIsZIS9a")
TABLE = os.environ.get("AIRTABLE_TABLE", "tbljINNeF0EmAMPJg")
VIEW = os.environ.get("AIRTABLE_VIEW", "viw4626Nu6AswCSzy")
DATA_DIR = os.environ.get("DATA_DIR", "data")
TRANSCRIPT_LIMIT = int(os.environ.get("TRANSCRIPT_LIMIT", "2000"))
TARGET_BYTES = int(os.environ.get("TARGET_BYTES", "112640"))

YOUTUBE_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?[^#]*v=|embed/|shorts/|live/|v/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)
THUMB_RE = re.compile(r"i\.ytimg\.com/vi/([A-Za-z0-9_-]{11})")


def api_get(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "health-video-archive-sync/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_all(token):
    records, offset = [], None
    while True:
        params = {"pageSize": 100, "view": VIEW}
        if offset:
            params["offset"] = offset
        url = (f"https://api.airtable.com/v0/{BASE}/"
               f"{urllib.parse.quote(TABLE, safe='')}?{urllib.parse.urlencode(params)}")
        data = api_get(url, token)
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def video_id_from(fields):
    for key, rx in (("url", YOUTUBE_RE), ("썸네일", THUMB_RE)):
        m = rx.search(str(fields.get(key) or ""))
        if m:
            return m.group(1)
    return None


def split_tags(raw):
    if not raw:
        return []
    text = re.sub(r"^[^:,;\n]*해시태그\s*[:\uff1a]\s*", "", str(raw))
    tags = []
    for p in re.split(r"[,;\n]", text):
        t = p.strip().lstrip("#").strip()
        if t and t not in tags:
            tags.append(t)
    return tags


def convert(records):
    videos, skipped = [], 0
    for r in records:
        f = r.get("fields", {})
        title = str(f.get("title") or "").strip()
        vid = video_id_from(f)
        if not title or not vid:
            skipped += 1
            continue
        videos.append({
            "title": title,
            "videoId": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "description": str(f.get("설명") or "").strip(),
            "tags": split_tags(f.get("hashtags")),
            "date": str(f.get("업로드일") or "")[:10],
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "transcript": str(f.get("transcript") or "").strip()[:TRANSCRIPT_LIMIT],
            "privacy": str(f.get("privacyStatus") or "").strip() or "unknown",
        })
    videos.sort(key=lambda v: v["date"], reverse=True)
    return videos, skipped


def write_chunks(videos):
    os.makedirs(DATA_DIR, exist_ok=True)
    for name in os.listdir(DATA_DIR):
        if name.endswith(".json"):
            os.remove(os.path.join(DATA_DIR, name))
    parts, current, cur_size = [], [], 0
    for v in videos:
        blob = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        size = len(blob.encode("utf-8")) + 1
        if current and cur_size + size > TARGET_BYTES:
            parts.append(current)
            current, cur_size = [], 0
        current.append(v)
        cur_size += size
    if current:
        parts.append(current)
    for i, chunk in enumerate(parts):
        with open(os.path.join(DATA_DIR, f"part-{i:02d}.json"), "w", encoding="utf-8") as fh:
            json.dump(chunk, fh, ensure_ascii=False, separators=(",", ":"))
    manifest = {"parts": len(parts), "count": len(videos),
                "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    with open(os.path.join(DATA_DIR, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    return len(parts)


def main():
    token = os.environ.get("AIRTABLE_PAT")
    if not token:
        print("ERROR: AIRTABLE_PAT env var is required", file=sys.stderr)
        sys.exit(1)
    records = fetch_all(token)
    print(f"fetched {len(records)} records from Airtable")
    videos, skipped = convert(records)
    print(f"converted {len(videos)} videos (skipped {skipped})")
    n = write_chunks(videos)
    print(f"wrote {n} chunk files + manifest.json to {DATA_DIR}/")


if __name__ == "__main__":
    main()
