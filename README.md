# Instagram Follow List Comparator

Collect Instagram followers and following data from copied browser cURL requests, then compare the two lists.

This repository contains three Python scripts:

- `getfollowers.py` collects followers into a JSON file.
- `getfollowing.py` collects following accounts into a JSON file.
- `compare_json.py` compares both JSON files and writes a summary of the differences.

## Requirements

- Python 3.9 or newer.
- Windows with `curl.exe` available. The collector scripts shell out to `curl.exe`.
- An Instagram session that can generate a browser cURL request.

Install dependencies with:

```bash
pip install -r requirements.txt
```

There are no third-party packages to install, but keeping the file makes the setup explicit and GitHub-friendly.

## How To Get The cURL

The scripts do not log in to Instagram themselves. They reuse a request you copy from your browser while you are already signed in.

In Chrome or Edge:

1. Open Instagram and sign in.
2. Open Developer Tools with `F12` or `Ctrl+Shift+I`.
3. Go to the `Network` tab and make sure recording is on.
4. Open the page that shows the followers or following list for the account you want to export.
5. Wait for the request list to populate, then click the request that returns the follower/following data.
6. Right-click that request and choose `Copy` then `Copy as cURL(bash)`.
7. Paste the full command into `RAW_CURL` in the matching script. Use `getfollowers.py` for followers and `getfollowing.py` for following.

What to paste matters:

- include the full URL,
- include the request headers,
- include the cookie/session data,
- paste the command exactly as copied, even if it spans multiple lines.

The collector scripts already clean Windows carets and line breaks before sending the request to `curl.exe`.

## Setup

1. Paste the followers request into `getfollowers.py`.
2. Paste the following request into `getfollowing.py`.
3. Run each collector once to generate the JSON files.
4. If needed, adjust the default input filenames in `compare_json.py` to match the files created by the collector scripts.

## Usage

Run the collectors first:

```bash
python getfollowers.py
python getfollowing.py
```

Each collector script:

- reads the pasted cURL command,
- pages through the API response,
- saves unique usernames to a JSON file,
- sorts the final output by username.

The collector output file name is derived from the request URL when possible, so the JSON file usually matches the Instagram endpoint or account identifier.

Then compare the two exported files:

```bash
python compare_json.py followers_123456789.json following_123456789.json
```

If your exported filenames are different, update the constants at the top of [compare_json.py](compare_json.py) or pass the file names directly on the command line:

- `DEFAULT_FILE1` for the followers JSON file
- `DEFAULT_FILE2` for the following JSON file
- `DEFAULT_OUT` for the summary output file

Optional flags:

- `--key` changes the field used for comparison, default `username`.
- `--out` writes the comparison summary to a file, default `comparison_summary.json`.

Command-line file paths override the defaults defined in [compare_json.py](compare_json.py).

## Output

The comparison summary includes:

- usernames only in followers,
- usernames only in following,
- usernames present in both files,
- counts for each list.

The summary is printed to the console and written to `comparison_summary.json` unless you change `DEFAULT_OUT` or pass `--out`.

## Notes

- The scripts are designed for personal use with your own session data.
- If Instagram changes the response shape or pagination parameters, you may need to update the pasted cURL command or the parsing logic.
- The generated JSON files are deduplicated by `username`.

## Suggested Project Name

If you want a cleaner GitHub name, I would use `instagram-follow-compare`.