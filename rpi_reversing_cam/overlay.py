from __future__ import annotations
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

def _parse_color(c: str) -> Tuple[int, int, int]:
    c = (c or "#00FF00").strip()
    if c.startswith("#"):
        c = c[1:]
    if len(c) == 6:
        r = int(c[0:2], 16)
        g = int(c[2:4], 16)
        b = int(c[4:6], 16)
        return (r, g, b)
    return (0, 255, 0)

def _draw_text(overlay: Image.Image, text: str, pos: str, font_size: int, margin: int) -> None:
    if not text:
        return
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", size=font_size)
    except Exception:
        font = ImageFont.load_default()
    w, h = overlay.size
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = margin, margin
    if pos == "top-right":
        x = w - tw - margin
    elif pos == "bottom-left":
        y = h - th - margin
    elif pos == "bottom-right":
        x = w - tw - margin
        y = h - th - margin
    # shadow
    for dx, dy in ((1, 1), (1, 0), (0, 1), (-1, -1)):
        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 160))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 220))

def _draw_line(overlay: Image.Image, start_xy: Tuple[int, int], end_xy: Tuple[int, int], width: int, color: str, alpha: float) -> None:
    draw = ImageDraw.Draw(overlay)
    r, g, b = _parse_color(color)
    a = max(0, min(255, int(alpha * 255)))
    draw.line([start_xy, end_xy], fill=(r, g, b, a), width=max(1, int(width)))

def draw_overlays(img: Image.Image, overlay_cfg: Dict, stats_text: Optional[str] = None) -> Image.Image:
    """Draw text + reversing guide lines. Returns RGB image."""
    if not overlay_cfg or not overlay_cfg.get("enabled", True):
        return img.convert("RGB") if img.mode != "RGB" else img

    base = img.convert("RGBA")
    w, h = base.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Text overlay
    text_cfg = overlay_cfg.get("text", {})
    if text_cfg.get("enabled", True) and text_cfg.get("content"):
        _draw_text(
            layer,
            text_cfg.get("content", ""),
            text_cfg.get("position", "top-left"),
            int(text_cfg.get("font_size", 20)),
            int(text_cfg.get("margin", 10)),
        )

    # Runtime stats (optional, bottom-left)
    if stats_text:
        _draw_text(
            layer,
            stats_text,
            "bottom-left",
            int(text_cfg.get("font_size", 20)),
            int(text_cfg.get("margin", 10)),
        )

    # Reversing lines (normalized coords 0..1)
    lines = overlay_cfg.get("lines", {})
    for key in ("line1", "line2"):
        ln = lines.get(key, {})
        if not ln.get("enabled", True):
            continue
        sx = float(ln.get("start", [0.1, 0.8])[0]) * w
        sy = float(ln.get("start", [0.1, 0.8])[1]) * h
        ex = float(ln.get("end", [0.9, 0.8])[0]) * w
        ey = float(ln.get("end", [0.9, 0.8])[1]) * h
        _draw_line(
            layer,
            (int(sx), int(sy)),
            (int(ex), int(ey)),
            int(ln.get("width_px", 4)),
            str(ln.get("color", "#00FF00")),
            float(ln.get("alpha", 0.7)),
        )

    return Image.alpha_composite(base, layer).convert("RGB")
