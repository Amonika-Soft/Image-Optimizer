#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import math
import logging
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageOps

try:
    import pillow_avif  # noqa
    AVIF_ENABLED = True
except Exception:
    AVIF_ENABLED = False

try:
    from tqdm import tqdm
except Exception:
    def tqdm(iterable, **kwargs):
        return iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SUPPORTED_INPUT_EXT = (".jpeg", ".jpg", ".png", ".webp", ".avif")
TARGET_FORMATS = ("original", "jpg", "png", "webp", "avif")


def sizeof_fmt(num_bytes: int) -> str:
    if num_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = int(math.floor(math.log(num_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(num_bytes / p, 2)
    return f"{s} {units[i]}"


def analyze_folder(input_folder: str):
    files = [f for f in os.listdir(input_folder)
             if os.path.isfile(os.path.join(input_folder, f))
             and os.path.splitext(f)[1].lower() in SUPPORTED_INPUT_EXT]
    total_size = sum(os.path.getsize(os.path.join(input_folder, f)) for f in files)
    return files, total_size


def parse_resize(s: str):
    if not s:
        return None, None
    if "x" not in s.lower():
        raise argparse.ArgumentTypeError("Resize must look like 1920x1080")
    w, h = s.lower().split("x", 1)
    return int(w) if w else None, int(h) if h else None


def save_image(img: Image.Image, out_path: str, target_fmt: str, quality: int, preserve_metadata: bool):
    ext = os.path.splitext(out_path)[1].lower()
    fmt = None

    if target_fmt == "jpg":
        fmt = "JPEG"
        out_path = os.path.splitext(out_path)[0] + ".jpg"
    elif target_fmt == "png":
        fmt = "PNG"
        out_path = os.path.splitext(out_path)[0] + ".png"
    elif target_fmt == "webp":
        fmt = "WEBP"
        out_path = os.path.splitext(out_path)[0] + ".webp"
    elif target_fmt == "avif":
        if not AVIF_ENABLED:
            raise RuntimeError("AVIF output requested, but pillow-avif-plugin is not installed.")
        fmt = "AVIF"
        out_path = os.path.splitext(out_path)[0] + ".avif"

    needs_rgb = (fmt in ("JPEG", "WEBP", "AVIF")) or (fmt is None and ext in (".jpg", ".jpeg", ".webp", ".avif"))
    if needs_rgb and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    save_kwargs = {}
    if fmt in ("JPEG", "WEBP", "AVIF") or (fmt is None and ext in (".jpg", ".jpeg", ".webp", ".avif")):
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True

    if preserve_metadata:
        try:
            exif = img.getexif()
            if exif:
                save_kwargs["exif"] = exif.tobytes()
        except Exception:
            pass

    img.save(out_path, format=fmt, **save_kwargs)
    return out_path


def process_one(input_folder: str, output_folder: str, filename: str,
                quality: int, max_w: int, max_h: int,
                preserve_metadata: bool, target_format: str) -> dict:
    src_path = os.path.join(input_folder, filename)
    dst_path = os.path.join(output_folder, filename)
    original_size = os.path.getsize(src_path)

    try:
        with Image.open(src_path) as im:
            if max_w or max_h:
                im = ImageOps.exif_transpose(im)
                im.thumbnail((max_w or im.width, max_h or im.height))
            saved_path = save_image(im, dst_path, target_format, quality, preserve_metadata)
            optimized_size = os.path.getsize(saved_path)
    except Exception as e:
        logging.error(f"Failed: {filename} — {e}")
        return {"filename": filename, "status": f"error: {e}", "original_bytes": original_size,
                "optimized_bytes": original_size, "reduction_pct": 0.0, "output_path": ""}

    reduction = (original_size - optimized_size) / original_size * 100 if original_size else 0.0
    logging.info(f"Optimized {filename} | {sizeof_fmt(original_size)} → {sizeof_fmt(optimized_size)} | -{reduction:.2f}%")
    return {"filename": filename, "status": "ok", "original_bytes": original_size,
            "optimized_bytes": optimized_size, "reduction_pct": reduction, "output_path": saved_path}


def write_csv(rows: list, csv_path: str):
    fieldnames = ["filename", "status", "original_bytes", "optimized_bytes", "reduction_pct", "output_path"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def plot_and_save(rows: list, charts_dir: str):
    os.makedirs(charts_dir, exist_ok=True)
    names = [r["filename"] for r in rows]
    reductions = [max(0.0, r["reduction_pct"]) for r in rows]

    plt.figure()
    plt.title("Savings per file (%)")
    plt.xlabel("Files")
    plt.ylabel("Size reduction (%)")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.bar(range(len(names)), reductions)
    bar_path = os.path.join(charts_dir, "per_file_savings.png")
    plt.savefig(bar_path, dpi=150)
    plt.close()

    total_original = sum(r["original_bytes"] for r in rows)
    total_optimized = sum(r["optimized_bytes"] for r in rows)
    plt.figure()
    plt.title("Total size before vs after")
    plt.pie([total_original, total_optimized], labels=["Before", "After"], autopct="%1.1f%%")
    pie_path = os.path.join(charts_dir, "total_pie.png")
    plt.savefig(pie_path, dpi=150)
    plt.close()

    return bar_path, pie_path


def write_html(rows: list, html_path: str, bar_path: str, pie_path: str,
               input_folder: str, output_folder: str):
    total_original = sum(r["original_bytes"] for r in rows)
    total_optimized = sum(r["optimized_bytes"] for r in rows)
    saved = total_original - total_optimized
    saved_pct = (saved / total_original * 100) if total_original else 0.0
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    def tr(r):
        return f"<tr><td>{r['filename']}</td><td align='right'>{sizeof_fmt(r['original_bytes'])}</td>" \
               f"<td align='right'>{sizeof_fmt(r['optimized_bytes'])}</td>" \
               f"<td align='right'>{r['reduction_pct']:.2f}%</td><td>{r['status']}</td></tr>"

    rows_html = "\n".join(tr(r) for r in rows)

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Image Optimization Report</title>
<style>body{{font-family:sans-serif;margin:32px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:6px}}th{{background:#f6f6f6}}</style>
</head><body>
<h1>Image Optimization Report</h1>
<p>Generated: {time_str}</p>
<p><b>Input:</b> {input_folder} <br><b>Output:</b> {output_folder}</p>
<p><b>Files:</b> {len(rows)} <br><b>Total saved:</b> {sizeof_fmt(saved)} ({saved_pct:.2f}%)</p>
<h2>Charts</h2>
<p><img src="{os.path.relpath(bar_path, os.path.dirname(html_path))}"></p>
<p><img src="{os.path.relpath(pie_path, os.path.dirname(html_path))}"></p>
<h2>Details</h2>
<table><tr><th>File</th><th>Before</th><th>After</th><th>Saved</th><th>Status</th></tr>
{rows_html}</table></body></html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description="Batch image optimization with CSV/HTML reports and charts.")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--resize", type=str, default="")
    parser.add_argument("--preserve-metadata", action="store_true")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--target-format", choices=TARGET_FORMATS, default="original")
    parser.add_argument("--report-prefix", default="report")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s - %(levelname)s - %(message)s")
    os.makedirs(args.output, exist_ok=True)

    files, total_size = analyze_folder(args.input)
    logging.info(f"Analyzing: {args.input} — {len(files)} files, total {sizeof_fmt(total_size)}")

    max_w, max_h = parse_resize(args.resize)
    results = []

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = [ex.submit(process_one, args.input, args.output, fname,
                             args.quality, max_w, max_h, args.preserve_metadata, args.target_format)
                   for fname in files]
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Optimizing"):
            results.append(fut.result())

    csv_path = os.path.join(args.output, f"{args.report_prefix}.csv")
    charts_dir = os.path.join(args.output, "charts")
    bar_path, pie_path = plot_and_save(results, charts_dir)
    html_path = os.path.join(args.output, f"{args.report_prefix}.html")
    write_csv(results, csv_path)
    write_html(results, html_path, bar_path, pie_path, args.input, args.output)

    total_original = sum(r["original_bytes"] for r in results)
    total_optimized = sum(r["optimized_bytes"] for r in results)
    saved = total_original - total_optimized
    pct = (saved / total_original * 100) if total_original else 0.0

    logging.info("=== Summary ===")
    logging.info(f"Original total:  {sizeof_fmt(total_original)}")
    logging.info(f"Optimized total: {sizeof_fmt(total_optimized)}")
    logging.info(f"Saved:           {sizeof_fmt(saved)} ({pct:.2f}%)")
    logging.info(f"CSV:  {csv_path}")
    logging.info(f"HTML: {html_path}")


if __name__ == "__main__":
    main()
