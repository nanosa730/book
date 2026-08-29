#!/usr/bin/env python3
"""「心晴日和」のエクスポートを、分析しやすいバッチファイルに分割する。

    python3 tools/split_posts.py 元データ.txt --out posts/ --size 50

区切りの検出は自動で試すが、実データを見る前に書いたものなので、
合わなければ --pattern で正規表現を渡す（名前付きグループ day / date が使える）。
本文は一字も変更しない。
"""
import argparse
import pathlib
import re
import sys

# 区切り行の候補。マッチ数が最も多いものを採用する。
DEFAULT_PATTERNS = [
    r"^\s*(?:心晴日和)?\s*[Dd]ay\s*[.:：#＃]?\s*(?P<day>\d{1,5})\b",
    r"^\s*心晴日和\s*[#＃]?\s*(?P<day>\d{1,5})\b",
    r"^\s*[#＃]\s*(?P<day>\d{1,5})\s*$",
    r"^\s*(?P<date>\d{4}\s*[/年.\-]\s*\d{1,2}\s*[/月.\-]\s*\d{1,2})\s*日?\s*$",
]

DATE_RE = re.compile(r"(\d{4})\s*[/年.\-]\s*(\d{1,2})\s*[/月.\-]\s*(\d{1,2})")


def normalize_date(text):
    if not text:
        return None
    m = DATE_RE.search(text)
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


def pick_pattern(lines, explicit=None):
    candidates = [explicit] if explicit else DEFAULT_PATTERNS
    best, best_hits = None, 0
    for pat in candidates:
        rx = re.compile(pat)
        hits = sum(1 for ln in lines if rx.match(ln))
        if hits > best_hits:
            best, best_hits = rx, hits
    return best, best_hits


def split(lines, rx):
    """区切り行の位置で分割し、(header_line, body_lines) のリストを返す。"""
    starts = [i for i, ln in enumerate(lines) if rx.match(ln)]
    posts = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        posts.append((lines[start], lines[start + 1:end]))
    return posts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="エクスポートしたテキストファイル")
    ap.add_argument("--out", default="posts", help="出力先ディレクトリ")
    ap.add_argument("--size", type=int, default=50, help="1バッチの投稿数")
    ap.add_argument("--pattern", help="区切り行の正規表現（省略時は自動判定）")
    ap.add_argument("--dry-run", action="store_true", help="書き込まずに結果だけ表示")
    args = ap.parse_args()

    text = pathlib.Path(args.input).read_text(encoding="utf-8")
    lines = text.splitlines()

    rx, hits = pick_pattern(lines, args.pattern)
    if not rx or hits < 2:
        sys.exit(
            "区切り行を見つけられなかった。\n"
            "  --pattern に正規表現を渡してほしい。例：\n"
            "    --pattern '^\\s*Day\\s*(?P<day>\\d+)'\n"
            "  名前付きグループ day / date が使える（両方とも省略可）。"
        )
    print(f"区切りパターン: {rx.pattern}  （{hits} 件）", file=sys.stderr)

    posts = split(lines, rx)
    print(f"投稿数: {len(posts)}", file=sys.stderr)

    outdir = pathlib.Path(args.out)
    index = []
    batches = [posts[i:i + args.size] for i in range(0, len(posts), args.size)]

    for bn, batch in enumerate(batches, start=1):
        name = f"batch-{bn:04d}.md"
        chunks = []
        for header, body in batch:
            m = rx.match(header)
            groups = m.groupdict() if m else {}
            day = groups.get("day")
            # 日付は見出し行の直後に置かれていることが多いので、本文の頭も見る。
            # （本文は書き換えない。読み取るだけ）
            date = (normalize_date(groups.get("date") or header)
                    or normalize_date("\n".join(body[:3])))
            pid = f"day-{int(day):04d}" if day else f"{name[:-3]}-{len(chunks) + 1:03d}"
            index.append((pid, day or "", date or "", name))
            chunks.append(
                f"## Day {day or '?'} | {date or '?'}\n"
                f"<!-- id: {pid} / 原文の見出し行: {header.strip()} -->\n\n"
                + "\n".join(body).strip("\n")
                + "\n"
            )
        content = "\n---\n\n".join(chunks) + "\n"
        if args.dry_run:
            print(f"[dry-run] {outdir / name}  ({len(batch)} 投稿)", file=sys.stderr)
        else:
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / name).write_text(content, encoding="utf-8")
            print(f"書き出し: {outdir / name}  ({len(batch)} 投稿)", file=sys.stderr)

    if not args.dry_run:
        idx = "id\tday\tdate\tbatch\n" + "\n".join("\t".join(r) for r in index) + "\n"
        (outdir / "_index.tsv").write_text(idx, encoding="utf-8")
        print(f"索引: {outdir / '_index.tsv'}", file=sys.stderr)

    no_day = sum(1 for r in index if not r[1])
    no_date = sum(1 for r in index if not r[2])
    if no_day:
        print(f"注意: Day番号が取れなかった投稿が {no_day} 件ある。", file=sys.stderr)
    if no_date:
        print(f"注意: 日付が取れなかった投稿が {no_date} 件ある。"
              "（時系列の分析ができる範囲が狭まる）", file=sys.stderr)


if __name__ == "__main__":
    main()
