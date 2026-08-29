#!/usr/bin/env python3
"""投稿の長さと promise の関係を調べる。

  python3 tools/length_vs_promise.py

なのさには二つのモードがあるのではないか——
短い激励の回は「良くなる」と言い（希望）、
長く掘り下げる回は「見え方が変わる」と言う（希望ではない）。
本をどちらのモードで書くかは、docs/10_希望という問題.md に直結する。
"""
import collections
import json
import pathlib
import re
import statistics


def post_lengths(posts_dir="posts"):
    """バッチファイルを読み、Day番号ごとの本文の文字数を返す。"""
    lengths = {}
    for f in sorted(pathlib.Path(posts_dir).glob("batch-*.md")):
        text = f.read_text(encoding="utf-8")
        parts = re.split(r"^## Day (\d+)", text, flags=re.M)
        for i in range(1, len(parts), 2):
            day = int(parts[i])
            body = re.sub(r"<!--.*?-->", "", parts[i + 1], flags=re.S)
            body = re.sub(r"^\s*\|.*$", "", body, flags=re.M)      # 日付行
            body = body.replace("---", "")
            lengths[f"day-{day:04d}"] = len(re.sub(r"\s", "", body))
    return lengths


def main():
    lengths = post_lengths()
    rows = []
    for f in sorted(pathlib.Path("analysis/records").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))

    rows = [r for r in rows if r["id"] in lengths]
    if not rows:
        print("照合できる投稿が無い。")
        return

    by = collections.defaultdict(list)
    for r in rows:
        by[r["promise"]].append(lengths[r["id"]])

    print(f"# 長さと promise　対象 {len(rows)} 投稿\n")
    print("promise の別ごとの本文の長さ（空白を除いた文字数）\n")
    labels = {"promise": "良くなると約束（希望）",
              "reframe": "見え方が変わる",
              "neither": "どちらでもない"}
    for key in ("promise", "reframe", "neither"):
        v = by.get(key, [])
        if not v:
            continue
        print(f"  {labels[key]:22s} n={len(v):3d}  "
              f"中央値 {int(statistics.median(v)):5d}字  "
              f"最短 {min(v):5d}  最長 {max(v):5d}")

    p, rf = by.get("promise", []), by.get("reframe", [])
    if p and rf:
        print(f"\n  promise の最長 : {max(p)}字")
        print(f"  reframe の最短 : {min(rf)}字")
        if max(p) < min(rf):
            print("\n→ 完全に分離している。長さだけで promise / reframe が決まる。")
        else:
            overlap = [r["id"] for r in rows
                       if r["promise"] == "reframe" and lengths[r["id"]] <= max(p)]
            print(f"\n→ 重なりあり。promise の最長より短い reframe: {len(overlap)}本")
            print("   " + " ".join(sorted(overlap)))

    print("\n## 長い順（上位12本）\n")
    for r in sorted(rows, key=lambda r: -lengths[r["id"]])[:12]:
        print(f"  {lengths[r['id']]:5d}字  {r['promise']:8s}  {r['id']}")
    print("\n## 短い順（下位12本）\n")
    for r in sorted(rows, key=lambda r: lengths[r["id"]])[:12]:
        print(f"  {lengths[r['id']]:5d}字  {r['promise']:8s}  {r['id']}")


if __name__ == "__main__":
    main()
