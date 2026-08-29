#!/usr/bin/env python3
"""PHASE 3 の「集計」部分。解釈はしない。材料を並べるだけ。

    python3 tools/report.py            # 全体
    python3 tools/report.py --top 40

出てくるのは頻度・共起・推移。
「なのさは、なぜ何度もこの話を書いているのか？」に答えるのは人間の仕事。
"""
import argparse
import collections
import itertools
import json
import pathlib
import unicodedata


def width(text):
    """全角を2、半角を1として数えた表示幅。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WFA" else 1 for c in text)


def pad(text, n):
    """表示幅 n になるまで右に空白を足す（長ければ切り詰める）。"""
    out = ""
    for c in text:
        if width(out) + width(c) > n:
            break
        out += c
    return out + " " * (n - width(out))


def load(records_dir):
    rows = []
    for f in sorted(pathlib.Path(records_dir).glob("*.jsonl")):
        for raw in f.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                rows.append(json.loads(raw))
    return rows


def bar(n, unit):
    return "█" * min(40, round(n / unit)) if unit else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="analysis/records")
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    rows = load(args.records)
    if not rows:
        print("分析レコードがまだ無い。（PHASE 2 未着手）")
        return

    print(f"# 集計　対象 {len(rows)} 投稿\n")

    # --- テーマの頻度 ---
    freq = collections.Counter(t for r in rows for t in r.get("themes", []))
    unit = max(freq.values()) / 40 if freq else 0
    print("## テーマの頻度\n")
    for t, c in freq.most_common(args.top):
        print(f"{c:5d}  {bar(c, unit):40s}  {t}")

    # --- 共起 ---
    print("\n## よく一緒に現れるテーマ\n")
    print("（別の話に見えて同じことを言っている「言い換えの束」の手がかり）\n")
    co = collections.Counter()
    for r in rows:
        for a, b in itertools.combinations(sorted(set(r.get("themes", []))), 2):
            co[(a, b)] += 1
    for (a, b), c in co.most_common(args.top):
        print(f"{c:5d}  {a} ＋ {b}")

    # --- 年ごとの推移 ---
    print("\n## 年ごとの推移\n")
    print("（思想が変化しているか。Day1のなのさと今のなのさは同じとは限らない）\n")
    years = sorted({str(r["date"])[:4] for r in rows if r.get("date")})
    if not years:
        print("date が記録されていないため、推移を出せない。")
    else:
        top_themes = [t for t, _ in freq.most_common(12)]
        per_year = {y: collections.Counter() for y in years}
        year_total = collections.Counter()
        for r in rows:
            if not r.get("date"):
                continue
            y = str(r["date"])[:4]
            year_total[y] += 1
            for t in r.get("themes", []):
                per_year[y][t] += 1
        head = pad("テーマ", 28) + "".join(y.rjust(8) for y in years)
        print(head)
        print(pad("投稿数", 28) + "".join(str(year_total[y]).rjust(8) for y in years))
        print("-" * width(head))
        for t in top_themes:
            cells = ""
            for y in years:
                n, tot = per_year[y][t], year_total[y]
                cells += (f"{100 * n / tot:.0f}%" if tot else "-").rjust(8)
            print(pad(t, 28) + cells)
        print("\n（％はその年の投稿のうち、そのテーマが付いた割合）")

    # --- 明示と推測 ---
    basis = collections.Counter(r.get("basis") for r in rows)
    print(f"\n## 人生観（第3層）の根拠\n")
    print(f"  stated （本文に書かれている）: {basis.get('stated', 0)}")
    print(f"  implied（読み取ったもの）    : {basis.get('implied', 0)}")
    print("\n implied が多いほど、なのさ本人への確認が必要になる。")

    # --- 熱量の高い投稿 ---
    hot = sorted([r for r in rows if r.get("strength", 0) >= 4],
                 key=lambda r: (-r.get("strength", 0), r.get("day") or 0))
    print(f"\n## 心が強く動いている投稿（strength 4以上）　{len(hot)} 件\n")
    print("（頻度が低くても、ここに根っこがある可能性が高い）\n")
    for r in hot[:60]:
        print(f"  [{r.get('strength')}] {r.get('id')}  {r.get('view', '')[:60]}")
    if len(hot) > 60:
        print(f"  … 他 {len(hot) - 60} 件")

    # --- 「良くなる」と約束しているか ---
    pr = collections.Counter(r.get("promise") for r in rows)
    n = len(rows)
    print("\n## 「良くなる」と約束しているか（本の結末を決める集計）\n")
    labels = [("promise", "良くなると約束している（希望）"),
              ("reframe", "見え方が変わると言っている（希望ではない）"),
              ("neither", "どちらでもない")]
    for key, label in labels:
        c = pr.get(key, 0)
        print(f"{c:5d}  {100 * c / n:5.1f}%  {bar(c, max(pr.values()) / 30 if pr else 0):30s}  {label}")
    p_n, r_n = pr.get("promise", 0), pr.get("reframe", 0)
    print()
    if p_n or r_n:
        if r_n > p_n * 2:
            print("→ reframe が優勢。なのさの文体は、最初から絶対負と両立していた可能性が高い。")
            print("　 執行草舟の「希望は悪徳」と衝突しない。憧れで終わらせる道が開く。")
        elif p_n > r_n:
            print("→ promise が優勢。衝突は本物。")
            print("　 執行草舟に従うか、読後感を守るかを選ぶことになる（docs/10）。")
        else:
            print("→ 拮抗している。時期による違いがないか、年ごとに見る必要がある。")

    # --- 触れかけて、触れなかったこと ---
    un = [r for r in rows if str(r.get("unsaid", "")).strip()]
    un.sort(key=lambda r: (-r.get("strength", 0), r.get("day") or 0))
    print(f"\n## 触れかけて、触れなかったこと　{len(un)} 件 / {len(rows)}\n")
    print("（本の核は1193本に書かれていない。核は空白の側にある。")
    print("　触れかけて引き返した場所が、物語の始点になる）\n")
    for r in un[:60]:
        print(f"  [{r.get('strength')}] {r.get('id')}  {r.get('unsaid', '')[:70]}")
    if len(un) > 60:
        print(f"  … 他 {len(un) - 60} 件")
    if not un:
        print("  一件も記録されていない。投稿の表面しか読んでいない可能性がある。")

    # --- なのさ本人の証言 ---
    tm = [r for r in rows if str(r.get("testimony", "")).strip()]
    print(f"\n## なのさ本人に聞いて分かったこと　{len(tm)} 件\n")
    print("（投稿を読んでも分からない。聞くしかない。本の材料はここにある）\n")
    for r in tm[:40]:
        print(f"  {r.get('id')}  {r.get('testimony', '')[:80]}")
    if not tm:
        print("  まだ聞けていない。strength 4〜5 の回から順に聞く。")

    # --- 反証 ---
    cn = [r for r in rows if str(r.get("counter_evidence", "")).strip()]
    print(f"\n## 仮説に合わない投稿　{len(cn)} 件 / {len(rows)}\n")
    print("（本の核の仮説で説明できない投稿。ここを軽く見ない）\n")
    for r in cn[:40]:
        print(f"  {r.get('id')}  {r.get('counter_evidence', '')[:80]}")
    if len(cn) > 40:
        print(f"  … 他 {len(cn) - 40} 件")
    if not cn:
        print("  反証が一件も記録されていない。読み方を疑うこと。")

    # --- 物語の種 ---
    seeds = [r for r in rows if str(r.get("story_seed", "")).strip()]
    print(f"\n## 物語の場面に変換できそうな投稿　{len(seeds)} 件")


if __name__ == "__main__":
    main()
