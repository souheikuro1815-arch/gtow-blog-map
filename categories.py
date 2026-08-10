"""カテゴリの日本語名と大分類の定義。

GTOウィザード側で新しいタグが増えたら、ここに1行足すだけで一覧に反映される。
未定義のタグは自動的に「その他」グループに入り、英語名のまま表示される。
"""

# 大分類（表示したい順に並べる） -> そのグループに属するタグのslug
GROUPS = [
    ("format", "フォーマット別", ["mtt", "cash", "spin", "pko"]),
    ("theory", "理論・戦略", ["theory", "icm", "postflop", "multiway", "straddle"]),
    ("player", "対人・実戦", ["exploit", "profiles", "soft-skills"]),
    ("guide", "学習ガイド", ["guides"]),
    ("info", "運営・お知らせ", ["patch-notes", "news", "behind-the-scenes"]),
]

# タグslug -> 日本語の表示名
LABELS_JA = {
    "mtt": "MTT（トーナメント）",
    "cash": "キャッシュゲーム",
    "spin": "スピン&ゴー",
    "pko": "PKO（バウンティ）",
    "theory": "理論",
    "icm": "ICM",
    "postflop": "ポストフロップ",
    "multiway": "マルチウェイ",
    "straddle": "ストラドル",
    "exploit": "エクスプロイト",
    "profiles": "プレイヤータイプ分析",
    "soft-skills": "メンタル・ソフトスキル",
    "guides": "ガイド・使い方",
    "patch-notes": "パッチノート",
    "news": "ニュース",
    "behind-the-scenes": "舞台裏",
}

OTHER_GROUP = ("other", "その他")


def group_of(slug):
    """タグslugが属する大分類の (id, 表示名) を返す。未定義なら「その他」。"""
    for gid, gname, slugs in GROUPS:
        if slug in slugs:
            return gid, gname
    return OTHER_GROUP


def label_of(slug, fallback):
    """タグslugの日本語表示名。未定義なら元の英語名をそのまま使う。"""
    return LABELS_JA.get(slug, fallback)


def group_order():
    """大分類の並び順（その他は最後）。"""
    return [(gid, gname) for gid, gname, _ in GROUPS] + [OTHER_GROUP]
