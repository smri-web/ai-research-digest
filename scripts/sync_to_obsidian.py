"""Download any digest notes missing from an Obsidian vault.

Runs on the user's machine (scheduled by launchd), not in the cloud. Lists the markdown digests
in the public GitHub repo and downloads the ones not yet in the vault folder. Uses only the
Python standard library so it works with the system python3, no installs.

Usage: python3 sync_to_obsidian.py "/path/to/Vault/AI Research Digest"
"""
import json
import os
import subprocess
import sys

REPO = "smri-web/ai-research-digest"
LIST_URL = f"https://api.github.com/repos/{REPO}/contents/digests"


def fetch(url: str) -> bytes:
    # Fetch with the system curl: it is present on every Mac and uses the OS certificate store,
    # avoiding the SSL verification failures python.org Python installs hit out of the box.
    # --retry covers transient network drops since this runs unattended.
    return subprocess.run(
        ["curl", "-fsSL", "-A", "ai-digest-obsidian-sync", "--max-time", "60",
         "--retry", "3", "--retry-delay", "2", "--retry-all-errors", url],
        check=True, capture_output=True,
    ).stdout


def main(vault_dir: str) -> None:
    os.makedirs(vault_dir, exist_ok=True)
    entries = json.loads(fetch(LIST_URL))
    new = 0
    for e in entries:
        name = e.get("name", "")
        if not name.endswith(".md"):
            continue
        dest = os.path.join(vault_dir, name)
        if os.path.exists(dest):
            continue
        content = fetch(e["download_url"])
        # Write atomically so Obsidian/iCloud never sees a half-written note.
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(content)
        os.rename(tmp, dest)
        print(f"added {name}")
        new += 1
    print(f"done: {new} new digest(s)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: sync_to_obsidian.py <vault-folder-for-digests>")
    main(sys.argv[1])
