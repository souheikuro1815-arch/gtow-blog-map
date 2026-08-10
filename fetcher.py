"""GTOウィザードのブログ（Ghost製）から公開記事を全件取得する。

Ghost の Content API を使う。APIキーはブログのトップページに公開状態で
埋め込まれているもの（購読フォーム用の公開キー）で、認証情報ではない。
キーが変わってもトップページから拾い直すので、基本メンテ不要。
"""

import json
import re
import urllib.error
import urllib.request

BLOG_URL = "https://blog.gtowizard.com/"
API_BASE = "https://admin.blog.gtowizard.com/ghost/api/content"

# 2026-08 時点でブログに埋め込まれている公開キー。失敗したら自動で拾い直す。
FALLBACK_KEY = "cb7e32915ecd73eb2ca84c4b92"

FIELDS = ",".join([
    "id", "title", "slug", "url", "excerpt",
    "published_at", "updated_at", "reading_time", "feature_image",
])

USER_AGENT = "gtow-blog-organizer/1.0"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8")


def discover_key():
    """ブログのトップページから Content API の公開キーを取り出す。"""
    html = _get(BLOG_URL)
    m = re.search(r'data-key="([0-9a-f]{20,})"', html)
    if not m:
        raise RuntimeError("ブログページからAPIキーを見つけられませんでした")
    return m.group(1)


def fetch_posts(key=None):
    """公開済み記事を全件取得して辞書のリストで返す（新しい順）。"""
    key = key or FALLBACK_KEY
    try:
        posts = _fetch_all(key)
    except urllib.error.HTTPError as e:
        if e.code not in (401, 403):
            raise
        # キーが更新されていた場合はページから拾い直して再試行
        key = discover_key()
        posts = _fetch_all(key)
    return posts


def _fetch_all(key):
    posts = []
    page = 1
    while True:
        url = (
            "{base}/posts/?key={key}&limit=100&page={page}"
            "&order=published_at%20desc&fields={fields}&include=tags"
        ).format(base=API_BASE, key=key, page=page, fields=FIELDS)
        data = json.loads(_get(url))
        posts.extend(data.get("posts", []))
        pagination = data.get("meta", {}).get("pagination", {})
        nxt = pagination.get("next")
        if not nxt:
            break
        page = nxt
    return posts


def normalize(post):
    """必要な項目だけに絞り、内部タグ（#で始まる管理用タグ）を落とす。"""
    tags = []
    for t in post.get("tags") or []:
        if t.get("visibility") != "public":
            continue
        tags.append({"slug": t.get("slug"), "name": t.get("name")})
    return {
        "id": post.get("id"),
        "title": post.get("title") or "",
        "url": post.get("url") or "",
        "excerpt": (post.get("excerpt") or "").strip().replace("\n", " ")[:300],
        "published_at": post.get("published_at") or "",
        "updated_at": post.get("updated_at") or "",
        "reading_time": post.get("reading_time") or 0,
        "tags": tags,
    }
