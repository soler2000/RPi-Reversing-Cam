cat > ~/RPi-Reversing-Cam/rpi_reversing_cam/overlay.py <<'PY'
from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def _hex_to_rgb(s: str) -> Tuple[int,int,int]:
    s = s.strip()
    if s.startswith("#"): s = s[1:]
    if len(s) == 3:
        s = "".join(ch*2 for ch in s)
    r = int(s[0:2], 16); g = int(s[2:4], 16); b = int(s[4:6], 16)
    return (r,g,b)

def _pos(img_w: int, img_h: int, where: str, margin: int) -> Tuple[int,int]:
    where = (where or "top-left").lower()
    x = margin if "left" in where else (img_w - margin) if "right" in where else img_w//2
    y = margin if "top" in where else (img_h - margin) if "bottom" in where else img_h//2
    return x, y

def apply_overlay(frame_rgb: np.ndarray, cfg: Dict[str, Any]) -> np.ndarray:
    """frame_rgb: HxWx3 uint8, returns same shape with overlay drawn."""
    ov = cfg.get("overlay", {})
    if not ov.get("enabled", True):
        return frame_rgb

    img = Image.fromarray(frame_rgb, mode="RGB").convert("RGBA")
    lay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(lay)

    # line
    line = ov.get("line", {})
    if line.get("enabled", False):
        w, h = img.size
        sx = int((line.get("start", [0.1,0.7])[0]) * w)
        sy = int((line.get("start", [0.1,0.7])[1]) * h)
        ex = int((line.get("end", [0.9,0.7])[0]) * w)
        ey = int((line.get("end", [0.9,0.7])[1]) * h)
        color = _hex_to_rgb(line.get("color", "#00FF00"))
        width = int(line.get("width_px", 4))
        draw.line([(sx,sy),(ex,ey)], fill=color+(255,), width=width)

    # text
    txt = ov.get("text", {})
    if txt.get("enabled", False):
        content = txt.get("content", "RPi Cam")
        font_size = int(txt.get("font_size", 20))
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        margin = int(txt.get("margin", 8))
        pos_name = txt.get("position", "top-left")
        x, y = _pos(img.size[0], img.size[1], pos_name, margin)
        # adjust to keep inside if centered/right
        if "right" in pos_name:
            bbox = draw.textbbox((0,0), content, font=font)
            x -= (bbox[2]-bbox[0])
        if "center" in pos_name:
            bbox = draw.textbbox((0,0), content, font=font)
            x -= (bbox[2]-bbox[0])//2
        draw.text((x, y), content, fill=(255,255,255,255), font=font, stroke_width=2, stroke_fill=(0,0,0,160))

    out = Image.alpha_composite(img, lay).convert("RGB")
    return np.array(out, dtype=np.uint8)
PY
