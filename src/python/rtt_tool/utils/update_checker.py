import re
import json
import urllib.request
import urllib.error
from typing import Optional, Tuple

CSDN_URL = "https://download.csdn.net/download/cl234583745/92870951"
GITHUB_API = "https://api.github.com/repos/cl234583745/RTT-Assistant/releases/latest"
GITEE_API = "https://gitee.com/api/v5/repos/292812832/RTT-Assistant/releases/latest"

RELEASE_PAGE_URLS = {
    "csdn": CSDN_URL,
    "github": "https://github.com/cl234583745/RTT-Assistant/releases",
    "gitee": "https://gitee.com/292812832/RTT-Assistant/releases",
}


def parse_version(v: str) -> Optional[Tuple[int, ...]]:
    m = re.search(r"(\d+(?:\.\d+)+)", v)
    if m:
        return tuple(int(x) for x in m.group(1).split("."))
    return None


def _fetch(url: str, timeout: int = 15) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def check_csdn() -> Optional[dict]:
    html = _fetch(CSDN_URL)
    if not html:
        return None
    m = re.search(r"RTT-Assistant[.\s]*v?(\d+\.\d+\.\d+)", html, re.IGNORECASE)
    if m:
        ver_str = m.group(1)
        return {"source": "CSDN", "version": ver_str, "url": CSDN_URL,
                "files": [{"name": f"RTT-Assistant.v{ver_str}", "url": CSDN_URL}]}
    return None


def check_github() -> Optional[dict]:
    data = _fetch(GITHUB_API)
    if not data:
        return None
    try:
        release = json.loads(data)
    except json.JSONDecodeError:
        return None
    tag = release.get("tag_name", "")
    ver_str = tag.lstrip("v")
    assets = []
    for a in release.get("assets", []):
        name = a.get("name", "")
        if re.search(r"RTT-Assistant[.\s]*v?\d", name):
            assets.append({"name": name, "url": a["browser_download_url"]})
    return {"source": "GitHub", "version": ver_str,
            "url": RELEASE_PAGE_URLS["github"], "files": assets} if assets else None


def check_gitee() -> Optional[dict]:
    data = _fetch(GITEE_API)
    if not data:
        return None
    try:
        release = json.loads(data)
    except json.JSONDecodeError:
        return None
    tag = release.get("tag_name", "")
    ver_str = tag.lstrip("v")
    assets = []
    for a in release.get("assets", []):
        name = a.get("name", "")
        if re.search(r"RTT-Assistant[.\s]*v?\d", name):
            assets.append({"name": name, "url": a["browser_download_url"]})
    return {"source": "Gitee", "version": ver_str,
            "url": RELEASE_PAGE_URLS["gitee"], "files": assets} if assets else None


def check_all_sources() -> list:
    results = []
    for fn in (check_csdn, check_github, check_gitee):
        try:
            r = fn()
            if r:
                results.append(r)
        except Exception:
            pass
    return results
