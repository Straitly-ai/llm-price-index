#!/usr/bin/env python3
"""Fetch live LLM API prices from straitly.ai/api/catalog and write prices.json, prices.csv, and README.md."""
import csv
import datetime as dt
import json
import pathlib
import urllib.request

CATALOG_URL = "https://straitly.ai/api/catalog"
EXCLUDE_IDS = {"gemini-4-neon"}
ROOT = pathlib.Path(__file__).resolve().parent


def fmt_usd(v):
    if v is None:
        return ""
    return f"${v:.4f}".rstrip("0").rstrip(".") if v < 0.1 else f"${v:.2f}"


def main():
    req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "straitly-llm-price-index/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.load(r)

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for m in raw.get("models", []):
        mid = str(m.get("id") or "")
        if mid in EXCLUDE_IDS or "gemini-4-neon" in str(m.get("key") or ""):
            continue
        price = m.get("price") or {}
        lst = m.get("list") or {}
        inp = price.get("input")
        out = price.get("output")
        if inp is None and out is None:
            continue
        rows.append({
            "key": m.get("key"),
            "id": mid,
            "name": m.get("name"),
            "lab": (m.get("author") or {}).get("label") or "",
            "context": m.get("context"),
            "released": m.get("released"),
            "straitly_input_per_1m_usd": inp,
            "straitly_output_per_1m_usd": out,
            "list_input_per_1m_usd": lst.get("input"),
            "list_output_per_1m_usd": lst.get("output"),
            "url": f"https://straitly.ai/models/{mid}",
        })

    rows.sort(key=lambda r: (r["released"] or "", r["key"] or ""), reverse=True)

    payload = {
        "source": "https://straitly.ai/llm-api-price-index",
        "catalog": CATALOG_URL,
        "updated_at_utc": now,
        "model_count": len(rows),
        "models": rows,
    }
    (ROOT / "prices.json").write_text(json.dumps(payload, indent=2) + "\n")

    fields = [
        "key", "name", "lab", "context", "released",
        "straitly_input_per_1m_usd", "straitly_output_per_1m_usd",
        "list_input_per_1m_usd", "list_output_per_1m_usd", "url",
    ]
    with (ROOT / "prices.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    top = rows[:40]
    lines = [
        "# LLM API Price Index (Open JSON & CSV Dataset)",
        "",
        f"Machine-readable LLM token pricing across **{len(rows)} models**, automatically refreshed daily from [Straitly](https://straitly.ai/llm-api-price-index).",
        "",
        f"- Updated: `{now}`",
        "- JSON feed: [`prices.json`](prices.json) (raw: `https://raw.githubusercontent.com/Straitly-ai/llm-price-index/main/prices.json`)",
        "- CSV feed: [`prices.csv`](prices.csv)",
        "- Interactive index & calculators: https://straitly.ai/llm-api-price-index",
        "- Full model catalog: https://straitly.ai/models",
        "",
        "## Newest 40 Models (USD per 1M tokens)",
        "",
        "| Model | Lab | Context | Straitly In / Out | Maker List In / Out |",
        "| :--- | :--- | --: | --: | --: |",
    ]
    for r in top:
        ctx = f"{r['context']//1000}K" if isinstance(r["context"], int) and r["context"] >= 1000 else str(r["context"] or "")
        s_str = f"{fmt_usd(r['straitly_input_per_1m_usd'])} / {fmt_usd(r['straitly_output_per_1m_usd'])}"
        l_str = f"{fmt_usd(r['list_input_per_1m_usd'])} / {fmt_usd(r['list_output_per_1m_usd'])}" if r["list_input_per_1m_usd"] is not None else "-"
        lines.append(f"| [{r['name']}]({r['url']}) | {r['lab']} | {ctx} | {s_str} | {l_str} |")

    lines += [
        "",
        "See [`prices.json`](prices.json) or [`prices.csv`](prices.csv) for all models. MIT licensed.",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(lines))
    print(f"wrote {len(rows)} models")


if __name__ == "__main__":
    main()
