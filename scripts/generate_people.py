#!/usr/bin/env python3
import csv
import os
import re
import sys
from collections import defaultdict

try:
    import yaml
except ImportError:
    yaml = None

ROOT = os.path.dirname(os.path.dirname(__file__))
SCHEDULE_DIR = os.path.join(ROOT, 'HSI2025', 'schedule')
CSV_PATH = os.path.join(SCHEDULE_DIR, 'people.csv')
SESSIONS_YML = os.path.join(SCHEDULE_DIR, 'sessions.yml')
OUT_YML = os.path.join(SCHEDULE_DIR, 'people.from_csv.yml')

PAREN_RE = re.compile(r"\s*\([^)]*\)")
PREFIXES = ["chair:", "co-chair:"]


def norm(s: str) -> str:
    return (s or '').strip()


def strip_parens(name: str) -> str:
    return PAREN_RE.sub('', name or '').strip()


def strip_prefixes(name: str) -> str:
    n = (name or '').strip()
    low = n.lower()
    for p in PREFIXES:
        if low.startswith(p):
            return n[len(p):].strip()
    return n


def collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or '').strip())


def split_name(name: str):
    n = strip_prefixes(strip_parens(name))
    parts = [p for p in re.split(r"[\s,]+", n) if p]
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[-1])


def first_initial(name: str) -> str:
    f, _ = split_name(name)
    return f[:1].lower()


def last_name(name: str) -> str:
    _, l = split_name(name)
    return l.lower()


