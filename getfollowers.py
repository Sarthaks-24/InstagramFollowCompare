import json
import os
import subprocess
import time
import urllib.parse
import re


# Edit only this: paste the entire curl command you copied (including headers, cookies, url)
# Example: paste the raw curl (single- or multi-line). The script will clean it and execute it.
RAW_CURL = r'''
{cURL(bash)}
'''

# Poll interval
POLL_INTERVAL_SECONDS = 2
VERBOSE = True

# Output filename: derive from the first URL found in the curl string, fallback to followers.json
def _derive_output_name(raw_curl: str):
    try:
        cleaned = raw_curl.replace('\n', ' ').replace('^', '')
        # find first http(s) URL
        import re

        m = re.search(r'https?://[^\s"\']+', cleaned)
        if not m:
            return 'followers.json'
        url = m.group(0)
        parsed = urllib.parse.urlparse(url)
        parts = parsed.path.split('/')
        if 'friendships' in parts:
            idx = parts.index('friendships')
            if idx + 1 < len(parts):
                return f'followers_{parts[idx+1]}.json'
        # fallback to hostname
        return f'followers_{parsed.netloc}.json'
    except Exception:
        return 'followers.json'


OUTPUT_FILE = _derive_output_name(RAW_CURL)


def load_existing_records(path):
    if not os.path.exists(path):
        return [], set()

    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError:
            return [], set()

    if not isinstance(data, list):
        return [], set()

    records = []
    seen_usernames = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        username = item.get("username")
        name = item.get("name", "")
        if not username or username in seen_usernames:
            continue
        records.append({"username": username, "name": name})
        seen_usernames.add(username)

    return records, seen_usernames


def save_records(path, records):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def sort_records_by_username(records):
    """Sort the records list in-place by the `username` field (case-insensitive)."""
    try:
        records.sort(key=lambda r: (r.get('username') or '').lower())
    except Exception:
        pass


def run_curl(max_id=None):
    # Clean the raw curl command (remove caret line-continuations and newlines)
    cleaned = RAW_CURL.replace('\n', ' ').replace('^', ' ').strip()

    # Extract URL
    m = re.search(r'https?://[^\s"\']+', cleaned)
    if not m:
        raise RuntimeError('Could not find URL in RAW_CURL')
    url = m.group(0)

    # Extract headers (-H "...") and cookie (-b "...")
    headers = []
    for h in re.finditer(r'-H\s+(?:"([^"]+)"|\'([^\']+)\')', cleaned):
        val = h.group(1) or h.group(2)
        if val:
            headers.append(val)

    # Extract cookie argument if present
    cookie = None
    bc = re.search(r'-(?:b|\-\-cookie)\s+(?:"([^"]+)"|\'([^\']+)\')', cleaned)
    if bc:
        cookie = bc.group(1) or bc.group(2)

    # Build curl args: ensure curl.exe, URL, then headers and cookie
    args = ['curl.exe', url]
    for h in headers:
        args.extend(['-H', h])
    if cookie:
        args.extend(['-b', cookie])

    # Inject max_id into the URL token
    if max_id:
        parsed = urllib.parse.urlparse(args[1])
        q = dict(urllib.parse.parse_qsl(parsed.query))
        q['max_id'] = max_id
        new_query = urllib.parse.urlencode(q)
        args[1] = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    if VERBOSE:
        print('Request URL:', args[1])
        print('Curl args count:', len(args))

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
    records, seen_usernames = load_existing_records(OUTPUT_FILE)
    max_id = None

    while True:
        payload = run_curl(max_id)

        new_records = []
        for user in payload.get("users", []):
            username = user.get("username")
            if not username or username in seen_usernames:
                continue
            new_records.append({
                "username": username,
                "name": user.get("full_name", ""),
            })
            seen_usernames.add(username)

        if new_records:
            records.extend(new_records)
            save_records(OUTPUT_FILE, records)
            print(f"Saved {len(new_records)} new followers to {OUTPUT_FILE}")
        else:
            print("No new followers found")

        max_id = payload.get("next_max_id")
        if not payload.get("has_more") or not max_id:
            break

        time.sleep(POLL_INTERVAL_SECONDS)

    # Final pass: sort all collected records by username and save final file
    sort_records_by_username(records)
    save_records(OUTPUT_FILE, records)


if __name__ == "__main__":
    main()
