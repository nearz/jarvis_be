import re
import requests
from re import Match
from urllib.parse import urlparse

import bleach


def sanitize_markdown(content: str) -> str:
    if not content:
        return ""

    try:
        content = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", content)
        content = bleach.clean(
            content,
            tags=[],
            attributes={},
            strip=True,
            strip_comments=True,
        )

        def validate_md_link(match: Match) -> str:
            text, url = match.groups()
            if url.startswith("https://"):
                return f"[{text}]({url})"
            else:
                return text

        content = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", validate_md_link, content)
        return content.strip()

    except Exception as e:
        return "Error sanitizing markdown"


def validate_url(url: str) -> tuple[bool, str]:
    if not url or not isinstance(url, str):
        return False, "No URL provided"

    if len(url) > 2048:
        return False, "URL exceeds max length (2048 characters)"

    try:
        parsed = urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format (must include protocol and domain)"

        if parsed.scheme != "https":
            return False, f"Unsupported protocol '{parsed.scheme}' (only https allowed)"

        return True, ""

    except Exception as e:
        return False, "Malformed URL"


async def is_url_accesible(url: str) -> tuple[bool, str]:
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)

        if resp.status_code not in (200, 203, 204):
            return (
                False,
                f"Head response not either 200, 203, 204. status code: {resp.status_code}",
            )

        ctype = resp.headers.get("content-type", "")
        if not ctype.startswith("text/html"):
            return False, f"Content type not acceptable. content-type: {ctype}"

        if resp.history:
            orig = urlparse(url).netloc
            for hop in resp.history:
                loc = hop.headers.get("Location", "")
                if loc and urlparse(loc).netloc not in ("", orig):
                    return False, "Domain changed between redirects"

        return True, ""
    except requests.RequestException:
        return False, "Head request failed."


# TODO: What else can I add to this pipeline for safe URL checks
# TODO: Look at Google Safe Search
async def should_extract(url: str) -> tuple[bool, str]:
    if not (result := validate_url(url))[0]:
        ok, err_msg = result
        return ok, err_msg

    if not (result := await is_url_accesible(url))[0]:
        ok, err_msg = result
        return ok, err_msg

    return True, ""