def name_key(name: str) -> str:
    n = strip_prefixes(strip_parens(name))
    n = n.replace('.', ' ').lower()
    n = re.sub(r"[^a-z\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def id_from_name(name: str) -> str:
    f, l = split_name(name)
    if not f and not l:
        return "unknown"
    return f"{f}.{l}".replace(' ', '')


def load_sessions():
    def build_maps(sessions_list):
        auth_map = defaultdict(set)
        chair_map = defaultdict(set)
        title_map = {}
        for sess in sessions_list:
            sid = sess.get('id')
            if not sid:
                continue
            title_map[sid] = collapse_ws(sess.get('title', ''))
            for a in (sess.get('authors') or []):
                if isinstance(a, str):
                    auth_map[name_key(a)].add(sid)
            chair = sess.get('chair')
            if chair:
                chair_map[name_key(chair)].add(sid)
        return auth_map, chair_map, title_map

    if yaml is not None:
        with open(SESSIONS_YML, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        sessions = data.get('sessions', []) if isinstance(data, dict) else []
        auth_map, chair_map, title_map = build_maps(sessions)
        return sessions, auth_map, chair_map, title_map

    # Fallback: naive parser for sessions.yml to extract id, title, authors, chair
    print("pyyaml not installed; using fallback parser for sessions.yml",
          file=sys.stderr)
    text = ''
    try:
        with open(SESSIONS_YML, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Cannot read sessions.yml: {e}", file=sys.stderr)
        return [], defaultdict(set), defaultdict(set), {}

    sessions = []
    current = None
    for line in text.splitlines():
        if line.strip().startswith('- id:'):
            # start new session
            if current:
                sessions.append(current)
            sid = line.split(':', 1)[1].strip()
            current = {'id': sid, 'authors': []}
        elif current is not None:
            if line.strip().startswith('title:'):
                current['title'] = line.split(':', 1)[1].strip().strip('"')
            elif line.strip().startswith('chair:'):
                current['chair'] = line.split(':', 1)[1].strip().strip('"')
            elif line.strip().startswith('authors:'):
                # Expect inline array authors: ["A", "B"]
                arr = line.split(':', 1)[1].strip()
                m = re.findall(r'"([^"]+)"', arr)
                if m:
                    current['authors'] = m
            # stop when blank line and we have minimum
    if current:
        sessions.append(current)
    auth_map, chair_map, title_map = build_maps(sessions)
    return sessions, auth_map, chair_map, title_map


def match_sessions(person_name: str, talk_title: str, auth_map, chair_map, title_map):
    sessions = set()
    nk = name_key(person_name)
    if nk in auth_map:
        sessions |= auth_map[nk]
    if nk in chair_map:
        sessions |= chair_map[nk]

    # Heuristic: match by last name and first initial among author keys
    p_last = last_name(person_name)
    p_fi = first_initial(person_name)
    for akey in list(auth_map.keys()) + list(chair_map.keys()):
        # recover a representative string for comparison
        parts = akey.split()
        if not parts:
            continue
        a_last = parts[-1]
        a_fi = parts[0][:1] if parts[0] else ''
        if a_last == p_last and a_fi == p_fi:
            sessions |= auth_map.get(akey, set())
            sessions |= chair_map.get(akey, set())

    # Heuristic: match talk title to session title if provided
    tt = collapse_ws(strip_parens(talk_title))
    if tt:
        for sid, stitle in title_map.items():
            if tt and (tt.lower() in stitle.lower() or stitle.lower() in tt.lower()):
                sessions.add(sid)
    return sorted(sessions)


def read_people_csv():
    people_rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            people_rows.append(row)
    return people_rows


def merge_people(rows, auth_map, chair_map, title_map):
    merged = {}
    for r in rows:
        name = strip_prefixes(strip_parens(norm(r.get('Name'))))
        if not name:
            continue
        key = name_key(name)
        entry = merged.get(key)
        if not entry:
            entry = {
                'id': id_from_name(name),
                'name': name,
                'job_title': norm(r.get('Job Title')) or 'N/A',
                'email': norm(r.get('')) or norm(r.get('Email')) or 'N/A',
                'affiliation': norm(r.get('Affiliations')) or 'N/A',
                'country': norm(r.get('Country')) or 'N/A',
                'roles': [],
                'picture': 'N/A',
                'bio': 'N/A',
                'sessions': [],
            }
        # Roles
        if (norm(r.get('Chair/Organiser?')) or '').strip().upper() == 'Y':
            if 'Chair/Organiser' not in entry['roles']:
                entry['roles'].append('Chair/Organiser')
        if norm(r.get('Talk title')):
            if 'Speaker' not in entry['roles']:
                entry['roles'].append('Speaker')
        # Headshot/Bio flags might suggest availability but we keep actual paths as N/A
        # Merge fields if missing
        if entry['job_title'] == 'N/A' and norm(r.get('Job Title')):
            entry['job_title'] = norm(r.get('Job Title'))
        if entry['email'] == 'N/A' and (norm(r.get('')) or norm(r.get('Email'))):
            entry['email'] = norm(r.get('')) or norm(r.get('Email'))
        if entry['affiliation'] == 'N/A' and norm(r.get('Affiliations')):
            entry['affiliation'] = norm(r.get('Affiliations'))
        if entry['country'] == 'N/A' and norm(r.get('Country')):
            entry['country'] = norm(r.get('Country'))

        # Session matching
        talk_title = norm(r.get('Talk title'))
        sess_ids = match_sessions(
            name, talk_title, auth_map, chair_map, title_map)
        entry['sessions'] = sorted(set(entry['sessions']).union(sess_ids))
        merged[key] = entry
    # Normalize role lists
    for m in merged.values():
        if not m['roles']:
            m['roles'] = ['N/A']
    return merged


def yaml_dump(data, path):
    if yaml is not None:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        return
    # Fallback: basic YAML writer for our fixed schema

    def esc(s):
        if s is None:
            return 'N/A'
        s = str(s)
        if s == '':
            return 'N/A'
        # quote if has special chars
        if re.search(r'[:#\-\[\]\{\}\n]', s):
            return '"' + s.replace('"', '\"') + '"'
        return s
    with open(path, 'w', encoding='utf-8') as f:
        f.write('people:\n')
        for person in data.get('people', []):
            f.write('  - id: ' + esc(person.get('id')) + '\n')
            f.write('    name: ' + esc(person.get('name')) + '\n')
            f.write('    job_title: ' + esc(person.get('job_title')) + '\n')
            f.write('    email: ' + esc(person.get('email')) + '\n')
            f.write('    affiliation: ' + esc(person.get('affiliation')) + '\n')
            f.write('    country: ' + esc(person.get('country')) + '\n')
            roles = person.get('roles') or []
            if not roles:
                roles = ['N/A']
            f.write('    roles: [' + ', '.join(esc(r) for r in roles) + ']\n')
            f.write('    picture: ' + esc(person.get('picture') or 'N/A') + '\n')
            bio = person.get('bio') or 'N/A'
            f.write('    bio: ' + esc(bio) + '\n')
            sess = person.get('sessions') or []
            f.write('    sessions: [' + ', '.join(esc(s)
                    for s in sess) + ']\n\n')


def main():
    sessions, auth_map, chair_map, title_map = load_sessions()
    people_rows = read_people_csv()
    merged = merge_people(people_rows, auth_map, chair_map, title_map)
    # Convert to list of dicts with the desired order
    people_list = []
    for key in sorted(merged.keys()):
        people_list.append(merged[key])
    out = {
        'people': people_list
    }
    yaml_dump(out, OUT_YML)
    print(f"Wrote {OUT_YML} with {len(people_list)} people")


if __name__ == '__main__':
    main()
