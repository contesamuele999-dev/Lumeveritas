import io
from datetime import datetime, timezone
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

_OG_FONT_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
_OG_FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_OG_FONT_MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def render_og_image(topic: str, headline: str, published_iso: Optional[str] = None) -> bytes:
    W, H = 1200, 630
    bg = (249, 249, 246)
    fg = (17, 17, 17)
    accent = (217, 56, 30)
    muted = (110, 110, 100)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    for i in range(300):
        x = (i * 37) % W
        y = (i * 91) % H
        draw.point((x, y), fill=(230, 230, 220))
    pad = 48
    draw.rectangle([pad, pad, W - pad, H - pad], outline=fg, width=2)
    try:
        f_mono = ImageFont.truetype(_OG_FONT_MONO, 22)
        f_title = ImageFont.truetype(_OG_FONT_SERIF, 64)
        f_kicker = ImageFont.truetype(_OG_FONT_SANS, 20)
    except Exception:
        f_mono = ImageFont.load_default()
        f_title = ImageFont.load_default()
        f_kicker = ImageFont.load_default()
    box = 64
    draw.rectangle([pad + 40, pad + 40, pad + 40 + box, pad + 40 + box], fill=fg)
    draw.text((pad + 40 + 22, pad + 40 + 10), "L", font=f_title, fill=bg)
    draw.text((pad + 40 + box + 20, pad + 48), "LUME VERITAS", font=f_mono, fill=fg)
    draw.text((pad + 40 + box + 20, pad + 78), "le notizie che i giornali trascurano", font=f_kicker, fill=muted)
    topic_up = (topic or "").upper()[:36]
    tw = draw.textbbox((0, 0), topic_up, font=f_mono)
    pill_w = tw[2] - tw[0] + 32
    px1 = W - pad - 40 - pill_w
    py1 = pad + 46
    draw.rectangle([px1, py1, W - pad - 40, py1 + 40], fill=accent)
    draw.text((px1 + 16, py1 + 8), topic_up, font=f_mono, fill=(255, 255, 255))
    max_w = W - 2 * (pad + 40)
    lines = _wrap_text(draw, headline, f_title, max_w)[:5]
    y = pad + 200
    for ln in lines:
        draw.text((pad + 40, y), ln, font=f_title, fill=fg)
        y += 78
    draw.line([(pad + 40, H - pad - 90), (W - pad - 40, H - pad - 90)], fill=fg, width=2)
    draw.text((pad + 40, H - pad - 70), "APPROFONDISCI SU LUME.VERITAS", font=f_mono, fill=fg)
    if published_iso:
        try:
            ts = datetime.fromisoformat(published_iso.replace("Z", "+00:00")).strftime("%d.%m.%Y").upper()
        except Exception:
            ts = datetime.now(timezone.utc).strftime("%d.%m.%Y").upper()
    else:
        ts = datetime.now(timezone.utc).strftime("%d.%m.%Y").upper()
    tsw = draw.textbbox((0, 0), ts, font=f_mono)
    draw.text((W - pad - 40 - (tsw[2] - tsw[0]), H - pad - 70), ts, font=f_mono, fill=muted)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
