# -*- coding: utf-8 -*-
"""Genera icon.ico + icon.png a partir del diseño de icon.svg (render con Pillow)."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 512
HERE = os.path.dirname(os.path.abspath(__file__))


def hx(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rounded_mask(size, radius):
    m = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([20, 20, size - 20, size - 20], radius=radius, fill=255)
    return m


def build():
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))

    # ---- fondo diagonal (tema NEGRO) ----
    c0, c1, c2 = hx('#1f1f1f'), hx('#0a0a0a'), hx('#000000')
    bg = np.zeros((S, S, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:S, 0:S]
    t = (xx + yy) / (2.0 * S)
    for i, c in enumerate(zip(c0, c1)):
        pass
    # interp 3 stops
    seg1 = t < 0.55
    tt1 = np.clip(t / 0.55, 0, 1)
    tt2 = np.clip((t - 0.55) / 0.45, 0, 1)
    for ch in range(3):
        v = np.where(seg1,
                     c0[ch] + (c1[ch] - c0[ch]) * tt1,
                     c1[ch] + (c2[ch] - c1[ch]) * tt2)
        bg[..., ch] = v.astype(np.uint8)
    bg_img = Image.fromarray(bg, 'RGB').convert('RGBA')

    plate = rounded_mask(S, 108)
    img.paste(bg_img, (0, 0), plate)

    # ---- glow radial ----
    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    cx, cy, r = 256, 236, 220
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    alpha = np.clip(1.0 - dist / r, 0, 1) ** 1.4 * 0.40 * 255
    garr = np.zeros((S, S, 4), dtype=np.uint8)
    gc = hx('#cccccc')
    garr[..., 0] = gc[0]; garr[..., 1] = gc[1]; garr[..., 2] = gc[2]
    garr[..., 3] = alpha.astype(np.uint8)
    glow = Image.fromarray(garr, 'RGBA')
    # recortar glow a la placa
    glow.putalpha(Image.composite(glow.getchannel('A'), Image.new('L', (S, S), 0), plate))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)

    # ---- grid sutil (clip a placa) ----
    grid = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for gy in range(120, 384, 48):
        gd.line([(0, gy), (S, gy)], fill=hx('#888888') + (18,), width=2)
    grid.putalpha(Image.composite(grid.getchannel('A'), Image.new('L', (S, S), 0), plate))
    img = Image.alpha_composite(img, grid)
    draw = ImageDraw.Draw(img)

    # ---- ecualizador con gradiente vertical compartido ----
    top_lut = hx('#f2f2f2'); mid_lut = hx('#999999'); bot_lut = hx('#333333')
    def col_at(y):
        if y <= 144: return top_lut
        if y >= 384: return bot_lut
        if y <= 264:
            return lerp(top_lut, mid_lut, (y - 144) / 120.0)
        return lerp(mid_lut, bot_lut, (y - 264) / 120.0)

    bars = [  # (x, top_y)
        (96, 264), (144, 184), (192, 224), (240, 144),
        (288, 214), (336, 174), (384, 274),
    ]
    bw = 32
    baseline = 384
    bars_layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    bl = ImageDraw.Draw(bars_layer)
    for bx, ty in bars:
        # pintar fila por fila el gradiente
        for y in range(ty, baseline):
            bl.line([(bx, y), (bx + bw, y)], fill=col_at(y))
        # mascara redondeada de la barra
    # mascara: redondear cada barra
    barmask = Image.new('L', (S, S), 0)
    bm = ImageDraw.Draw(barmask)
    for bx, ty in bars:
        bm.rounded_rectangle([bx, ty, bx + bw, baseline], radius=12, fill=255)
    bars_layer.putalpha(Image.composite(bars_layer.getchannel('A'),
                                        Image.new('L', (S, S), 0), barmask))
    img = Image.alpha_composite(img, bars_layer)
    draw = ImageDraw.Draw(img)

    # puntas accent
    for bx, ty in bars:
        draw.rounded_rectangle([bx, ty - 2, bx + bw, ty + 6], radius=4, fill=hx('#ffffff'))

    # ---- scanlines ----
    scan = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan)
    for sy in range(100, 384, 30):
        sd.rectangle([0, sy, S, sy + 3], fill=hx('#000000') + (60,))
    scan.putalpha(Image.composite(scan.getchannel('A'), Image.new('L', (S, S), 0), plate))
    img = Image.alpha_composite(img, scan)
    draw = ImageDraw.Draw(img)

    # ---- wordmark ----
    font = None
    for fn in ['consolab.ttf', 'consola.ttf', 'cour.ttf']:
        try:
            font = ImageFont.truetype(fn, 50)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    txt1, txt2 = 'UTMOST', '.FM'
    w1 = draw.textlength(txt1, font=font)
    w2 = draw.textlength(txt2, font=font)
    total = w1 + w2
    x0 = 256 - total / 2
    ty = 408
    draw.text((x0, ty), txt1, font=font, fill=hx('#cccccc'))
    draw.text((x0 + w1, ty), txt2, font=font, fill=hx('#ffffff'))

    # ---- borde glow ----
    bdr = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bdr)
    bd.rounded_rectangle([20, 20, S - 20, S - 20], radius=108,
                         outline=hx('#b3b3b3') + (255,), width=10)
    img = Image.alpha_composite(img, bdr)

    return img


def main():
    img = build()
    png_path = os.path.join(HERE, 'icon.png')
    ico_path = os.path.join(HERE, 'icon.ico')
    img.resize((256, 256), Image.LANCZOS).save(png_path)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format='ICO', sizes=sizes)
    print('icon.png ->', png_path)
    print('icon.ico ->', ico_path)


if __name__ == '__main__':
    main()
