"""記事データから、ブラウザで開く一覧ページ（HTML1枚）を作る。"""

import datetime
import json

import categories
import store

NEW_WINDOW_DAYS = 30  # 「新着」として扱う日数
NO_TAG = "__none__"  # カテゴリタグが付いていない記事の受け皿


EXCERPT_CHARS = 190


def _shorten(text):
    """抜粋を単語の途中で切らずに縮め、省略記号を付ける。"""
    text = (text or "").strip()
    if len(text) <= EXCERPT_CHARS:
        return text
    cut = text[:EXCERPT_CHARS]
    space = cut.rfind(" ")
    if space > EXCERPT_CHARS * 0.6:
        cut = cut[:space]
    return cut.rstrip(" ,.;:-–—") + "…"


def build_view_model(state):
    """保存データを、ページで使う形（記事一覧＋カテゴリ一覧）に整える。"""
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=NEW_WINDOW_DAYS)

    posts = []
    tag_meta = {}
    tag_counts = {}

    for record in state.get("posts", {}).values():
        tags = record.get("tags") or []
        if not tags:
            # カテゴリタグが付いていない記事も取りこぼさないよう受け皿に入れる
            tags = [{"slug": NO_TAG, "name": "未分類"}]
        for t in tags:
            slug = t["slug"]
            if slug not in tag_meta:
                gid, gname = categories.group_of(slug)
                tag_meta[slug] = {
                    "slug": slug,
                    "label": categories.label_of(slug, t["name"]),
                    "name_en": t["name"],
                    "group": gid,
                    "group_label": gname,
                }
            tag_counts[slug] = tag_counts.get(slug, 0) + 1

        first_seen = store.parse_dt(record.get("first_seen"))
        is_new = bool(
            record.get("added_in_run")
            and first_seen is not None
            and first_seen >= cutoff
        )
        changed = store.parse_dt(record.get("last_changed"))
        is_updated = bool(changed is not None and changed >= cutoff)

        published = store.parse_dt(record.get("published_at"))
        jp = record.get("jp") or None
        posts.append({
            "jp_title": jp["title"] if jp else "",
            "jp_url": jp["url"] if jp else "",
            "title": record.get("title", ""),
            "url": record.get("url", ""),
            "excerpt": _shorten(record.get("excerpt", "")),
            "date": published.strftime("%Y-%m-%d") if published else "",
            "ts": published.timestamp() if published else 0,
            "read": record.get("reading_time") or 0,
            "tags": [t["slug"] for t in tags],
            "primary": tags[0]["slug"] if tags else "",
            "new": is_new,
            "upd": is_updated and not is_new,
            "seen": (first_seen.strftime("%Y-%m-%d") if first_seen else ""),
        })

    posts.sort(key=lambda p: p["ts"], reverse=True)

    # カテゴリを大分類ごとにまとめる（記事が1本もないタグは出さない）
    groups = []
    used = set()
    for gid, gname in categories.group_order():
        items = [
            dict(tag_meta[s], count=tag_counts[s])
            for s in tag_meta
            if tag_meta[s]["group"] == gid and tag_counts.get(s)
        ]
        if not items:
            continue
        items.sort(key=lambda t: -t["count"])
        used.update(t["slug"] for t in items)
        groups.append({"id": gid, "label": gname, "tags": items})

    return {
        "posts": posts,
        "groups": groups,
        "total": len(posts),
        "new_count": sum(1 for p in posts if p["new"]),
        "upd_count": sum(1 for p in posts if p["upd"]),
        "jp_count": sum(1 for p in posts if p["jp_url"]),
        "runs": state.get("runs", 0),
        "last_run": (state.get("last_run_at") or "")[:16].replace("T", " ") + " UTC",
        "window": NEW_WINDOW_DAYS,
    }



def render(state):
    """パソコン用に、単体で開けるHTMLファイルを作る。"""
    return (
        "<!doctype html>\n<html lang=\"ja\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        + PAGE_TITLE + STYLE + "</head>\n<body>\n"
        + _body(state) + "\n</body>\n</html>\n"
    )


