#!/usr/bin/env python3
"""
Render a captured hospital playbook transcript JSON into chat-bubble PNG pages.
"""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        paragraph = paragraph.rstrip()
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(" ")
        current = words[0]
        for word in words[1:]:
            trial = current + " " + word
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _bubble_height(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    pad: int,
    line_gap: int,
) -> tuple[int, list[str]]:
    lines = _wrap(draw, text, font, max_width - 2 * pad)
    line_h = font.size + line_gap if hasattr(font, "size") else 18
    h = pad * 2 + max(line_h * len(lines), line_h)
    return h, lines


def render(transcript_path: Path, out_prefix: Path, max_page_height: int = 4200) -> list[Path]:
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))

    width = 1600
    margin = 36
    lane_w = width - margin * 2
    user_w = int(lane_w * 0.78)
    assistant_w = int(lane_w * 0.78)
    tool_w = int(lane_w * 0.62)
    pad = 16
    line_gap = 6

    font_ui = _load_font("C:/Windows/Fonts/segoeui.ttf", 22)
    font_body = _load_font("C:/Windows/Fonts/consola.ttf", 18)
    font_small = _load_font("C:/Windows/Fonts/consola.ttf", 15)

    bg = (246, 240, 229)
    panel = (255, 252, 246)
    border = (205, 195, 175)
    user_bg = (245, 229, 210)
    assistant_bg = (216, 232, 244)
    tool_bg = (231, 236, 223)
    text_color = (32, 32, 32)
    muted = (84, 79, 70)

    # Build draw plan first with estimated heights.
    scratch = Image.new("RGB", (width, 200), bg)
    draw = ImageDraw.Draw(scratch)

    items: list[dict[str, Any]] = []
    items.append({"type": "title", "text": "Hospital CPM Playbook Session"})
    items.append(
        {
            "type": "meta",
            "text": f"Captured: {transcript['captured_at']} | Model: {transcript['model']} | Integration: {transcript['integration']}",
        }
    )

    for step in transcript["steps"]:
        items.append({"type": "step", "text": step["step"]})
        items.append({"type": "user", "text": step["prompt"]})

        tool_lines = []
        for call in step["tool_calls"]:
            tool_lines.append(f"{call['tool']} {json.dumps(call.get('arguments', {}), ensure_ascii=True)}")
        tool_text = "\n".join(tool_lines) if tool_lines else "(no tool calls)"
        items.append({"type": "tool", "text": tool_text})

        items.append({"type": "assistant", "text": step.get("assistant_message", "") or "(empty reply)"})

    # Pagination and rendering.
    pages: list[Path] = []
    page_index = 1
    y = margin
    img = Image.new("RGB", (width, max_page_height), bg)
    draw = ImageDraw.Draw(img)

    def flush_page(final: bool = False) -> None:
        nonlocal img, draw, y, page_index
        crop_h = min(max_page_height, y + margin)
        page_img = img.crop((0, 0, width, crop_h))
        out_path = Path(f"{out_prefix}-p{page_index}.png")
        page_img.save(out_path, format="PNG")
        pages.append(out_path)
        page_index += 1
        img = Image.new("RGB", (width, max_page_height), bg)
        draw = ImageDraw.Draw(img)
        y = margin

    def ensure_space(h: int) -> None:
        nonlocal y
        if y + h + margin > max_page_height:
            flush_page()

    for item in items:
        if item["type"] == "title":
            h = 60
            ensure_space(h)
            draw.text((margin, y), item["text"], fill=text_color, font=font_ui)
            y += h
            continue
        if item["type"] == "meta":
            h = 42
            ensure_space(h)
            draw.text((margin, y), item["text"], fill=muted, font=font_small)
            y += h
            continue
        if item["type"] == "step":
            h = 46
            ensure_space(h)
            draw.rounded_rectangle((margin, y, width - margin, y + 38), radius=12, fill=panel, outline=border, width=2)
            draw.text((margin + 14, y + 8), f"Step: {item['text']}", fill=text_color, font=font_small)
            y += h
            continue

        if item["type"] == "user":
            box_w = user_w
            h, lines = _bubble_height(draw, item["text"], font_body, box_w, pad, line_gap)
            ensure_space(h + 12)
            x1 = width - margin - box_w
            x2 = width - margin
            draw.rounded_rectangle((x1, y, x2, y + h), radius=20, fill=user_bg, outline=border, width=2)
            draw.text((x1 + pad, y + 6), "User", fill=muted, font=font_small)
            ty = y + 28
            for line in lines:
                draw.text((x1 + pad, ty), line, fill=text_color, font=font_body)
                ty += (font_body.size + line_gap if hasattr(font_body, "size") else 20)
            y += h + 12
            continue

        if item["type"] == "tool":
            box_w = tool_w
            h, lines = _bubble_height(draw, item["text"], font_small, box_w, pad, 4)
            ensure_space(h + 12)
            x1 = (width - box_w) // 2
            x2 = x1 + box_w
            draw.rounded_rectangle((x1, y, x2, y + h), radius=16, fill=tool_bg, outline=border, width=2)
            draw.text((x1 + pad, y + 6), "Tool Calls", fill=muted, font=font_small)
            ty = y + 26
            for line in lines:
                draw.text((x1 + pad, ty), line, fill=text_color, font=font_small)
                ty += (font_small.size + 4 if hasattr(font_small, "size") else 18)
            y += h + 12
            continue

        if item["type"] == "assistant":
            box_w = assistant_w
            h, lines = _bubble_height(draw, item["text"], font_body, box_w, pad, line_gap)
            ensure_space(h + 18)
            x1 = margin
            x2 = margin + box_w
            draw.rounded_rectangle((x1, y, x2, y + h), radius=20, fill=assistant_bg, outline=border, width=2)
            draw.text((x1 + pad, y + 6), "Assistant", fill=muted, font=font_small)
            ty = y + 28
            for line in lines:
                draw.text((x1 + pad, ty), line, fill=text_color, font=font_body)
                ty += (font_body.size + line_gap if hasattr(font_body, "size") else 20)
            y += h + 18
            continue

    flush_page(final=True)
    return pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render hospital transcript JSON to chat-bubble images.")
    parser.add_argument(
        "--input",
        default="docs/examples/hospital-cpm-playbook-session.json",
        help="Transcript JSON path.",
    )
    parser.add_argument(
        "--out-prefix",
        default="docs/examples/hospital-cpm-playbook-session",
        help="Output image prefix (without -pN.png suffix).",
    )
    parser.add_argument(
        "--max-page-height",
        type=int,
        default=4200,
        help="Maximum page height per PNG.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pages = render(Path(args.input), Path(args.out_prefix), max_page_height=args.max_page_height)
    print("Rendered pages:")
    for page in pages:
        print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
