#!/usr/bin/env python3
"""投稿の段落ごとに、具体か抽象かを見る。

    python3 tools/abstraction.py --day 1650    # 「でも」の階段が見える
    python3 tools/abstraction.py --day 1638    # 具体が続く場所が見える
    python3 tools/abstraction.py --summary     # 全投稿の抽象度

なのさ本人の言葉（2026-08-29）：
「私の文は具体と抽象を行き来する。抽象だけの時もある。具体だけはほとんどないと思う。
　抽象であれば書きやすい。でも、物語は具体です。具体の中で書いていくということ。」

抽象へ上がった瞬間に、痛みは痛くなくなる。
本は具体の中に留まらなければならない（docs/12_具体と抽象.md）。

語のマーカーによる粗い判定であり、正解ではない。目安として使う。
"""
import argparse
import pathlib
import re
import statistics

# 抽象へ上がったことを示す語
ABSTRACT = ["人生", "私たち", "僕たち", "大切", "意味", "価値", "成長", "幸福", "幸せ",
            "生き方", "世の中", "すべて", "全て", "人は", "誰でも", "本質", "自分自身",
            "ということ", "というのは", "かもしれ", "のだと思", "のでしょう", "べき",
            "つまり", "だからこそ", "ものです", "のである"]

# 具体に留まっていることを示す語
CONCRETE = ["時", "分", "朝", "夜", "昨日", "今朝", "円", "枚", "個", "本",
            "手", "足", "目", "耳", "指", "息", "汗", "涙", "喉", "肩", "背中",
            "風", "雨", "波", "空", "雲", "山", "海", "道", "水", "木", "花",
            "歩", "座", "立っ", "見た", "言っ", "聞い", "置い", "触", "食べ"]

# 段落の頭に来ると、抽象への階段になりやすい語
STAIRS = ["でも", "けれど", "けれども", "しかし", "だから", "つまり", "むしろ",
          "そして", "だからこそ", "ただ"]

# 一般化した瞬間。ここから先は、その出来事の話ではなくなる
GENERAL = ["人生", "私たち", "僕たち", "人は", "誰でも", "みんな", "世の中",
           "も同じ", "もきっと同じ", "ものです", "のである", "生き方", "人間",
           "にも似て", "人というのは", "私たちは"]

# 感情に名前をつけた語。名前は書くが、なのさは中には入らない
EMOTION = ["悔し", "悲し", "怖", "こわ", "嬉し", "うれし", "つら", "辛い",
           "苦し", "寂し", "さみし", "不安", "恐怖", "腹が立"]


def score(block):
    a = sum(block.count(w) for w in ABSTRACT)
    c = sum(block.count(w) for w in CONCRETE)
    c += len(re.findall(r"[0-9０-９]", block))
    c += len(re.findall(r"[ァ-ヴー]{3,}", block))
    return a, c


def label(a, c):
    if a == 0 and c == 0:
        return "—　", ""
    if a > c:
        return "抽象", "░" * min(20, a * 2)
    if c > a:
        return "具体", "█" * min(20, c * 2)
    return "中間", "▒" * 4


def load_posts(posts_dir="posts"):
    posts = {}
    for f in sorted(pathlib.Path(posts_dir).glob("batch-*.md")):
        text = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
        parts = re.split(r"^## Day (\d+).*$", text, flags=re.M)
        for i in range(1, len(parts), 2):
            posts[int(parts[i])] = parts[i + 1].replace("---", "")
    return posts


def blocks_of(body):
    return [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]


def trace(day, body):
    print(f"# Day {day}　段落ごとの具体／抽象\n")
    print("  具体 █　抽象 ░　中間 ▒　—＝マーカー無し")
    print("  ★＝抽象への階段になりやすい語で始まる　般＝一般化した　情＝感情に名前をつけた\n")
    first_general = None
    for n, b in enumerate(blocks_of(body), 1):
        a, c = score(b)
        lab, bar = label(a, c)
        head = re.sub(r"\s+", "", b)[:26]
        marks = ""
        if any(b.lstrip().startswith(w) for w in STAIRS):
            marks += "★"
        if any(w in b for w in GENERAL):
            marks += "般"
            first_general = first_general or n
        if any(w in b for w in EMOTION):
            marks += "情"
        print(f"{n:3d} {marks:6s} {lab}  {bar:22s} {head}")
    a, c = score(body)
    print(f"\n  全体：抽象 {a} / 具体 {c}")
    if first_general:
        total = len(blocks_of(body))
        print(f"  一般化した段落：{first_general} / {total}"
              f"（{100 * first_general / total:.0f}%の位置）")
        print("  ここから先は、その出来事の話ではなくなる。")


def general_at(body):
    """一段落目から数えて、何番目で一般化するか。（位置, 全段落数）"""
    bs = blocks_of(body)
    for n, b in enumerate(bs, 1):
        if any(w in b for w in GENERAL):
            return n, len(bs)
    return None, len(bs)


def summary(posts):
    rows = []
    for day, body in posts.items():
        n, total = general_at(body)
        rows.append((n / total if n else 1.01, n, total, day))
    rows.sort()
    print("# どこで一般化するか\n")
    print("その出来事の話をやめて「人生」「私たち」「人は」へ移る位置。")
    print("早いほど、具体に留まっていない。\n")
    print("  位置    段落      Day\n")
    never = 0
    for r, n, total, day in rows:
        if n is None:
            never += 1
            print(f"   —      —/{total:<3d}    Day{day}  ← 最後まで一般化しない")
        else:
            bar = "█" * int(r * 24)
            print(f"  {r * 100:4.0f}%   {n:3d}/{total:<3d}    Day{day}  {bar}")
    done = [r for r, n, _, _ in rows if n]
    if done:
        print(f"\n  一般化する回：{len(done)}本／一般化しない回：{never}本")
        print(f"  一般化する位置の中央値：{statistics.median(done) * 100:.0f}%")
    print("\n（本は、最後まで一般化しない。→ docs/12_具体と抽象.md）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--posts", default="posts")
    args = ap.parse_args()

    posts = load_posts(args.posts)
    if not posts:
        print("投稿がまだ無い。")
        return
    if args.day:
        if args.day not in posts:
            print(f"Day{args.day} は未受領。")
            return
        trace(args.day, posts[args.day])
    else:
        summary(posts)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:      # head などに繋いだとき
        pass
