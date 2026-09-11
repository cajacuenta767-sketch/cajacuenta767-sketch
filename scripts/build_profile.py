#!/usr/bin/env python3
"""
Generador de los SVG del perfil de GitHub.

Lee `profile.json`, consulta la API de GitHub (REST + GraphQL) y escribe:

  assets/banner.svg          cabecera con el snippet de código y la mascota
  assets/stats.svg           followers / following / repositorios
  assets/pins/<repo>.svg     tarjetas de repositorios destacados
  assets/contributions.svg   calendario de contribuciones del último año
  assets/avatar.svg          mascota sola (para usar como foto de perfil)
  assets/skills.svg          lenguajes, frameworks y herramientas del CV
  assets/experience.svg      experiencia profesional
  assets/education.svg       formación y logros

Si la API no responde (sin red, sin token, límite de peticiones) usa los
datos guardados en `scripts/cache.json`, así el perfil nunca se queda vacío.

Uso:
  python scripts/build_profile.py            # intenta la API y cae al caché
  python scripts/build_profile.py --offline  # solo caché
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
PINS = os.path.join(ASSETS, "pins")
CACHE_PATH = os.path.join(ROOT, "scripts", "cache.json")
CONFIG_PATH = os.path.join(ROOT, "profile.json")

# ---------------------------------------------------------------- paleta ---
BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
LINK = "#58a6ff"
GREEN = "#3fb950"
GREEN_SOFT = "#7ee787"
INK = "#111318"          # contorno de la mascota
WHITE = "#ffffff"
PINK = "#f3b8c6"        # interior de las orejas
BLUSH = "#f4a6b7"
NOSE = "#e7a2b6"        # nariz rosada
PATCH = "#343a43"       # manchas negras del merle
MERLE = "#9aa3ad"       # manchas grises
EYE_BLUE = "#7cc4ee"    # ojo celeste
EYE_BROWN = "#6b4a2b"   # ojo marrón
HARNESS = "#7d8590"     # arnés
HEAT = ["#232a33", "#0e4429", "#006d32", "#26a641", "#39d353"]

FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Dart": "#00B4AB",
    "Python": "#3572A5", "HTML": "#e34c26", "CSS": "#563d7c", "Java": "#b07219",
    "Kotlin": "#A97BFF", "Rust": "#dea584", "Go": "#00ADD8", "PHP": "#4F5D95",
    "C#": "#178600", "C++": "#f34b7d", "C": "#555555", "Shell": "#89e051",
    "Vue": "#41b883", "Swift": "#F05138", "Ruby": "#701516", "Astro": "#ff5a03",
    "Svelte": "#ff3e00", "SCSS": "#c6538c", "Jupyter Notebook": "#DA5B0B",
}

# Octicons (MIT, © GitHub) --------------------------------------------------
ICON_STAR = ("M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 "
             ".416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l"
             "-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 "
             ".416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a"
             ".75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 "
             "3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 "
             "1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z")
ICON_FORK = ("M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 "
             "2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 "
             "0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 "
             "0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 "
             "0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z")
ICON_PEOPLE = ("M2 5.5a3.5 3.5 0 1 1 5.898 2.549 5.508 5.508 0 0 1 3.034 4.084.75.75 "
               "0 1 1-1.482.235 4 4 0 0 0-7.9 0 .75.75 0 0 1-1.482-.236A5.507 5.507 "
               "0 0 1 3.102 8.05 3.493 3.493 0 0 1 2 5.5ZM11 4a3.001 3.001 0 0 1 2.22 "
               "5.018 5.01 5.01 0 0 1 2.56 3.012.749.749 0 0 1-.885.954.752.752 0 0 "
               "1-.549-.514 3.507 3.507 0 0 0-2.522-2.372.75.75 0 0 1-.574-.73v-.352a"
               ".75.75 0 0 1 .416-.672A1.5 1.5 0 0 0 11 5.5.75.75 0 0 1 11 4Zm-5.5-.5a"
               "2 2 0 1 0-.001 3.999A2 2 0 0 0 5.5 3.5Z")
ICON_REPO = ("M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1"
             "-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 "
             "1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A"
             "2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 "
             "1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 "
             "15.7a.25.25 0 0 1-.4-.2Z")


def icon(path: str, x: float, y: float, size: float, color: str) -> str:
    s = size / 16
    return (f'<path transform="translate({x:.1f} {y:.1f}) scale({s:.3f})" '
            f'd="{path}" fill="{color}"/>')


# ------------------------------------------------------------- mascota ---
def sparkle(x: float, y: float, r: float, color: str = GREEN_SOFT, delay: float = 0) -> str:
    """Estrella de cuatro puntas que parpadea."""
    d = (f"M{x},{y - r} Q{x + r * .18},{y - r * .18} {x + r},{y} "
         f"Q{x + r * .18},{y + r * .18} {x},{y + r} "
         f"Q{x - r * .18},{y + r * .18} {x - r},{y} "
         f"Q{x - r * .18},{y - r * .18} {x},{y - r} Z")
    return (f'<path d="{d}" fill="{color}" class="tw" '
            f'style="animation-delay:{delay:.1f}s"/>')


def plus(x: float, y: float, r: float, color: str = GREEN, delay: float = 0) -> str:
    return (f'<path d="M{x - r},{y} h{2 * r} M{x},{y - r} v{2 * r}" stroke="{color}" '
            f'stroke-width="{max(2, r * .45):.1f}" stroke-linecap="round" class="tw" '
            f'style="animation-delay:{delay:.1f}s"/>')


def mascot_head(eyes: str = "open", tilt: float = 0) -> str:
    """Cabeza de la perrita centrada en (0,0): merle blanca, ojo celeste y gafas."""
    sw = 3.5
    ears = (
        # orejas caídas en forma de gota: izquierda blanca, derecha negra
        f'<g stroke="{INK}" stroke-width="{sw}" stroke-linejoin="round">'
        f'<path d="M-18,-30 C-34,-46 -58,-36 -60,-14 C-62,6 -54,24 -42,24 C-32,24 -30,8 -30,-4 Z" fill="{WHITE}"/>'
        f'<path d="M18,-30 C34,-46 58,-36 60,-14 C62,6 54,24 42,24 C32,24 30,8 30,-4 Z" fill="{PATCH}"/>'
        f'</g>'
        f'<path d="M-30,-26 C-40,-34 -52,-26 -52,-12 C-52,2 -47,14 -42,14 C-37,14 -36,4 -36,-4 Z" fill="{PINK}"/>'
        f'<path d="M30,-26 C40,-34 52,-26 52,-12 C52,2 47,14 42,14 C37,14 36,4 36,-4 Z" fill="{PINK}"/>'
    )
    head = (
        f'<ellipse cx="0" cy="0" rx="40" ry="34" fill="{WHITE}"/>'
        # manchas (recortadas a la cabeza): gris en la frente, negra sobre el ojo derecho
        f'<g clip-path="url(#hd)">'
        f'<path d="M-20,-36 C-6,-46 16,-44 26,-30 C18,-20 -2,-16 -18,-22 Z" fill="{MERLE}"/>'
        f'<circle cx="-6" cy="-30" r="2.5" fill="{PATCH}"/><circle cx="8" cy="-34" r="2" fill="{PATCH}"/>'
        f'<circle cx="16" cy="-26" r="2.2" fill="{PATCH}"/>'
        f'<path d="M6,-18 C22,-28 42,-14 40,6 C36,18 18,20 8,8 Z" fill="{PATCH}"/>'
        f'<circle cx="-30" cy="-6" r="3" fill="{MERLE}"/>'
        f'</g>'
        f'<ellipse cx="0" cy="0" rx="40" ry="34" fill="none" stroke="{INK}" stroke-width="{sw}"/>'
    )
    if eyes == "open":
        face = (
            # ojos: celeste (izquierda) y marrón (derecha)
            f'<ellipse cx="-16" cy="-3" rx="8" ry="8.5" fill="{WHITE}" stroke="{INK}" stroke-width="2"/>'
            f'<circle cx="-15" cy="-2" r="5.5" fill="{EYE_BLUE}"/><circle cx="-15" cy="-2" r="2.8" fill="{INK}"/>'
            f'<circle cx="-17" cy="-4.5" r="1.6" fill="{WHITE}"/>'
            f'<ellipse cx="16" cy="-3" rx="8" ry="8.5" fill="{WHITE}" stroke="{INK}" stroke-width="2"/>'
            f'<circle cx="17" cy="-2" r="5.5" fill="{EYE_BROWN}"/><circle cx="17" cy="-2" r="2.8" fill="{INK}"/>'
            f'<circle cx="15" cy="-4.5" r="1.6" fill="{WHITE}"/>'
            # gafas con cristal transparente
            f'<g stroke="{INK}" stroke-width="3" fill="#9fd3ff" fill-opacity=".14">'
            f'<rect x="-30" y="-15" width="27" height="23" rx="6"/>'
            f'<rect x="3" y="-15" width="27" height="23" rx="6"/>'
            f'<path d="M-3,-5 h6 M-30,-7 l-7,-3 M30,-7 l7,-3" fill="none" stroke-linecap="round"/>'
            f'</g>'
        )
    else:  # dormida
        face = (
            f'<path d="M-24,-2 q8,7 16,0 M8,-2 q8,7 16,0" fill="none" stroke="{INK}" '
            f'stroke-width="3" stroke-linecap="round"/>'
        )
    muzzle = (
        f'<ellipse cx="0" cy="18" rx="21" ry="15" fill="#f3f4f6" stroke="#cfd6de" stroke-width="2"/>'
        f'<ellipse cx="-33" cy="8" rx="5" ry="3" fill="{BLUSH}" opacity=".8"/>'
        f'<ellipse cx="33" cy="8" rx="5" ry="3" fill="{BLUSH}" opacity=".8"/>'
        # nariz rosada con motitas
        f'<path d="M-10,10 h20 a5,5 0 0 1 4,7 l-11,9 a4,4 0 0 1 -6,0 l-11,-9 a5,5 0 0 1 4,-7 Z" '
        f'fill="{NOSE}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>'
        f'<circle cx="-4" cy="14" r="1.3" fill="{PATCH}"/><circle cx="5" cy="13" r="1.1" fill="{PATCH}"/>'
        f'<path d="M0,26 v3 M-7,30 q7,6 14,0" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>'
    )
    return f'<g transform="rotate({tilt})">{ears}{head}{face}{muzzle}</g>'


def mascot_body() -> str:
    return (
        f'<path d="M-30,18 C-36,40 -32,66 0,66 C32,66 36,40 30,18 Z" '
        f'fill="{WHITE}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>'
        # manchas del lomo
        f'<g clip-path="url(#bd)"><path d="M18,40 C28,36 36,46 30,56 C24,62 14,56 16,48 Z" fill="{PATCH}"/>'
        f'<circle cx="-22" cy="52" r="4" fill="{MERLE}"/></g>'
        # arnés
        f'<path d="M-31,30 C-14,42 14,42 31,30" fill="none" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>'
        f'<path d="M-31,30 C-14,42 14,42 31,30" fill="none" stroke="{HARNESS}" stroke-width="7" stroke-linecap="round"/>'
        f'<path d="M-31,30 C-14,42 14,42 31,30" fill="none" stroke="#c9d1d9" stroke-width="1.5" stroke-dasharray="4 4"/>'
        f'<rect x="-6" y="32" width="12" height="9" rx="2" fill="#444c56" stroke="{INK}" stroke-width="2"/>'
    )


def mug(x: float, y: float, s: float = 1.0, steam: bool = True) -> str:
    """Taza con el símbolo </>. Origen: esquina superior izquierda de la taza."""
    body = (
        f'<g transform="translate({x} {y}) scale({s})">'
        f'<path d="M38,10 h8 a9,9 0 0 1 0,18 h-8" fill="none" stroke="{INK}" stroke-width="11" stroke-linecap="round"/>'
        f'<path d="M38,10 h8 a9,9 0 0 1 0,18 h-8" fill="none" stroke="{WHITE}" stroke-width="4.5"/>'
        f'<rect x="0" y="0" width="40" height="40" rx="6" fill="{WHITE}" stroke="{INK}" stroke-width="3.5"/>'
        f'<text x="20" y="26" font-family="{MONO}" font-size="14" font-weight="700" '
        f'fill="{INK}" text-anchor="middle">&lt;/&gt;</text>'
    )
    if steam:
        body += (
            f'<g fill="none" stroke="{MUTED}" stroke-width="2.5" stroke-linecap="round" class="steam">'
            f'<path d="M12,-6 c-4,-6 4,-10 0,-16"/>'
            f'<path d="M22,-8 c-4,-6 4,-10 0,-16" style="animation-delay:.6s"/>'
            f'<path d="M31,-5 c-4,-6 4,-10 0,-16" style="animation-delay:1.2s"/>'
            f'</g>'
        )
    return body + '</g>'


def keyboard(x: float, y: float, w: float = 150, h: float = 40) -> str:
    keys = []
    kw, kh, gap = 11, 8, 3
    cols = int((w - 16) // (kw + gap))
    for r in range(3):
        for c in range(cols):
            kx = x + 8 + c * (kw + gap) + (r * 4)
            if kx + kw > x + w - 8:
                continue
            ky = y + 7 + r * (kh + gap)
            keys.append(f'<rect x="{kx:.0f}" y="{ky:.0f}" width="{kw}" height="{kh}" rx="2" fill="#3a4150"/>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#21262d" '
            f'stroke="{INK}" stroke-width="3.5"/>' + "".join(keys))


def plant(x: float, y: float, s: float = 1.0) -> str:
    """Planta en maceta. Origen: base de la maceta."""
    return (
        f'<g transform="translate({x} {y}) scale({s})">'
        f'<g fill="#2ea043" stroke="{INK}" stroke-width="3" stroke-linejoin="round">'
        f'<ellipse cx="-22" cy="-62" rx="10" ry="20" transform="rotate(-35 -22 -62)"/>'
        f'<ellipse cx="22" cy="-64" rx="10" ry="20" transform="rotate(35 22 -64)"/>'
        f'<ellipse cx="0" cy="-74" rx="10" ry="24"/>'
        f'<ellipse cx="-8" cy="-52" rx="8" ry="14" transform="rotate(-15 -8 -52)" fill="#3fb950"/>'
        f'<ellipse cx="10" cy="-50" rx="8" ry="14" transform="rotate(20 10 -50)" fill="#3fb950"/>'
        f'</g>'
        f'<path d="M-30,-34 h60 l-7,34 h-46 Z" fill="#c8a27a" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>'
        f'<rect x="-34" y="-42" width="68" height="12" rx="4" fill="#d9b58f" stroke="{INK}" stroke-width="3.5"/>'
        f'</g>'
    )


def arm(d: str) -> str:
    """Brazo: trazo blanco grueso con contorno oscuro."""
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="{WHITE}" stroke-width="6" stroke-linecap="round"/>')


def motion(d: str) -> str:
    """Líneas de movimiento, claras para que se vean sobre el fondo oscuro."""
    return (f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="2.5" stroke-linecap="round"/>')


def mascot_typing(x: float, y: float, s: float = 1.0) -> str:
    """Mascota sentada tecleando, con taza a la derecha. (x,y) = centro de la cabeza."""
    return (
        f'<g transform="translate({x} {y}) scale({s})">'
        + mascot_body()
        + arm("M-24,36 C-46,40 -62,50 -56,62")
        + arm("M24,36 C42,42 50,50 44,62")
        + mascot_head()
        + keyboard(-92, 60, 160, 40)
        # manos sobre el teclado
        + f'<ellipse cx="-54" cy="66" rx="10" ry="6.5" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>'
        + f'<ellipse cx="42" cy="66" rx="10" ry="6.5" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>'
        + motion("M-78,56 l-7,-5 M-74,46 l-8,-3 M64,54 l7,-5 M60,45 l8,-3")
        + mug(84, 62, 1.0)
        + '</g>'
    )


def mascot_peek(x: float, y: float, s: float = 1.0) -> str:
    """Asoma la cabeza con una patita saludando (para el borde de una tarjeta)."""
    return (
        f'<g transform="translate({x} {y}) scale({s})">'
        + mascot_head(tilt=-12)
        + f'<ellipse cx="40" cy="26" rx="9" ry="7" fill="{WHITE}" stroke="{INK}" stroke-width="3" transform="rotate(-25 40 26)"/>'
        + motion("M54,12 l6,-7 M60,22 l8,-2")
        + '</g>'
    )


def mascot_sleep(x: float, y: float, s: float = 1.0) -> str:
    """Durmiendo con gorro y almohada, luna y zzz."""
    return (
        f'<g transform="translate({x} {y}) scale({s})">'
        f'<ellipse cx="0" cy="34" rx="58" ry="16" fill="#6e7681" stroke="{INK}" stroke-width="3.5"/>'
        f'<ellipse cx="0" cy="30" rx="50" ry="12" fill="#8b949e"/>'
        + mascot_head(eyes="closed", tilt=-14)
        # gorro
        + f'<g transform="rotate(-14)">'
        f'<path d="M-34,-22 C-26,-48 26,-52 46,-68 C34,-46 34,-30 34,-22 Z" fill="#1f6feb" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>'
        f'<path d="M-36,-20 C-24,-34 24,-34 36,-20" fill="none" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>'
        f'<path d="M-36,-20 C-24,-34 24,-34 36,-20" fill="none" stroke="{WHITE}" stroke-width="6" stroke-linecap="round"/>'
        f'<circle cx="48" cy="-70" r="7" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>'
        f'</g>'
        f'<text x="52" y="-40" font-family="{FONT}" font-size="16" font-weight="700" fill="{TEXT}" class="zz">z</text>'
        f'<text x="64" y="-58" font-family="{FONT}" font-size="20" font-weight="700" fill="{TEXT}" class="zz" style="animation-delay:.5s">z</text>'
        f'<text x="80" y="-80" font-family="{FONT}" font-size="24" font-weight="700" fill="{TEXT}" class="zz" style="animation-delay:1s">Z</text>'
        f'<path d="M-52,-72 a18,18 0 1 0 22,-20 a14,14 0 1 1 -22,20 Z" fill="#f2cc60" stroke="{INK}" stroke-width="3"/>'
        + sparkle(-66, -40, 5, "#f2cc60") + sparkle(-20, -90, 4, "#f2cc60", .7)
        + '</g>'
    )


def mascot_laptop(x: float, y: float, s: float = 1.0) -> str:
    """Portátil abierto con la cara de la mascota en la pantalla."""
    return (
        f'<g transform="translate({x} {y}) scale({s})">'
        f'<rect x="-46" y="-70" width="92" height="66" rx="8" fill="#21262d" stroke="{INK}" stroke-width="3.5"/>'
        f'<rect x="-40" y="-64" width="80" height="54" rx="4" fill="{BG}"/>'
        f'<g transform="translate(0 -30) scale(.42)">' + mascot_head() + '</g>'
        f'<path d="M-58,-4 h116 l10,18 h-136 Z" fill="#30363d" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>'
        f'<rect x="-16" y="0" width="32" height="6" rx="2" fill="#484f58"/>'
        + plus(-60, -76, 6, GREEN, .3) + sparkle(62, -70, 6, GREEN_SOFT, .9)
        + '</g>'
    )


def mascot_coffee(x: float, y: float, s: float = 1.0) -> str:
    """Sentada, sosteniendo una taza con las dos manos."""
    return (
        f'<g transform="translate({x} {y}) scale({s})">'
        + mascot_body()
        + mascot_head()
        + arm("M-24,36 C-32,50 -24,60 -10,60")
        + arm("M24,36 C32,50 26,60 12,60")
        + mug(-18, 40, .9)
        + f'<ellipse cx="-12" cy="62" rx="8" ry="5.5" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>'
        + f'<ellipse cx="14" cy="62" rx="8" ry="5.5" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>'
        + '</g>'
    )


def sticky_note(x: float, y: float, s: float = 1.0) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s}) rotate(8)">'
        f'<rect x="-30" y="-30" width="60" height="60" rx="3" fill="#f2cc60" stroke="{INK}" stroke-width="3"/>'
        f'<path d="M-18,-12 l6,6 l12,-12" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="M6,-14 h14 M6,-6 h10" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>'
        f'<rect x="-18" y="6" width="12" height="12" rx="2" fill="none" stroke="{INK}" stroke-width="3"/>'
        f'<path d="M0,10 h20 M0,16 h14" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>'
        f'</g>'
        + sparkle(x - 42, y - 34, 5, GREEN_SOFT, .4)
    )


STYLE = f"""<style>
  .tw {{ animation: tw 2.4s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }}
  @keyframes tw {{ 0%,100% {{ opacity: .35; transform: scale(.8); }} 50% {{ opacity: 1; transform: scale(1.15); }} }}
  .steam path {{ animation: steam 2.2s ease-in-out infinite; opacity: 0; }}
  @keyframes steam {{ 0% {{ opacity: 0; transform: translateY(6px); }} 40% {{ opacity: .9; }} 100% {{ opacity: 0; transform: translateY(-8px); }} }}
  .zz {{ animation: zz 2.4s ease-in-out infinite; opacity: 0; }}
  @keyframes zz {{ 0% {{ opacity: 0; transform: translate(0,4px); }} 35% {{ opacity: 1; }} 100% {{ opacity: 0; transform: translate(6px,-10px); }} }}
