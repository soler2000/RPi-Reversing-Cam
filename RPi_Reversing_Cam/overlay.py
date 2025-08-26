from __future__ import annotations
_DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"




def _parse_color(color: str, alpha: float) -> Tuple[int, int, int, int]:
color = color.strip()
if color.startswith("#"):
color = color[1:]
r = int(color[0:2], 16)
g = int(color[2:4], 16)
b = int(color[4:6], 16)
a = int(max(0.0, min(1.0, alpha)) * 255)
return (r, g, b, a)




def draw_overlays(img: Image.Image, cfg: Dict, stats_text: str | None = None) -> Image.Image:
if not cfg.get("enabled", True):
return img


draw = ImageDraw.Draw(img, "RGBA")
W, H = img.size


# Text overlay
text_cfg = cfg.get("text", {})
if text_cfg.get("enabled", False):
font_size = int(text_cfg.get("font_size", 20))
margin = int(text_cfg.get("margin", 10))
try:
font = ImageFont.truetype(_DEFAULT_FONT, font_size)
except Exception:
font = ImageFont.load_default()
text = text_cfg.get("content", "")
if stats_text:
text = f"{text} | {stats_text}" if text else stats_text
tw, th = draw.textbbox((0, 0), text, font=font)[2:]
pos = text_cfg.get("position", "top-left")
if pos == "top-right":
xy = (W - tw - margin, margin)
elif pos == "bottom-left":
xy = (margin, H - th - margin)
elif pos == "bottom-right":
xy = (W - tw - margin, H - th - margin)
else:
xy = (margin, margin)
# background
draw.rectangle([xy, (xy[0] + tw + 6, xy[1] + th + 4)], fill=(0, 0, 0, 96))
draw.text((xy[0] + 3, xy[1] + 2), text, font=font, fill=(255, 255, 255, 255))
elif stats_text:
# show stats alone if requested
try:
font = ImageFont.truetype(_DEFAULT_FONT, 16)
except Exception:
font = ImageFont.load_default()
draw.text((10, 10), stats_text, font=font, fill=(255, 255, 255, 200))


# Reversing guide lines (two independent lines)
lines_cfg = cfg.get("lines", {})
for key in ("line1", "line2"):
ln = lines_cfg.get(key, {})
if not ln.get("enabled", False):
continue
sx, sy = ln.get("start", [0.1, 0.8])
ex, ey = ln.get("end", [0.9, 0.8])
w = int(ln.get("width_px", 4))
color = ln.get("color", "#00FF00")
alpha = float(ln.get("alpha", 0.7))
rgba = _parse_color(color, alpha)
p1 = (int(sx * W), int(sy * H))
p2 = (int(ex * W), int(ey * H))
draw.line([p1, p2], fill=rgba, width=w)


return img