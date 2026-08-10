#!/usr/bin/env python3
"""GTOウィザードのブログ記事を取得して、カテゴリ別の一覧ページを更新する。

使い方:
    python3 update.py            取得して一覧ページを作り直す
    python3 update.py --open     作り直したあとブラウザで開く
    python3 update.py --notify   新着があればMacの通知で知らせる（週次の自動実行用）
    python3 update.py --dry-run  取得だけして保存しない（動作確認用）
"""

import datetime
import os
import subprocess
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetcher
import jp_fetcher
import renderer
import store

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "data", "posts.json")
HISTORY_PATH = os.path.join(HERE, "data", "history.jsonl")
OUTPUT_PATH = os.path.join(HERE, "記事一覧.html")
# GitHub Pages に公開する用。中身は 記事一覧.html と同じ
SITE_PATH = os.path.join(HERE, "site", "index.html")


def notify(title, message):
    """Macの通知センターに知らせる。失敗しても本体の処理は止めない。"""
    script = 'display notification {} with title {}'.format(
        _osa_quote(message), _osa_quote(title))
    try:
        subprocess.run(["/usr/bin/osascript", "-e", script], timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _osa_quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main(argv):
    dry_run = "--dry-run" in argv
    do_open = "--open" in argv
    do_notify = "--notify" in argv

    print("=== {} ===".format(
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("ブログから記事を取得中 ...")
    try:
        raw = fetcher.fetch_posts()
    except Exception as e:
        print("取得に失敗しました: {}".format(e))
        print("ネット接続を確認して、少し待ってからもう一度実行してください。")
        return 1
    posts = [fetcher.normalize(p) for p in raw]
    print("  英語版 {} 件を取得しました".format(len(posts)))

    jp_posts = jp_fetcher.fetch_posts()
    if jp_posts:
        print("  日本語版 {} 件を取得しました".format(len(jp_posts)))
        jp_index = jp_fetcher.build_index(jp_posts)
    else:
        # 日本語サイトが落ちていても英語版の更新は止めない
        print("  日本語版は取得できませんでした（前回の対応づけを維持します）")
        jp_index = None

    state = store.load(STATE_PATH)
    diff = store.apply_fetch(state, posts, jp_index)

    if dry_run:
        print("--dry-run のため保存しませんでした。")
        return 0

    store.save(STATE_PATH, state)
    store.append_history(HISTORY_PATH, diff)

    page = renderer.render(state)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)
    os.makedirs(os.path.dirname(SITE_PATH), exist_ok=True)
    with open(SITE_PATH, "w", encoding="utf-8") as f:
        f.write(page)

    report(diff)
    print("\n一覧ページを更新しました: {}".format(OUTPUT_PATH))
    if do_notify and diff["added"]:
        first = diff["added"][0]["title"]
        rest = len(diff["added"]) - 1
        body = first if not rest else "{} ほか{}件".format(first, rest)
        notify("GTO Wizard 新着 {}件".format(len(diff["added"])), body)
    if do_open:
        webbrowser.open("file://" + OUTPUT_PATH)
    return 0


def report(diff):
    if diff["baseline"]:
        print("\n[初回実行] 現在の {} 件を基準として記録しました（うち日本語版あり {} 件）。".format(
            diff["total"], diff["jp_total"]))
        print("次回以降、ここから増えた記事が「新着」として出ます。")
        return

    print("\n[{}回目の実行] 記事は全 {} 件（うち日本語版あり {} 件）".format(
        diff["run"], diff["total"], diff["jp_total"]))
    if diff["added"]:
        print("\n■ 新しく出た記事 {} 件".format(len(diff["added"])))
        for p in diff["added"]:
            print("  ・{}".format(p["title"]))
            print("    {}".format(p["url"]))
    else:
        print("  新着はありません。")
    if diff["updated"]:
        print("\n■ 内容が更新された記事 {} 件".format(len(diff["updated"])))
        for p in diff["updated"]:
            print("  ・{}".format(p["title"]))
    if diff["translated"]:
        print("\n■ 新しく日本語版が出た記事 {} 件".format(len(diff["translated"])))
        for p in diff["translated"]:
            print("  ・{}".format(p["jp"]["title"]))
            print("    {}".format(p["jp"]["url"]))
    if diff["removed"]:
        print("\n■ 公開が取り下げられた記事 {} 件".format(len(diff["removed"])))
        for p in diff["removed"]:
            print("  ・{}".format(p["title"]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
