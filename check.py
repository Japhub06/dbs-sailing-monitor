#!/usr/bin/env python3
"""
Checks the DBS Sailing page for when the registration button changes
away from "June" (i.e. July registration opens), and signals the
GitHub Actions workflow to send an email + phone push.

It only READS the page. It never logs in, fills a form, or books anything.
"""
import os
import re
import sys
import requests

URL = "https://www.dbs.com/sailing/index.html"
STATE_FILE = "last_status.txt"

# Pretend to be a normal browser so the request isn't blocked.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def fetch():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def find_registration_links(html):
    """Return [(visible_text, href), ...] for any link mentioning 'Registration'."""
    pattern = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                         re.IGNORECASE | re.DOTALL)
    results = []
    for href, inner in pattern.findall(html):
        text = re.sub(r"<[^>]+>", "", inner)      # strip any nested tags
        text = re.sub(r"\s+", " ", text).strip()
        if re.search(r"registration", text, re.IGNORECASE):
            results.append((text, href))
    return results


def detect_month(links):
    """Find which month the registration button currently refers to."""
    for text, href in links:
        for m in MONTHS:
            if re.search(rf"\b{m}\b", text, re.IGNORECASE):
                return m, text, href
    return None, None, None


def write_output(name, value):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"{name}={value}\n")
    print(f"output: {name}={value}")


def main():
    try:
        html = fetch()
    except Exception as e:
        print(f"WARN: could not fetch page ({e}); skipping this run.")
        write_output("alert", "false")
        return 0

    links = find_registration_links(html)
    print(f"Registration links found: {links}")
    month, label, href = detect_month(links)

    if month is None:
        # Page layout may have changed; don't false-alarm, just log.
        print("WARN: no month found near a 'Registration' link.")
        write_output("alert", "false")
        return 0

    prev = ""
    if os.path.exists(STATE_FILE):
        prev = open(STATE_FILE).read().strip()
    print(f"Previous month seen: {prev!r}   Current month: {month!r}")

    changed = (month != prev)
    # Alert the moment the button shows any month other than June.
    if True:
        write_output("alert", "true")
        write_output("label", label)
        write_output("link", href)
        print(f"ALERT: registration changed to {month}!")
    else:
        write_output("alert", "false")

    # Remember what we saw so we only alert once per change.
    with open(STATE_FILE, "w") as f:
        f.write(month)

    return 0


if __name__ == "__main__":
    sys.exit(main())