</style>"""


def svg(w: int, h: int, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title>{STYLE}'
            f'<defs><clipPath id="hd"><ellipse cx="0" cy="0" rx="40" ry="34"/></clipPath>'
            f'<clipPath id="bd"><path d="M-30,18 C-36,40 -32,66 0,66 C32,66 36,40 30,18 Z"/></clipPath></defs>'
            f'{body}</svg>')


def fmt(n: int) -> str:
    if n >= 1000:
        v = n / 1000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "k"
    return str(n)


def wrap(text: str, max_chars: int, max_lines: int = 2) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max_chars - 1].rstrip() + "…"
    return lines


# --------------------------------------------------------------- render ---
def render_banner(cfg: dict) -> str:
    W, H = 1200, 400
    body = [
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#0b0f14"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
        f'<pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">'
        f'<path d="M28 0H0V28" fill="none" stroke="#1b2129" stroke-width="1"/></pattern></defs>',
        f'<rect width="{W}" height="{H}" fill="url(#g)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#grid)" opacity=".55"/>',
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="16" fill="none" stroke="{BORDER}" stroke-width="3"/>',
    ]
    # snippet de código
    kw = {"for": "#ff7b72", "while": "#ff7b72", "if": "#ff7b72", "return": "#ff7b72"}
    y = 118
    for line in cfg["code_snippet"]:
        parts = []
        for tok in re.split(r"(\s+|[();{}]+)", line):
            if not tok:
                continue
            if tok in kw:
                parts.append(f'<tspan fill="{kw[tok]}">{escape(tok)}</tspan>')
            elif re.fullmatch(r"[();{}]+", tok):
                parts.append(f'<tspan fill="{TEXT}">{escape(tok)}</tspan>')
            elif re.fullmatch(r"\s+", tok):
                parts.append(escape(tok))
            else:
                parts.append(f'<tspan fill="#d2a8ff">{escape(tok)}</tspan>')
        body.append(f'<text x="70" y="{y}" font-family="{MONO}" font-size="34" '
                    f'xml:space="preserve">{"".join(parts)}</text>')
        y += 48
    # cursor parpadeante
    body.append(f'<rect x="70" y="{y - 30}" width="16" height="36" fill="{GREEN}" class="tw"/>')
    # brillitos
    for (x, yy, r, d) in [(560, 70, 9, 0), (640, 130, 6, .8), (1010, 60, 8, .4), (1110, 130, 6, 1.2),
                          (500, 300, 6, .6), (1060, 300, 7, 1.0)]:
        body.append(sparkle(x, yy, r, GREEN_SOFT, d))
    for (x, yy, r, d) in [(600, 40, 6, .3), (1120, 80, 7, .9), (520, 200, 5, 1.4)]:
        body.append(plus(x, yy, r, GREEN, d))
    # suelo
    body.append(f'<rect x="440" y="318" width="720" height="8" rx="4" fill="#1b2129"/>')
    body.append(mascot_typing(790, 178, 1.55))
    body.append(plant(1095, 320, 1.15))
    return svg(W, H, "".join(body), "for (;;) { code(); coffee(); }")


def stat_block(x: float, y: float, ic: str, value: str, label: str) -> str:
    return (
        icon(ic, x, y - 20, 30, MUTED)
        + f'<text x="{x + 44}" y="{y + 2}" font-family="{FONT}" font-size="30" font-weight="700" fill="{TEXT}">{escape(value)}</text>'
        + f'<text x="{x + 44}" y="{y + 26}" font-family="{FONT}" font-size="15" fill="{MUTED}">{escape(label)}</text>'
    )


def render_stats(user: dict) -> str:
    W, H = 900, 110
    third = W / 3
    body = [
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="14" fill="{CARD}" stroke="{BORDER}" stroke-width="3"/>',
        f'<line x1="{third:.0f}" y1="24" x2="{third:.0f}" y2="{H - 24}" stroke="{BORDER}" stroke-width="2"/>',
        f'<line x1="{2 * third:.0f}" y1="24" x2="{2 * third:.0f}" y2="{H - 24}" stroke="{BORDER}" stroke-width="2"/>',
        stat_block(70, 50, ICON_PEOPLE, fmt(user["followers"]), "followers"),
        stat_block(third + 70, 50, ICON_PEOPLE, fmt(user["following"]), "following"),
        stat_block(2 * third + 70, 50, ICON_REPO, fmt(user["public_repos"]), "repositorios"),
    ]
    return svg(W, H, "".join(body), "Estadísticas del perfil")


def render_pin(pin: dict, data: dict, lang_overrides: dict) -> str:
    W, H = 410, 190
    deco = pin.get("decoration", "none")
    # la tarjeta deja hueco a la izquierda o derecha para la decoración
    left_pad = 66 if deco in ("peek", "laptop") else 6
    right_pad = 72 if deco in ("mug", "note", "sleep") else 6
    cx, cy, cw, ch = left_pad, 16, W - left_pad - right_pad, 150
    name = pin["repo"]
    lang = lang_overrides.get(name) or data.get("language")
    body = [
        f'<rect x="{cx + 1.5}" y="{cy + 1.5}" width="{cw - 3}" height="{ch - 3}" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-width="3"/>',
        # icono de repo
        f'<rect x="{cx + 18}" y="{cy + 20}" width="30" height="30" rx="6" fill="#21262d" stroke="{BORDER}" stroke-width="2"/>',
        f'<text x="{cx + 33}" y="{cy + 41}" font-family="{MONO}" font-size="14" font-weight="700" fill="{TEXT}" text-anchor="middle">&gt;_</text>',
        f'<text x="{cx + 60}" y="{cy + 41}" font-family="{FONT}" font-size="19" font-weight="700" fill="{LINK}">{escape(name)}</text>',
    ]
    ty = cy + 70
    for line in wrap(pin.get("description", ""), int((cw - 40) / 7.6)):
        body.append(f'<text x="{cx + 18}" y="{ty}" font-family="{FONT}" font-size="14.5" fill="{TEXT}">{escape(line)}</text>')
        ty += 21
    fy = cy + ch - 24
    fx = cx + 18
    if lang:
        color = LANG_COLORS.get(lang, "#8b949e")
        body.append(f'<circle cx="{fx + 6}" cy="{fy - 4}" r="6" fill="{color}"/>')
        body.append(f'<text x="{fx + 18}" y="{fy}" font-family="{FONT}" font-size="13.5" fill="{TEXT}">{escape(lang)}</text>')
        fx += 30 + len(lang) * 7.6 + 12
    body.append(icon(ICON_STAR, fx, fy - 12, 16, MUTED))
    body.append(f'<text x="{fx + 22}" y="{fy}" font-family="{FONT}" font-size="13.5" fill="{TEXT}">{fmt(data.get("stars", 0))}</text>')
    fx += 22 + len(fmt(data.get("stars", 0))) * 8 + 18
    body.append(icon(ICON_FORK, fx, fy - 12, 16, MUTED))
    body.append(f'<text x="{fx + 22}" y="{fy}" font-family="{FONT}" font-size="13.5" fill="{TEXT}">{fmt(data.get("forks", 0))}</text>')

    if deco == "peek":
        body.append(mascot_peek(42, 104, .62))
        body.append(sparkle(14, 26, 6, GREEN_SOFT, .2) + plus(60, 14, 5, GREEN, .7))
    elif deco == "laptop":
        body.append(mascot_laptop(56, 140, .54))
    elif deco == "mug":
        body.append(mug(W - 60, 60, 1.05))
        body.append(sparkle(W - 14, 30, 5, GREEN_SOFT, .5))
    elif deco == "note":
        body.append(sticky_note(W - 40, 60, .88))
    elif deco == "sleep":
        body.append(mascot_sleep(W - 50, 112, .56))
    return svg(W, H, "".join(body), f"{name}: {pin.get('description', '')}")


DAYS_ES = ["Lun", "Mié", "Vie"]
MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def render_contributions(cal: dict | None) -> str:
    W, H = 1000, 300
    cell, gap = 10, 3
    gx, gy = 250, 74
    body = [
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="14" fill="{CARD}" stroke="{BORDER}" stroke-width="3"/>',
    ]
    if cal:
        weeks = cal["weeks"]
        title = f'{cal["total"]:,} contribuciones en el último año'.replace(",", ".")
    else:
        # sin datos todavía: cuadrícula vacía con las fechas reales
        today = dt.date.today()
        start = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
        weeks, wk = [], []
        d = start
        while d <= today:
            wk.append({"date": d.isoformat(), "level": 0})
            if len(wk) == 7:
                weeks.append(wk)
                wk = []
            d += dt.timedelta(days=1)
        if wk:
            weeks.append(wk)
        title = "Contribuciones en el último año"
    body.append(f'<text x="28" y="40" font-family="{FONT}" font-size="18" font-weight="700" fill="{TEXT}">{escape(title)}</text>')
    body.append(f'<text x="{W - 28}" y="40" font-family="{FONT}" font-size="13" fill="{MUTED}" text-anchor="end">Se actualiza cada día ✦</text>')
    # etiquetas de meses
    last_month = None
    for wi, wk in enumerate(weeks):
        for day in wk:
            m = int(day["date"][5:7])
            if m != last_month:
                if wi > 0 or last_month is None:
                    body.append(f'<text x="{gx + wi * (cell + gap)}" y="{gy - 10}" font-family="{FONT}" '
                                f'font-size="11" fill="{MUTED}">{MONTHS_ES[m - 1]}</text>')
                last_month = m
            break
    for i, lab in enumerate(DAYS_ES):
        body.append(f'<text x="{gx - 10}" y="{gy + (1 + i * 2) * (cell + gap) + 10}" font-family="{FONT}" '
                    f'font-size="11" fill="{MUTED}" text-anchor="end">{lab}</text>')
    for wi, wk in enumerate(weeks):
        for di, day in enumerate(wk):
            body.append(f'<rect x="{gx + wi * (cell + gap)}" y="{gy + di * (cell + gap)}" width="{cell}" '
                        f'height="{cell}" rx="2" fill="{HEAT[day["level"]]}"/>')
    # leyenda
    lx, ly = W - 28 - (5 * (cell + gap)) - 70, gy + 7 * (cell + gap) + 22
    body.append(f'<text x="{lx - 8}" y="{ly + 10}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">Menos</text>')
    for i, c in enumerate(HEAT):
        body.append(f'<rect x="{lx + i * (cell + gap)}" y="{ly}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')
    body.append(f'<text x="{lx + 5 * (cell + gap) + 6}" y="{ly + 10}" font-family="{FONT}" font-size="11" fill="{MUTED}">Más</text>')
    # mascota con café
    body.append(mascot_coffee(118, 168, .8))
    body.append(sparkle(40, 110, 6, GREEN_SOFT, .3) + plus(196, 92, 5, GREEN, .9))
    return svg(W, H, "".join(body), title)


def render_avatar() -> str:
    W = 460
    body = (
        f'<defs><clipPath id="c"><circle cx="{W / 2}" cy="{W / 2}" r="{W / 2}"/></clipPath></defs>'
        f'<g clip-path="url(#c)"><rect width="{W}" height="{W}" fill="{BG}"/>'
        + sparkle(70, 120, 12, GREEN_SOFT) + sparkle(400, 90, 10, GREEN_SOFT, .8)
        + plus(390, 170, 9, GREEN, .4) + plus(60, 210, 8, GREEN, 1.1)
        + mascot_typing(212, 186, 1.5)
        + f'</g><circle cx="{W / 2}" cy="{W / 2}" r="{W / 2 - 3}" fill="none" stroke="{BORDER}" stroke-width="6"/>'
    )
    return svg(W, W, body, "Avatar")



# ------------------------------------------------- tarjetas del CV ---
def chip(x: float, y: float, label: str, color: str) -> tuple[str, float]:
    """Píldora con punto de color y etiqueta. Devuelve (svg, ancho)."""
    w = 26 + len(label) * 7.2 + 14
    return (
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="30" rx="15" fill="#21262d" stroke="{BORDER}" stroke-width="1.5"/>'
        f'<circle cx="{x + 15:.0f}" cy="{y + 15:.0f}" r="5" fill="{color}"/>'
        f'<text x="{x + 26:.0f}" y="{y + 19.5:.0f}" font-family="{FONT}" font-size="13" fill="{TEXT}">{escape(label)}</text>',
        w,
    )


def card_title(text: str, y: float = 40) -> str:
    return (f'<text x="28" y="{y}" font-family="{FONT}" font-size="18" font-weight="700" '
            f'fill="{TEXT}">{escape(text)}</text>')


def trophy(x: float, y: float, s: float = 1.0) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="#f2cc60" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round">'
        f'<path d="M-7,-9 h14 v6 a7,7 0 0 1 -14,0 Z"/>'
        f'<path d="M-7,-7 h-4 a4,4 0 0 0 4,6 M7,-7 h4 a4,4 0 0 1 -4,6" fill="none"/>'
        f'<path d="M-2,3 h4 v4 h-4 Z"/><path d="M-6,7 h12 v3 h-12 Z"/>'
        f'</g>'
    )


def mortarboard(x: float, y: float, s: float = 1.0) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})">'
        f'<path d="M-14,4 v8 q14,9 28,0 v-8" fill="#30363d" stroke="{TEXT}" stroke-width="1.5"/>'
        f'<path d="M0,-10 L24,0 L0,10 L-24,0 Z" fill="#484f58" stroke="{TEXT}" stroke-width="1.5" stroke-linejoin="round"/>'
        f'<path d="M24,0 v12" stroke="#f2cc60" stroke-width="2" stroke-linecap="round"/>'
        f'<circle cx="24" cy="13" r="2.5" fill="#f2cc60"/>'
        f'</g>'
    )


def render_skills(cfg: dict) -> str:
    W = 900
    right_limit = 700           # espacio reservado a la derecha para la mascota
    y = 74
    body = [card_title("Lenguajes, frameworks y herramientas")]
    for group in cfg.get("skills", []):
        body.append(f'<text x="28" y="{y}" font-family="{FONT}" font-size="12" font-weight="700" '
                    f'fill="{MUTED}" letter-spacing="1">{escape(group["category"].upper())}</text>')
        y += 12
        x = 28
        for label, color in group["items"]:
            _, w = chip(0, 0, label, color)
            if x + w > right_limit:
                x = 28
                y += 38
            svg_chip, w = chip(x, y, label, color)
            body.append(svg_chip)
            x += w + 8
        y += 30 + 26
    H = y + 4
    body.insert(0, f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="14" fill="{CARD}" stroke="{BORDER}" stroke-width="3"/>')
    body.append(mascot_laptop(800, H - 60, .8))
    body.append(sparkle(740, 70, 7, GREEN_SOFT, .2) + plus(870, 60, 6, GREEN, .8) + sparkle(866, 120, 5, GREEN_SOFT, 1.1))
    return svg(W, H, "".join(body), "Stack tecnológico")


def render_experience(cfg: dict) -> str:
    W = 900
    text_right = 690
    y = 46
    entries = []
    for job in cfg.get("experience", []):
        lines = wrap(job["summary"], int((text_right - 64) / 7.3), 3)
        entries.append((job, lines, y))
        y += 24 + 20 + 20 * len(lines) + 22
    H = y - 6
    body = [
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="14" fill="{CARD}" stroke="{BORDER}" stroke-width="3"/>',
    ]
    if entries:
        body.append(f'<line x1="40" y1="{entries[0][2] - 6}" x2="40" y2="{entries[-1][2] + 6}" stroke="{BORDER}" stroke-width="3"/>')
    for job, lines, ey in entries:
        body.append(f'<circle cx="40" cy="{ey - 6}" r="7" fill="{GREEN}" stroke="{CARD}" stroke-width="3"/>')
        body.append(f'<text x="64" y="{ey}" font-family="{FONT}" font-size="16" font-weight="700" fill="{TEXT}">{escape(job["role"])}</text>')
        body.append(f'<text x="64" y="{ey + 21}" font-family="{FONT}" font-size="13.5" fill="{LINK}">{escape(job["company"])}'
                    f'<tspan fill="{MUTED}"> · {escape(job["period"])}</tspan></text>')
        ty = ey + 44
        for line in lines:
            body.append(f'<text x="64" y="{ty}" font-family="{FONT}" font-size="14" fill="{TEXT}">{escape(line)}</text>')
            ty += 20
    body.append(mascot_typing(800, H - 120, .6))
    body.append(sparkle(732, 40, 7, GREEN_SOFT, .4) + plus(872, 48, 6, GREEN, 1.0))
    return svg(W, H, "".join(body), "Experiencia profesional")


def render_education(cfg: dict) -> str:
    W = 900
    edu = cfg.get("education", {})
    honors = cfg.get("honors", [])
    body = []
    # columna izquierda: formación
    body.append(mortarboard(48, 50, 1.0))
    body.append(f'<text x="86" y="48" font-family="{FONT}" font-size="16" font-weight="700" fill="{TEXT}">{escape(edu.get("school", ""))}</text>')
    body.append(f'<text x="86" y="69" font-family="{FONT}" font-size="13.5" fill="{LINK}">{escape(edu.get("degree", ""))}'
                f'<tspan fill="{MUTED}"> · {escape(edu.get("date", ""))}</tspan></text>')
    ty = 96
    body.append(f'<text x="86" y="{ty}" font-family="{FONT}" font-size="13" font-weight="700" fill="{MUTED}">TESIS</text>')
    ty += 20
    for line in wrap(edu.get("thesis", ""), 52, 4):
        body.append(f'<text x="86" y="{ty}" font-family="{FONT}" font-size="13.5" fill="{TEXT}" font-style="italic">{escape(line)}</text>')
        ty += 19
    left_h = ty
    # columna derecha: logros
    hx, hy = 500, 48
    body.append(f'<text x="{hx}" y="{hy - 2}" font-family="{FONT}" font-size="13" font-weight="700" fill="{MUTED}">LOGROS</text>')
    hy += 22
    for h in honors:
        lines = wrap(h, 46, 2)
        body.append(trophy(hx + 8, hy - 5, .95))
        for i, line in enumerate(lines):
            body.append(f'<text x="{hx + 26}" y="{hy + i * 18}" font-family="{FONT}" font-size="13.5" fill="{TEXT}">{escape(line)}</text>')
        hy += 18 * len(lines) + 12
    H = max(left_h, hy) + 14
    body.insert(0, f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="14" fill="{CARD}" stroke="{BORDER}" stroke-width="3"/>')
    body.append(sparkle(470, 26, 6, "#f2cc60", .3) + sparkle(878, 26, 6, GREEN_SOFT, .9) + plus(866, 70, 5, GREEN, .5))
    return svg(W, H, "".join(body), "Formación y logros")

# ------------------------------------------------------------------ API ---
def token() -> str | None:
    return os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")


def http(url: str, data: dict | None = None) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-builder"}
    if token():
        headers["Authorization"] = f"Bearer {token()}"
    req = urllib.request.Request(url, headers=headers,
                                 data=json.dumps(data).encode() if data else None,
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch(cfg: dict) -> dict:
    user = cfg["username"]
    u = http(f"https://api.github.com/users/{user}")
    repos = {}
    for pin in cfg["pinned"]:
        try:
            r = http(f"https://api.github.com/repos/{user}/{pin['repo']}")
            repos[pin["repo"]] = {"stars": r["stargazers_count"], "forks": r["forks_count"],
                                  "language": r.get("language")}
        except urllib.error.HTTPError as e:
            print(f"  aviso: no pude leer {pin['repo']} ({e.code})", file=sys.stderr)
    data = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "user": {"followers": u["followers"], "following": u["following"],
                     "public_repos": u["public_repos"]},
            "repos": repos, "calendar": None}
    if token():
        q = """query($login:String!){ user(login:$login){ contributionsCollection{
              contributionCalendar{ totalContributions weeks{ contributionDays{
              date contributionCount contributionLevel }}}}}}"""
        try:
            g = http("https://api.github.com/graphql", {"query": q, "variables": {"login": user}})
            cal = g["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
            data["calendar"] = {
                "total": cal["totalContributions"],
                "weeks": [[{"date": d["date"], "count": d["contributionCount"],
                            "level": lv[d["contributionLevel"]]} for d in w["contributionDays"]]
                          for w in cal["weeks"]],
            }
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: calendario no disponible ({e})", file=sys.stderr)
    return data


def load_cache() -> dict | None:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def main() -> int:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    offline = "--offline" in sys.argv
    cache = load_cache()
    data = None
    if not offline:
        try:
            data = fetch(cfg)
            # conserva el calendario anterior si esta vez no se pudo obtener
            if data["calendar"] is None and cache and cache.get("calendar"):
                data["calendar"] = cache["calendar"]
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            print("datos obtenidos de la API de GitHub")
        except Exception as e:  # noqa: BLE001
            print(f"API no disponible ({e}); uso el caché", file=sys.stderr)
    if data is None:
        if not cache:
            print("no hay caché ni API: no puedo generar", file=sys.stderr)
            return 1
        data = cache

    os.makedirs(PINS, exist_ok=True)
    out = {
        os.path.join(ASSETS, "banner.svg"): render_banner(cfg),
        os.path.join(ASSETS, "stats.svg"): render_stats(data["user"]),
        os.path.join(ASSETS, "contributions.svg"): render_contributions(data.get("calendar")),
        os.path.join(ASSETS, "avatar.svg"): render_avatar(),
        os.path.join(ASSETS, "skills.svg"): render_skills(cfg),
        os.path.join(ASSETS, "experience.svg"): render_experience(cfg),
        os.path.join(ASSETS, "education.svg"): render_education(cfg),
    }
    for pin in cfg["pinned"]:
        slug = re.sub(r"[^a-z0-9]+", "-", pin["repo"].lower()).strip("-")
        out[os.path.join(PINS, f"{slug}.svg")] = render_pin(
            pin, data["repos"].get(pin["repo"], {}), cfg.get("language_overrides", {}))
    for path, content in out.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ->", os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
