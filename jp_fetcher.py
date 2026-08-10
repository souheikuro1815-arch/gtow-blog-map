"""GTOウィザードの日本語版ブログ（japan.gtowizard.com）から記事を取得する。

日本語版はWordPress製で、英語版とは別サイト・別URL。ただし記事のURL末尾
（スラッグ）が英語版と共通なので、それを手がかりに対応付けできる。
2026年8月時点で、英語版364件に対し日本語版は158件（約4割）。
"""

import html
import json
import re
import urllib.request

API = "https://japan.gtowizard.com/wp-json/wp/v2/posts"
USER_AGENT = "gtow-blog-organizer/1.0"


def fetch_posts():
    """日本語版の記事を全件取得する。取得できなければ空リストを返す。"""
    posts = []
    page = 1
    while page <= 20:  # 暴走よけの上限
        url = "{}?per_page=100&page={}&_fields=slug,title,link,date".format(API, page)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                batch = json.loads(res.read().decode("utf-8"))
        except Exception:
            break
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    out = []
    for p in posts:
        title = html.unescape(re.sub(r"<[^>]+>", "", p.get("title", {}).get("rendered", "")))
        out.append({
            "slug": p.get("slug", ""),
            "title": title.strip(),
            "url": p.get("link", ""),
            "date": (p.get("date") or "")[:10],
        })
    return out


def normalize(slug):
    """英語版と日本語版でスラッグの表記ゆれを吸収する。"""
    return re.sub(r"-+", "-", (slug or "").lower().replace("_", "-")).strip("-")


def build_index(jp_posts):
    """スラッグをキーにした対応表を作る。"""
    return {normalize(p["slug"]): p for p in jp_posts if p.get("slug")}


def match(en_url, index):
    """英語記事のURLから、対応する日本語記事を探す。

    スラッグ完全一致が基本。見つからないときだけ、片方が途中で切れている
    ケース（例: ...-comparison-too / ...-comparison-tool）を前方一致で拾う。
    """
    slug = normalize(en_url.rstrip("/").split("/")[-1])
    if not slug:
        return None
    if slug in index:
        return index[slug]
    for jp_slug, jp in index.items():
        if len(jp_slug) < 20 or len(slug) < 20:
            continue
        if jp_slug.startswith(slug) or slug.startswith(jp_slug):
            return jp
    return None
