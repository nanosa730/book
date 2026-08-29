#!/usr/bin/env python3
"""analysis/records/*.jsonl を検査する。

    python3 tools/validate_records.py

1193本を分析する途中で形式がぶれると、PHASE 3 の集計ができなくなる。
1バッチ書き終えるたびに走らせる。
"""
import argparse
import collections
import json
import pathlib
import re
import sys

REQUIRED = ["id", "day", "source", "event", "insight", "view",
            "basis", "themes", "strength", "promise", "unsaid",
            "counter_evidence"]
OPTIONAL = ["date", "question", "quotes", "testimony", "story_seed",
            "links", "notes"]
BASIS = {"stated", "implied"}
PROMISE = {"promise", "reframe", "neither"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_vocabulary(path):
    """vocabulary.md の「## タグ一覧」表から、1列目のタグを読む。"""
    tags, in_table = set(), False
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_table = line.strip() == "## タグ一覧"
            continue
        if not in_table or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not cells[0] or set(cells[0]) <= set("-: "):
            continue
        if cells[0] == "タグ":
            continue
        tags.add(cells[0])
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="analysis/records")
    ap.add_argument("--vocabulary", default="analysis/vocabulary.md")
    args = ap.parse_args()

    vocab = load_vocabulary(args.vocabulary)
    files = sorted(pathlib.Path(args.records).glob("*.jsonl"))
    if not files:
        print("分析レコードがまだ無い。（PHASE 2 未着手）")
        return 0

    errors, warnings = [], []
    seen_ids = {}
    unknown_tags = collections.Counter()
    total = 0
    no_counter = collections.Counter()
    no_unsaid = collections.Counter()

    for f in files:
        for lineno, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            total += 1
            where = f"{f.name}:{lineno}"
            try:
                r = json.loads(raw)
            except json.JSONDecodeError as e:
                errors.append(f"{where} JSONとして読めない: {e}")
                continue

            for k in REQUIRED:
                if k not in r:
                    errors.append(f"{where} 必須項目が無い: {k}")
            for k in r:
                if k not in REQUIRED and k not in OPTIONAL:
                    warnings.append(f"{where} 知らない項目: {k}")

            rid = r.get("id")
            if rid in seen_ids:
                errors.append(f"{where} id が重複: {rid}（{seen_ids[rid]} と同じ）")
            elif rid:
                seen_ids[rid] = where

            if r.get("basis") not in BASIS:
                errors.append(f"{where} basis は stated / implied のどちらか: {r.get('basis')!r}")

            if r.get("promise") not in PROMISE:
                errors.append(
                    f"{where} promise は promise / reframe / neither のいずれか: "
                    f"{r.get('promise')!r}")

            s = r.get("strength")
            if not isinstance(s, int) or not 1 <= s <= 5:
                errors.append(f"{where} strength は 1〜5 の整数: {s!r}")

            d = r.get("date")
            if d is not None and not DATE_RE.match(str(d)):
                errors.append(f"{where} date は YYYY-MM-DD か null: {d!r}")

            themes = r.get("themes")
            if not isinstance(themes, list) or not themes:
                errors.append(f"{where} themes が空")
            else:
                for t in themes:
                    if t not in vocab:
                        unknown_tags[t] += 1
                        errors.append(f"{where} 語彙表に無いタグ: {t}")

            for k in ("event", "insight", "view"):
                if not str(r.get(k, "")).strip():
                    errors.append(f"{where} {k} が空（三層はすべて埋める）")

            if not str(r.get("counter_evidence", "")).strip():
                no_counter[f.name] += 1
            if not str(r.get("unsaid", "")).strip():
                no_unsaid[f.name] += 1

    print(f"レコード数: {total}（{len(files)} ファイル）")

    # 反証がゼロのバッチは、読み方が仮説に引きずられている可能性がある。
    for f in files:
        n = sum(1 for _ in f.read_text(encoding="utf-8").splitlines() if _.strip())
        if n and no_counter.get(f.name, 0) == n:
            warnings.append(
                f"{f.name} は counter_evidence が全件空。"
                "仮説に引きずられていないか読み返す。"
            )
        if n and no_unsaid.get(f.name, 0) == n:
            warnings.append(
                f"{f.name} は unsaid が全件空。"
                "本の核は空白の側にある。投稿の表面しか読んでいない可能性がある。"
            )

    if unknown_tags:
        print("\n語彙表に無いタグ（先に analysis/vocabulary.md へ追加する）:")
        for t, c in unknown_tags.most_common():
            print(f"  {t}  ({c}件)")

    if warnings:
        print(f"\n注意 {len(warnings)} 件:")
        for w in warnings[:40]:
            print(f"  - {w}")

    if errors:
        print(f"\nエラー {len(errors)} 件:")
        for e in errors[:60]:
            print(f"  - {e}")
        if len(errors) > 60:
            print(f"  … 他 {len(errors) - 60} 件")
        return 1

    print("\n形式に問題なし。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
