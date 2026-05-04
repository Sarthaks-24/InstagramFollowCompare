import json
import os
import subprocess
import time
import urllib.parse
import re


# Paste the entire curl command you copied (including headers, cookies, url)
# For following pagination the script will add an offset parameter (0, count, 2*count...)
RAW_CURL = r'''
{cURL(bash)}
'''

# Poll interval (seconds)
POLL_INTERVAL_SECONDS = 2
VERBOSE = True


def _derive_output_name(raw_curl: str):
    try:
        cleaned = raw_curl.replace('\n', ' ').replace('^', '')
        m = re.search(r'https?://[^\s"\']+', cleaned)
        if not m:
            return 'following.json'
        url = m.group(0)
        parsed = urllib.parse.urlparse(url)
        parts = parsed.path.split('/')
        if 'friendships' in parts:
            idx = parts.index('friendships')
            if idx + 1 < len(parts):
                return f'following_{parts[idx+1]}.json'
        return f'following_{parsed.netloc}.json'
    except Exception:
        return 'following.json'


OUTPUT_FILE = _derive_output_name(RAW_CURL)


def load_existing_records(path):
    if not os.path.exists(path):
        return [], set()
    with open(path, 'r', encoding='utf-8') as fh:
        try:
            data = json.load(fh)
        except Exception:
            return [], set()
    if not isinstance(data, list):
        return [], set()
    records = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        u = item.get('username')
        if not u or u in seen:
            continue
        records.append({'username': u, 'name': item.get('name','')})
        seen.add(u)
    return records, seen


def save_records(path, records):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)


def sort_records_by_username(records):
    """Sort the records list in-place by the `username` field (case-insensitive)."""
    try:
        records.sort(key=lambda r: (r.get('username') or '').lower())
    except Exception:
        pass


def run_curl_with_offset(offset=None):
    cleaned = RAW_CURL.replace('\n', ' ').replace('^', ' ').strip()
    m = re.search(r'https?://[^\s"\']+', cleaned)
    if not m:
        raise RuntimeError('Could not find URL in RAW_CURL')
    url = m.group(0)

    headers = []
    for h in re.finditer(r'-H\s+(?:"([^"]+)"|\'([^\']+)\')', cleaned):
        val = h.group(1) or h.group(2)
        if val:
            headers.append(val)

    cookie = None
    bc = re.search(r'-(?:b|--cookie)\s+(?:"([^"]+)"|\'([^\']+)\')', cleaned)
    if bc:
        cookie = bc.group(1) or bc.group(2)

    args = ['curl.exe', url]
    for h in headers:
        args.extend(['-H', h])
    if cookie:
        args.extend(['-b', cookie])

    # If offset provided, append or replace {offset} placeholder
    if offset is not None:
        if '{offset}' in args[1]:
            args[1] = args[1].replace('{offset}', str(offset))
        else:
            parsed = urllib.parse.urlparse(args[1])
            q = dict(urllib.parse.parse_qsl(parsed.query))
            # we'll use max_id param as the offset per user request
            q['max_id'] = str(offset)
            new_query = urllib.parse.urlencode(q)
            args[1] = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    if VERBOSE:
        print('Request URL:', args[1])

    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if VERBOSE:
            print('curl stderr:', stderr)
            print('curl stdout (truncated):', result.stdout[:500])
        raise RuntimeError(stderr or f'curl failed with exit code {result.returncode}')

    if VERBOSE:
        print('curl stdout (truncated 500):')
        print(result.stdout[:500])

    return json.loads(result.stdout)


def main():
    records, seen = load_existing_records(OUTPUT_FILE)

    # detect count per page from URL
    m = re.search(r'https?://[^\s"\']+', RAW_CURL)
    if not m:
        print('RAW_CURL missing URL')
        return
    parsed = urllib.parse.urlparse(m.group(0))
    q = dict(urllib.parse.parse_qsl(parsed.query))
    try:
        count = int(q.get('count', '12'))
    except Exception:
        count = 12

    page = 0
    while True:
        offset = page * count
        # for first page Instagram expects no offset — pass None
        payload = run_curl_with_offset(None if page == 0 else offset)

        users = payload.get('users', [])
        if VERBOSE:
            print('users returned:', len(users))

        new = []
        for u in users:
            username = u.get('username')
            if not username or username in seen:
                continue
            new.append({'username': username, 'name': u.get('full_name','')})
            seen.add(username)

        if new:
            records.extend(new)
            save_records(OUTPUT_FILE, records)
            print(f'Saved {len(new)} new following to {OUTPUT_FILE}')
        else:
            print('No new following found on this page')

        # stop if server indicates no more or returned fewer than count
        if not payload.get('has_more') or len(users) < count:
            break

        page += 1
        time.sleep(POLL_INTERVAL_SECONDS)

    # Final pass: sort all collected records by username and save final file
    sort_records_by_username(records)
    save_records(OUTPUT_FILE, records)


if __name__ == '__main__':
    main()
