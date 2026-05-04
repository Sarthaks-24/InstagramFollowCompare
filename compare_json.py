import json
import argparse
from typing import List, Dict

# Default file paths - edit these to match the JSON files created by the collector scripts
DEFAULT_FILE1 = 'followers.json'
DEFAULT_FILE2 = 'following.json'
DEFAULT_OUT = 'comparison_summary.json'


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def _to_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # convert dict to single-item list for uniform handling
        return [data]
    return []


def _extract_keys(records: List[Dict], key: str):
    s = set()
    for r in records:
        if isinstance(r, dict):
            v = r.get(key)
            if v is not None:
                s.add(str(v))
        else:
            s.add(str(r))
    return s


def compare_json(file1: str, file2: str, key: str = 'username') -> Dict:
    a = load_json(file1)
    b = load_json(file2)
    la = _to_list(a)
    lb = _to_list(b)
    ka = _extract_keys(la, key)
    kb = _extract_keys(lb, key)

    only_a = sorted(ka - kb)
    only_b = sorted(kb - ka)
    both = sorted(ka & kb)

    # Build a more readable summary structure using 'followers' and 'following'
    return {
        'key': key,
        'followers': {
            'file': file1,
            'count': len(ka),
            'only': only_a,
        },
        'following': {
            'file': file2,
            'count': len(kb),
            'only': only_b,
        },
        'in_both': both,
    }


def main():
    p = argparse.ArgumentParser(description='Compare two JSON files (lists of objects) by a key')
    # positional args made optional — fall back to defaults defined in this file
    p.add_argument('file1', nargs='?', default=DEFAULT_FILE1, help='first JSON file (default from DEFAULT_FILE1)')
    p.add_argument('file2', nargs='?', default=DEFAULT_FILE2, help='second JSON file (default from DEFAULT_FILE2)')
    p.add_argument('--key', default='username', help='object key to compare (default: username)')
    p.add_argument('--out', default=DEFAULT_OUT, help='optional output JSON file for the summary')
    args = p.parse_args()

    if not args.file1 or not args.file2:
        p.error('file1 and file2 must be provided either as arguments or via DEFAULT_FILE1/DEFAULT_FILE2')

    summary = compare_json(args.file1, args.file2, args.key)

    print(f"Counts: {summary['followers']['count']} (followers) vs {summary['following']['count']} (following)")
    print(f"Only in {summary['followers']['file']}: {len(summary['followers']['only'])}")
    print(f"Only in {summary['following']['file']}: {len(summary['following']['only'])}")

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
        print(f"Wrote summary to {args.out}")
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
