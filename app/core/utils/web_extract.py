import re
import httpx
from re import Match
from urllib.parse import urlparse

import bleach

from ..logging import get_logger

logger = get_logger(__name__)


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
        logger.warning("Could not sanitize markdown content")
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
        logger.warning("Error validating URL | url: %s", url)
        return False, "Malformed URL"


async def is_url_accessible(url: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            try:
                resp = await client.head(url)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 405:
                    try:
                        resp = await client.get(url, headers={"Range": "bytes=0-1024"})
                    except:
                        logger.warning("HEAD and GET request failed | url: %s", url)
                        return False, "Both HEAD and GET requests failed"
                else:
                    logger.warning("HTTP error | url: %s", url)
                    return False, f"HTTP error: {e.response.status_code}"

            if resp.status_code not in (200, 203):
                return (
                    False,
                    f"Head response not either 200, 203. status code: {resp.status_code}",
                )

            ctype = resp.headers.get("content-type", "")
            allowed_types = ("text/html", "application/xhtml+xml")
            if not any(ctype.startswith(t) for t in allowed_types):
                logger.warning("Content type not allowed | url: %s", url)
                return False, f"Content type not acceptable. content-type: {ctype}"

            if resp.history:
                orig_netloc = urlparse(url).netloc

                for hop in resp.history:
                    hop_netloc = urlparse(str(hop.url)).netloc
                    if hop_netloc != orig_netloc:
                        logger.warning(
                            "Redirect to different domain not allowed | url: %s",
                            hop_netloc,
                        )
                        return False, "Domain changed between redirects"

            return True, ""

    except httpx.HTTPError as e:
        logger.warning("HTTP Error | url: %s", url)
        return False, "Head request failed."


# TODO: What else can I add to this pipeline for safe URL checks
# TODO: Look at Google Safe Search
async def should_extract(url: str) -> tuple[bool, str]:
    if not (result := validate_url(url))[0]:
        ok, err_msg = result
        return ok, err_msg

    if not (result := await is_url_accessible(url))[0]:
        ok, err_msg = result
        return ok, err_msg

    return True, ""