def render_artifact(state):
    """Webで公開する用（<head>などの外枠は公開side が付けるので中身だけ）。"""
    return PAGE_TITLE + STYLE + _body(state)


def _body(state):
    vm = build_view_model(state)
    payload = json.dumps(vm, ensure_ascii=False).replace("</", "<\\/")
    return MARKUP.replace("__DATA__", payload)


PAGE_TITLE = "<title>GTO Wizard ブログ記事マップ</title>\n"


STYLE = r"""<style>
/* 配色は Google Search Console に合わせている。
   明るいテーマ：白いカードを薄いグレー地に置き、青をアクセントにする */
:root{
  --bg:#f8f9fa; --panel:#ffffff; --ink:#202124; --muted:#5f6368;
  --line:#dadce0; --hover:#f1f3f4;
  --accent:#1a73e8; --accent-soft:#e8f0fe; --on-accent:#1967d2;
  --new:#188038; --new-soft:#e6f4ea; --upd:#1967d2; --upd-soft:#e8f0fe;
}
/* 端末が暗いテーマのとき（明るいテーマを明示指定した場合は除く） */
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#202124; --panel:#292a2d; --ink:#e8eaed; --muted:#9aa0a6;
    --line:#3c4043; --hover:#35363a;
    --accent:#8ab4f8; --accent-soft:#283b5b; --on-accent:#8ab4f8;
    --new:#81c995; --new-soft:#1e3a29; --upd:#8ab4f8; --upd-soft:#1f3a5f;
  }
}
/* 暗いテーマを明示指定したとき */
:root[data-theme="dark"]{
  --bg:#202124; --panel:#292a2d; --ink:#e8eaed; --muted:#9aa0a6;
  --line:#3c4043; --hover:#35363a;
  --accent:#8ab4f8; --accent-soft:#283b5b; --on-accent:#8ab4f8;
  --new:#81c995; --new-soft:#1e3a29; --upd:#8ab4f8; --upd-soft:#1f3a5f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  -webkit-text-size-adjust:100%;
  font:14px/1.6 "Google Sans",Roboto,-apple-system,BlinkMacSystemFont,
       "Hiragino Sans","Noto Sans JP",sans-serif;}
a{color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}

/* 上部バー */
.head{background:var(--panel);border-bottom:1px solid var(--line);padding:16px 24px}
.head h1{margin:0;font-size:22px;font-weight:400;letter-spacing:0}
.sub{color:var(--muted);font-size:12px;margin-top:4px}

.wrap{display:grid;grid-template-columns:256px 1fr;align-items:start}

/* 左のカテゴリ一覧。選択中はピル型に色が付く */
.side{background:var(--panel);border-right:1px solid var(--line);
  padding:12px 0 40px;position:sticky;top:0;max-height:100vh;overflow:auto}
.gtitle{font-size:11px;letter-spacing:.8px;color:var(--muted);text-transform:uppercase;
  padding:0 24px;margin:18px 0 4px}
.chip{display:flex;justify-content:space-between;align-items:center;gap:8px;
  width:calc(100% - 12px);min-height:36px;padding:6px 24px;border:0;
  border-radius:0 20px 20px 0;background:transparent;color:var(--ink);
  font:inherit;font-size:13px;text-align:left;cursor:pointer}
.chip:hover{background:var(--hover)}
.chip[aria-pressed="true"]{background:var(--accent-soft);color:var(--on-accent);
  font-weight:500}
.chip .n{color:var(--muted);font-variant-numeric:tabular-nums;font-size:12px}
.chip[aria-pressed="true"] .n{color:var(--on-accent)}

main{padding:20px 24px 60px;min-width:0}

/* 数値カード */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));
  gap:12px;margin:0 0 16px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;
  padding:14px 16px}
.stat b{display:block;font-size:26px;font-weight:400;line-height:1.2;
  font-variant-numeric:tabular-nums}
.stat span{display:block;color:var(--muted);font-size:12px;margin-top:2px}

/* 検索・並び替えの帯 */
.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;
  background:var(--panel);border:1px solid var(--line);border-radius:8px;
  padding:12px 16px;margin-bottom:16px}
input[type=search],select{height:36px;padding:0 12px;border:1px solid var(--line);
  border-radius:4px;background:var(--panel);color:var(--ink);font:inherit;
  font-size:14px;max-width:100%}
input[type=search]{flex:1;min-width:170px}
input[type=search]:focus,select:focus{outline:none;border-color:var(--accent);
  box-shadow:0 0 0 1px var(--accent)}
#catsel{display:none}
.count{color:var(--muted);font-size:13px;margin-left:auto;
  font-variant-numeric:tabular-nums;white-space:nowrap}

/* 大分類の見出しと、カテゴリごとのカード */
.glabel{font-size:11px;letter-spacing:.8px;color:var(--muted);text-transform:uppercase;
  margin:24px 0 8px;padding-left:4px}
.sec{background:var(--panel);border:1px solid var(--line);border-radius:8px;
  padding:4px 20px 12px;margin:0 0 12px}
.sec h2{font-size:14px;font-weight:500;margin:0;padding:12px 0;
  display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;
  border-bottom:1px solid var(--line)}
.sec h2 .n{font-size:12px;color:var(--muted);font-weight:400;
  font-variant-numeric:tabular-nums}
.more{border:0;background:transparent;color:var(--accent);font:inherit;font-size:12px;
  cursor:pointer;padding:0;margin-left:auto;text-align:left}
.more:hover{text-decoration:underline}

ul{list-style:none;margin:0;padding:0}
li.item{padding:12px 0;border-top:1px solid var(--line)}
li.item:first-child{border-top:0}
.t{font-size:14px;font-weight:500;color:var(--accent);text-decoration:none;
  line-height:1.45;text-wrap:balance}
.t:hover{text-decoration:underline}
.jp{display:block;margin-top:3px;font-size:13px;color:var(--muted);
  text-decoration:none;line-height:1.5}
.jp:hover{color:var(--accent);text-decoration:underline}
.meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;
  color:var(--muted);font-size:12px;margin-top:6px}
.tag{padding:2px 10px;border:1px solid var(--line);border-radius:16px;cursor:pointer}
.tag:hover{border-color:var(--accent);color:var(--accent)}
.badge{padding:2px 8px;border-radius:4px;font-weight:500;font-size:11px}
.badge.new{background:var(--new-soft);color:var(--new)}
.badge.upd{background:var(--upd-soft);color:var(--upd)}
.ex{color:var(--muted);font-size:13px;margin-top:4px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.empty{color:var(--muted);padding:40px 0;text-align:center}
.note{color:var(--muted);font-size:12px;margin-top:24px;padding-left:4px}

/* 携帯・タブレット：サイドバーをやめ、上部の操作バーだけで絞り込む */
@media (max-width:820px){
  .head{padding:14px 16px}
  .head h1{font-size:18px}
  .wrap{grid-template-columns:1fr}
  .side{display:none}
  main{padding:16px 12px 50px}
  .stats{grid-template-columns:repeat(2,1fr);gap:8px}
  .stat{padding:12px 14px}
  .stat b{font-size:22px}
  .bar{position:sticky;top:0;z-index:5;padding:12px}
  input[type=search]{flex:1 1 100%;font-size:16px}  /* 16px未満だとiOSで拡大される */
  #catsel{display:block;flex:1 1 auto;min-width:0;font-size:16px}
  #sort{flex:0 1 auto;min-width:0;font-size:16px}
  .count{flex:1 1 100%;margin-left:0}
  .sec{padding:4px 14px 10px}
  .more{flex:1 1 100%;margin-left:0}
  .t{font-size:15px}
}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto !important}}
</style>
"""


