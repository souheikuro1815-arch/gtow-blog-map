"""前回取得した記事一覧を保存し、次回との差分（新着・更新）を出す。"""

import datetime
import json
import os
import re

SCHEMA = 1


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def parse_dt(value):
    """ISO文字列を datetime に。パースできなければ None。"""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
    if m:
        return datetime.datetime(
            int(m.group(1)), int(m.group(2)), int(m.group(3)),
            tzinfo=datetime.timezone.utc,
        )
    return None


def load(path):
    if not os.path.exists(path):
        return {"schema": SCHEMA, "runs": 0, "first_run_at": None,
                "last_run_at": None, "posts": {}}
    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("posts", {})
    state.setdefault("runs", 0)
    return state


def save(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def apply_fetch(state, posts, jp_index=None):
    """取得した記事を state に反映し、差分サマリを返す。

    初回実行（runs == 0）は「全部が新着」になってしまうので基準日を
    公開日にそろえ、新着としては扱わない。

    jp_index を渡すと、日本語版がある記事にその情報を紐づける。
    """
    import jp_fetcher

    stamp = now_iso()
    is_baseline = state.get("runs", 0) == 0
    known = state.get("posts", {})

    added, updated, translated = [], [], []
    fresh = {}

    for post in posts:
        pid = post["id"]
        prev = known.get(pid)
        record = dict(post)

        if jp_index is not None:
            jp = jp_fetcher.match(post["url"], jp_index)
            record["jp"] = {"title": jp["title"], "url": jp["url"]} if jp else None
            # 日本語版の記録がまだ無い回（初回・機能追加直後）は基準づくりなので
            # 「新しく和訳が出た」とは数えない
            jp_known = prev is not None and "jp" in prev
            if jp and jp_known and not prev.get("jp") and not is_baseline:
                translated.append(record)
        elif prev is not None:
            record["jp"] = prev.get("jp")
        if prev is None:
            record["first_seen"] = post["published_at"] if is_baseline else stamp
            record["added_in_run"] = 0 if is_baseline else state["runs"] + 1
            record["last_changed"] = None
            if not is_baseline:
                added.append(record)
        else:
            record["first_seen"] = prev.get("first_seen") or post["published_at"]
            record["added_in_run"] = prev.get("added_in_run", 0)
            record["last_changed"] = prev.get("last_changed")
            if prev.get("updated_at") and post["updated_at"] != prev["updated_at"]:
                record["last_changed"] = stamp
                updated.append(record)
        fresh[pid] = record

    removed = [known[pid] for pid in known if pid not in fresh]

    state["schema"] = SCHEMA
    state["runs"] = state.get("runs", 0) + 1
    state["first_run_at"] = state.get("first_run_at") or stamp
    state["last_run_at"] = stamp
    state["posts"] = fresh

    return {
        "baseline": is_baseline,
        "run": state["runs"],
        "at": stamp,
        "total": len(fresh),
        "added": added,
        "updated": updated,
        "removed": removed,
        "translated": translated,
        "jp_total": sum(1 for r in fresh.values() if r.get("jp")),
    }


def append_history(path, diff):
    """実行のたびに1行ずつ記録を残す（あとから「いつ何が増えたか」を追える）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "at": diff["at"],
        "run": diff["run"],
        "baseline": diff["baseline"],
        "total": diff["total"],
        "added": [{"title": p["title"], "url": p["url"]} for p in diff["added"]],
        "updated": [{"title": p["title"], "url": p["url"]} for p in diff["updated"]],
        "removed": [{"title": p["title"], "url": p["url"]} for p in diff["removed"]],
        "translated": [{"title": p["title"], "jp": p["jp"]["title"]}
                       for p in diff.get("translated", [])],
        "jp_total": diff.get("jp_total", 0),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
