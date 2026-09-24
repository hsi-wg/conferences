#!/usr/bin/env python3
"""Generate session .qmd files from YAML master schedule.

Usage:
  python scripts/generate_sessions.py                # normal run (no overwrite of existing unless identical)
  python scripts/generate_sessions.py --force        # overwrite existing files
  python scripts/generate_sessions.py --dry-run      # show actions only

Assumptions:
  - sessions.yaml lives in HSI2025/schedule/
  - day mapping: day 1 -> day1/, etc.
  - Each session id corresponds to desired filename <id>.qmd
  - Duration is ISO 8601 (e.g., PT90M) but body currently only shows start & derived end
"""

from __future__ import annotations
import argparse
import hashlib
import sys
import textwrap
from datetime import datetime
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # We'll error later with a clearer message

ROOT = Path(__file__).resolve().parents[1]  # points to HSIConferenceWebsite/
SCHEDULE_DIR = ROOT / "HSI2025" / "schedule"
# Our data file is sessions.yml (not .yaml)
YAML_FILE = SCHEDULE_DIR / "sessions.yml"


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate session .qmd files from YAML")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing differing files")
    p.add_argument("--dry-run", action="store_true",
                   help="Show intended actions without writing")
    return p.parse_args()


def load_sessions():
    if not YAML_FILE.exists():
        raise SystemExit(f"YAML file not found: {YAML_FILE}")
    if yaml is None:
        raise SystemExit(
            "PyYAML is required to read sessions.yml. Install with: pip install pyyaml")
    data = yaml.safe_load(YAML_FILE.read_text(encoding="utf-8"))
    sessions = data.get("sessions", []) if data else []
    if not isinstance(sessions, list):
        raise SystemExit("sessions.yml malformed: 'sessions' should be a list")
    return sessions


def iso_to_local_fragment(iso: str) -> tuple[str, str]:
    try:
        if not isinstance(iso, datetime):
            iso = iso.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
        elif isinstance(iso, datetime):
            dt = iso
        else:
            raise ValueError("Invalid iso format")
    except ValueError:
        return iso, iso
    # Show local-like HH:MM (UTC assumed) and keep ISO
    return dt.strftime("%H:%M"), dt.isoformat()


def slugify(text: str) -> str:
    """Create a filename-safe slug from an id/title.
    Lowercase, replace non-alphanumerics with '-', collapse repeats, trim dashes.
    """
    import re as _re
    if not text:
        return "session"
    s = text.lower()
    s = _re.sub(r"[^a-z0-9]+", "-", s)
    s = _re.sub(r"-+", "-", s)
    s = s.strip('-')
    return s or "session"


def build_front_matter(sess: dict) -> str:
    # Map current schema -> front matter
    title = sess.get("title", "Untitled Session")
    authors = sess.get("authors") or []
    # In new schema, sessionType (array) replaces category
    session_types = sess.get("sessionType") or []
    category = session_types[0] if session_types else "Session"
    tags = sess.get("tags") or []
    abstract = (sess.get("abstract") or "").strip()
    start = sess.get("start")
    end = sess.get("end")
    duration = sess.get("duration")
    if not (start and (end or duration)):
        raise ValueError(
            f"Session {sess.get('id')} missing start and end/duration")

    fm_lines = [
        "---",
        f"title: \"{title}\"",
        f"author: \"{' ; '.join(authors)}\"",
        f"category: {category}",
    ]
    if tags:
        tags_serial = ",".join([f'\"{t}\"' for t in tags])
        fm_lines.append(f"tags: [{tags_serial}]")
    if abstract:
        fm_lines.append(f"abstract: |\n  {abstract.replace('\n', '\n  ')}")
    fm_lines.append(f"date: {start}")
    if duration:
        fm_lines.append(f"duration: {duration}")
    if end:
        fm_lines.append(f"end: {end}")
    fm_lines.append("---")
    return "\n".join(fm_lines)


BODY_TEMPLATE = textwrap.dedent(
    """
    # {title}

    **Speakers:** {authors}
    **Time:** {start_hm}–{end_hm} (UTC)  
    **Category:** {category}  
    **Tags:** {tags}

    ## Abstract
    {abstract}

    ## Bio
    Bios TBD.
    """
).lstrip()


def render_body(sess: dict) -> str:
    start_hm, _ = iso_to_local_fragment(sess.get("start", ""))
    end_hm, _ = iso_to_local_fragment(sess.get("end", ""))
    tags = ", ".join(sess.get("tags", [])) or "—"
    authors = "; ".join(sess.get("authors", []))
    # sessionType to category label
    session_types = sess.get("sessionType") or []
    category = session_types[0] if session_types else "Session"
    abstract = (sess.get("abstract") or "").strip() or "TBD."
    return BODY_TEMPLATE.format(
        title=sess.get("title", "Untitled Session"),
        authors=authors,
        start_hm=start_hm,
        end_hm=end_hm,
        category=category,
        tags=tags,
        abstract=abstract,
    )


def file_needs_update(path: Path, new_content: str) -> bool:
    if not path.exists():
        return True
    old_hash = hashlib.sha256(path.read_text(
        encoding="utf-8").encode()).hexdigest()
    new_hash = hashlib.sha256(new_content.encode()).hexdigest()
    return old_hash != new_hash


def main():
    args = parse_args()
    sessions = load_sessions()
    if not sessions:
        print("No sessions found.")
        return

    written = 0
    skipped = 0
    for sess in sessions:
        day_dir = SCHEDULE_DIR / f"day{sess['day']}"
        day_dir.mkdir(parents=True, exist_ok=True)
        outfile = day_dir / f"{slugify(str(sess.get('id') or ''))}.qmd"
        content = build_front_matter(sess) + "\n\n" + render_body(sess)
        if not file_needs_update(outfile, content) and not args.force:
            skipped += 1
            continue
        action = "WRITE" if outfile.exists() else "CREATE"
        if args.dry_run:
            print(f"{action} {outfile}")
            continue
        if outfile.exists() and not args.force and file_needs_update(outfile, content):
            print(f"Skipping (differs, use --force): {outfile}")
            skipped += 1
            continue
        outfile.write_text(content, encoding="utf-8")
        written += 1
        print(f"{action} {outfile}")

    if args.dry_run:
        print("Dry run complete.")
    else:
        print(f"Done. Written: {written}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