MARKUP = r"""<div class="head">
  <h1>GTO Wizard ブログ記事マップ</h1>
  <div class="sub" id="sub"></div>
</div>

<div class="wrap">
  <aside class="side" id="nav"></aside>
  <main>
    <div class="stats" id="stats"></div>
    <div class="bar">
      <input type="search" id="q" placeholder="タイトル・本文冒頭で検索"
             aria-label="記事を検索">
      <select id="catsel" aria-label="カテゴリを選ぶ"></select>
      <select id="sort" aria-label="並び替え">
        <option value="new">公開日：新しい順</option>
        <option value="old">公開日：古い順</option>
        <option value="short">読了時間：短い順</option>
        <option value="long">読了時間：長い順</option>
        <option value="title">タイトル順</option>
      </select>
      <span class="count" id="count"></span>
    </div>
    <div id="list"></div>
    <p class="note" id="note"></p>
  </main>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const LABEL = {};
D.groups.forEach(g => g.tags.forEach(t => LABEL[t.slug] = t.label));
let filter = 'all', query = '', sort = 'new';

const esc = s => String(s).replace(/[&<>"]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function stats(){
  document.getElementById('sub').textContent =
    `最終更新 ${D.last_run}　/　これまでの取得回数 ${D.runs}回`
    + `　/　出典 blog.gtowizard.com ・ japan.gtowizard.com`;
  document.getElementById('stats').innerHTML = [
    ['全記事', D.total], ['日本語版あり', D.jp_count], ['カテゴリ', Object.keys(LABEL).length],
    [`新着（${D.window}日）`, D.new_count], [`更新（${D.window}日）`, D.upd_count],
  ].map(([k, v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
}

/* パソコン用のサイドバーと、携帯用のプルダウンを同じ内容で用意する */
function controls(){
  let side = `<button class="chip" data-f="all"><span>すべての記事</span>`
           + `<span class="n">${D.total}</span></button>`
           + `<button class="chip" data-f="new"><span>🆕 新着</span>`
           + `<span class="n">${D.new_count}</span></button>`;
  let sel = `<option value="all">すべての記事（${D.total}）</option>`
          + `<option value="new">🆕 新着（${D.new_count}）</option>`;
  side += `<button class="chip" data-f="jp"><span>🇯🇵 日本語版あり</span>`
        + `<span class="n">${D.jp_count}</span></button>`
        + `<button class="chip" data-f="nojp"><span>未訳（英語のみ）</span>`
        + `<span class="n">${D.total - D.jp_count}</span></button>`;
  sel += `<option value="jp">🇯🇵 日本語版あり（${D.jp_count}）</option>`
       + `<option value="nojp">未訳・英語のみ（${D.total - D.jp_count}）</option>`;
  if (D.upd_count) {
    side += `<button class="chip" data-f="upd"><span>✏️ 更新あり</span>`
          + `<span class="n">${D.upd_count}</span></button>`;
    sel += `<option value="upd">✏️ 更新あり（${D.upd_count}）</option>`;
  }
  D.groups.forEach(g => {
    side += `<div class="gtitle">${esc(g.label)}</div>`;
    sel += `<optgroup label="${esc(g.label)}">`;
    g.tags.forEach(t => {
      side += `<button class="chip" data-f="${esc(t.slug)}" title="${esc(t.name_en)}">`
            + `<span>${esc(t.label)}</span><span class="n">${t.count}</span></button>`;
      sel += `<option value="${esc(t.slug)}">${esc(t.label)}（${t.count}）</option>`;
    });
    sel += `</optgroup>`;
  });

  const side_el = document.getElementById('nav');
  side_el.innerHTML = side;
  side_el.onclick = e => {
    const b = e.target.closest('.chip');
    if (b) { filter = b.dataset.f; render(); }
  };
  const sel_el = document.getElementById('catsel');
  sel_el.innerHTML = sel;
  sel_el.onchange = e => { filter = e.target.value; render(); };
}

function matches(p){
  if (query) {
    const q = query.toLowerCase();
    /* 日本語タイトルも検索対象にするので、日本語で探しても引っかかる */
    if (!(p.title + ' ' + p.excerpt + ' ' + p.jp_title).toLowerCase().includes(q)) return false;
  }
  if (filter === 'all') return true;
  if (filter === 'new') return p.new;
  if (filter === 'upd') return p.upd;
  if (filter === 'jp') return !!p.jp_url;
  if (filter === 'nojp') return !p.jp_url;
  return p.tags.includes(filter);
}

function ordered(list){
  const c = {
    new:   (a, b) => b.ts - a.ts,
    old:   (a, b) => a.ts - b.ts,
    short: (a, b) => a.read - b.read || b.ts - a.ts,
    long:  (a, b) => b.read - a.read || b.ts - a.ts,
    title: (a, b) => a.title.localeCompare(b.title),
  }[sort];
  return list.slice().sort(c);
}

function card(p){
  const badges = (p.new ? `<span class="badge new">NEW ${p.seen}</span>` : '')
               + (p.upd ? `<span class="badge upd">更新</span>` : '');
  const tags = p.tags.map(s =>
    `<span class="tag" data-t="${esc(s)}">${esc(LABEL[s] || s)}</span>`).join('');
  const jp = p.jp_url
    ? `<a class="jp" href="${esc(p.jp_url)}" target="_blank" rel="noopener"`
      + ` title="日本語版を開く">🇯🇵 ${esc(p.jp_title)}</a>`
    : '';
  return `<li class="item">`
    + `<a class="t" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a>`
    + jp
    + `<div class="meta">${badges}<span>${p.date}</span>`
    + (p.read ? `<span>${p.read}分</span>` : '') + tags + `</div>`
    + (p.excerpt ? `<div class="ex">${esc(p.excerpt)}</div>` : '')
    + `</li>`;
}

function render(){
  document.querySelectorAll('.chip').forEach(c =>
    c.setAttribute('aria-pressed', c.dataset.f === filter));
  document.getElementById('catsel').value = filter;

  const hits = D.posts.filter(matches);
  document.getElementById('count').textContent = `${hits.length} 件`;
  const list = document.getElementById('list');

  if (!hits.length) {
    list.innerHTML = `<section class="sec"><p class="empty">該当する記事がありません。</p></section>`;
  } else if (filter === 'all' && !query) {
    /* 「すべて」のときはカテゴリごとに章立てして並べる */
    let h = '';
    D.groups.forEach(g => {
      h += `<div class="glabel">${esc(g.label)}</div>`;
      g.tags.forEach(t => {
        const items = ordered(hits.filter(p => p.primary === t.slug));
        if (!items.length) return;
        const more = t.count > items.length
          ? `<button class="more" data-t="${esc(t.slug)}">`
            + `他カテゴリと兼ねる記事も含めて全${t.count}件を見る →</button>`
          : '';
        h += `<section class="sec"><h2>${esc(t.label)}`
           + `<span class="n">${items.length}件</span>${more}</h2><ul>`
           + items.map(card).join('') + `</ul></section>`;
      });
    });
    list.innerHTML = h;
  } else {
    list.innerHTML = `<section class="sec"><ul>`
      + ordered(hits).map(card).join('') + `</ul></section>`;
  }

  list.onclick = e => {
    const t = e.target.closest('.tag, .more');
    if (!t) return;
    filter = t.dataset.t;
    document.getElementById('q').value = query = '';
    render();
    window.scrollTo({top: 0, behavior: 'smooth'});
  };
  document.getElementById('note').textContent =
    `「すべての記事」表示では、各記事を最初のカテゴリ1つに振り分けて章立てしています`
    + `（記事によっては複数カテゴリが付いています）。`
    + `カテゴリを選ぶと、そのカテゴリが付いた記事をすべて表示します。`;
}

document.getElementById('q').oninput = e => { query = e.target.value.trim(); render(); };
document.getElementById('sort').onchange = e => { sort = e.target.value; render(); };
stats(); controls(); render();
</script>
"""
