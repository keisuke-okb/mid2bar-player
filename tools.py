import math
import os
import sys
import json
import pygame
import numpy as np

if os.path.exists("project.json"):
    with open("project.json", "r", encoding="utf-8") as f:
        proj = json.load(f)
        l = proj["editor_lang"]
else:
    l = "en"

with open(f"./lang/{l}.json", "r", encoding="utf-8") as f:
    lang = json.load(f)


def get_lang_text(k):
    return lang["main_gui"].get(k, k)


def get_lang_text_app(k):
    return lang["app"].get(k, k)


def load_image(img_path):
    return pygame.image.load(img_path).convert_alpha()


def scale_with_aspect(image, scale):
    if scale <= 0:
        raise ValueError("scale は正の数である必要があります。")

    w, h = image.get_width(), image.get_height()
    new_w = max(1, math.ceil(w * scale))
    new_h = max(1, math.ceil(h * scale))

    return pygame.transform.smoothscale(image, (new_w, new_h))


def draw_stretchable_rounded_rect(
    screen, x, y, width, height, left_img, mid_img, right_img, padding
):

    assert left_img.get_width() == right_img.get_width()
    bar_lr_w = left_img.get_width() - padding
    bar_h = mid_img.get_height() - padding * 2

    if width >= bar_lr_w * 2:
        draw_x = x - padding
        draw_y = y - padding
        screen.blit(left_img, (draw_x, draw_y))
        draw_x += left_img.get_width()

        mid_w = width - (bar_lr_w * 2)
        if mid_w > 0:
            mid_scaled = pygame.transform.smoothscale(
                mid_img, (math.ceil(mid_w), mid_img.get_height())
            )
            screen.blit(mid_scaled, (draw_x, draw_y))
            draw_x += mid_w

        screen.blit(right_img, (draw_x, draw_y))

    else:
        scale = width / (bar_lr_w * 2)
        padding_lr_scaled = padding * scale
        left_scaled = pygame.transform.smoothscale(
            left_img, (math.ceil(left_img.get_width() * scale), left_img.get_height())
        )
        draw_x = x - padding_lr_scaled
        draw_y = y - padding
        screen.blit(left_scaled, (draw_x, draw_y))
        draw_x += left_scaled.get_width()
        right_scaled = pygame.transform.smoothscale(
            right_img,
            (math.ceil(right_img.get_width() * scale), right_img.get_height()),
        )
        screen.blit(right_scaled, (draw_x, draw_y))


def blit_with_alpha(target, source, pos, crop_rect=None, alpha=1.0):
    a = max(0, min(1.0, alpha))
    a255 = int(a * 255)

    if crop_rect is not None:
        sub = source.subsurface(crop_rect).copy()
    else:
        sub = source.copy()

    sub.fill((255, 255, 255, a255), special_flags=pygame.BLEND_RGBA_MULT)

    target.blit(sub, pos)


def render_outlined_text(text, font, text_color, outline_color, outline_width=2):
    base = font.render(text, True, text_color)

    outline = pygame.Surface(
        (base.get_width() + outline_width * 2, base.get_height() + outline_width * 2),
        pygame.SRCALPHA,
    )
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                pos = (dx + outline_width, dy + outline_width)
                outline.blit(font.render(text, True, outline_color), pos)

    outline.blit(base, (outline_width, outline_width))

    return outline


def draw_sparkle(surface, color, center, radius, inner_ratio=0.35):
    cx, cy = center
    verts = [
        (cx, cy - radius),
        (cx + radius * inner_ratio, cy - radius * inner_ratio),
        (cx + radius, cy),
        (cx + radius * inner_ratio, cy + radius * inner_ratio),
        (cx, cy + radius),
        (cx - radius * inner_ratio, cy + radius * inner_ratio),
        (cx - radius, cy),
        (cx - radius * inner_ratio, cy - radius * inner_ratio),
    ]
    pygame.draw.polygon(surface, color, verts)


def round_pitch(input_pitch, original_pitch, tolerance=0.5):
    if abs(input_pitch - original_pitch) <= tolerance:
        return original_pitch
    else:
        return round(input_pitch)


def mod12_custom(x):
    r = x % 12
    if r > 6:
        r -= 12
    return r


def split_range(A, B, step):
    # 区間の端の候補を作成
    edges = np.arange(A, B, step)
    if edges[-1] < B:
        edges = np.append(edges, B)

    if len(edges) >= 3 and (edges[-1] - edges[-2]) < step:
        edges = np.delete(edges, -2)

    intervals = list(zip(edges[:-1], edges[1:]))
    return intervals


def bezier3(p0, p1, p2, p3, t):
    u = 1 - t
    x = (
        (u**3) * p0[0]
        + 3 * (u**2) * t * p1[0]
        + 3 * u * (t**2) * p2[0]
        + (t**3) * p3[0]
    )
    y = (
        (u**3) * p0[1]
        + 3 * (u**2) * t * p1[1]
        + 3 * u * (t**2) * p2[1]
        + (t**3) * p3[1]
    )
    return (x, y)


def point_on_curve_ratio(A, B, progress, curve_strength=0.2, accel=2.0):
    # clamp
    if progress <= 0.0:
        return A
    if progress >= 1.0:
        return B

    u = progress**accel

    mx = (A[0] + B[0]) / 2
    my = (A[1] + B[1]) / 2

    dx = B[0] - A[0]
    dy = B[1] - A[1]

    nx = -dy
    ny = dx

    length = math.hypot(nx, ny)
    if length != 0:
        nx /= length
        ny /= length

    AB_len = math.hypot(dx, dy)

    offset = AB_len * curve_strength

    C1 = (mx + nx * offset, my + ny * offset)
    C2 = (mx + nx * offset, my + ny * offset)

    return bezier3(A, C1, C2, B, u)


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        # onefile
        base_path = sys._MEIPASS
    else:
        # 通常 / onedir
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base_path, relative_path)
