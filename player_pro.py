# -*- coding: utf-8 -*-
"""
 UTMOST.FM PRO 2.0  Retro Futurista  ·  Modo Compositor / Studio
Version PRO: ademas del player local, vigila las carpetas de export/samples de
FL Studio y, al detectar un render nuevo, lo auto-carga, reproduce y analiza
(LUFS, true peak/clipping, balance espectral, estereo/fase). Permite exportar
una version normalizada.

La version estable (player.py) queda intacta. Esta usa su propio perfil de datos.
"""

import os
import sys
import io
import json
import math
import time
import random
import re
import queue
import threading
import ctypes

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter import font as tkfont

# ---- dependencias opcionales con fallback amable -----------------------------
try:
    import requests
except ImportError:
    print("ERROR: falta 'requests' -> pip install -r requirements.txt")
    sys.exit(1)

try:
    from PIL import Image, ImageTk, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    PYGAME_AVAILABLE = True
except Exception as e:
    print(f"ERROR: pygame no disponible: {e}")
    print("Instala con: pip install pygame")
    sys.exit(1)

try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3, APIC
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("AVISO: mutagen no disponible. Sin metadatos ni caratulas embebidas.")

try:
    import numpy as np
    import soundfile as sf
    AUDIO_FFT_AVAILABLE = True
except ImportError:
    AUDIO_FFT_AVAILABLE = False
    print("AVISO: numpy/soundfile no disponibles. Espectro sintetico (no reactivo).")

try:
    import pyloudnorm as pyln
    PYLOUDNORM_AVAILABLE = True
except ImportError:
    PYLOUDNORM_AVAILABLE = False
    # sin pyloudnorm el LUFS se estima por RMS (etiquetado 'approx')

# ==============================================================================
#   TRADUCCIONES
# ==============================================================================
LANGS = {
    'es': {
        'cfg_title':        ' CONFIGURACION ',
        'cfg_creds':        'BIBLIOTECA LOCAL',
        'cfg_folder':       'CARPETA DE MUSICA:',
        'cfg_browse':       '[ EXAMINAR ]',
        'cfg_name':         'TU NOMBRE / USUARIO:',
        'cfg_theme':        'TEMA',
        'cfg_lang':         'IDIOMA',
        'cfg_spectrum':     'ESPECTRO',
        'spectrum_compact': 'COMPACTO',
        'spectrum_large':   'GRANDE',
        'cfg_lyric_style':  'ESTILO DE LETRAS',
        'lyric_classic':    'CLASICO',
        'lyric_large':      'GRANDE',
        'cfg_art_style':    'ESTILO DE PORTADA',
        'art_normal':       'NORMAL',
        'art_crt':          'CRT / TV ANTIGUA',
        'cfg_auto_theme':   'TEMA SEGUN PORTADA',
        'auto_theme_on':    'AUTOMATICO',
        'auto_theme_off':   'MANUAL',
        'cfg_fl_title':     'FL STUDIO / COMPOSITOR',
        'cfg_fl_watch':     'VIGILAR FL STUDIO',
        'cfg_fl_export':    'CARPETA DE EXPORT (RENDERS):',
        'cfg_fl_samples':   'CARPETA DE SAMPLES:',
        'cfg_fl_autoplay':  'AUTO-REPRODUCIR RENDER',
        'cfg_fl_target':    'OBJETIVO LUFS:',
        'fl_on':            'ACTIVADO',
        'fl_off':           'DESACTIVADO',
        'studio_title':     '◉  ANALISIS STUDIO  ◉',
        'studio_lufs':      'LOUDNESS (LUFS)',
        'studio_peak':      'TRUE PEAK',
        'studio_clip':      'CLIPPING',
        'studio_balance':   'BALANCE ESPECTRAL',
        'studio_bass':      'GRAVES',
        'studio_mid':       'MEDIOS',
        'studio_treble':    'AGUDOS',
        'studio_stereo':    'ESTEREO / FASE',
        'studio_width':     'ANCHURA',
        'studio_corr':      'CORRELACION',
        'studio_export_opt':'[ EXPORTAR OPTIMIZADO ]',
        'studio_none':      'sin analisis todavia',
        'studio_analyzing': 'analizando render...',
        'studio_mono':      'mono',
        'v_ok':             'listo para streaming  ✓',
        'v_clip':           '⚠ clipping detectado',
        'v_phase':          '⚠ problema de fase (mono?)',
        'v_loud':           'demasiado alto vs objetivo',
        'v_quiet':          'bajo vs objetivo',
        'v_bright':         'demasiado brillante',
        'v_dark':           'demasiado oscuro',
        'fl_new_render':    '◉ render nuevo detectado',
        'fl_samples_added': 'samples nuevos: ',
        'cfg_save':         '[ GUARDAR Y APLICAR ]',
        'cfg_follow':       '[ SIGUEME EN MIS REDES ]',
        'cfg_scanning':     'escaneando carpeta...',
        'cfg_scanned':      'pistas encontradas: ',
        'theme_purple':     'MORADO',
        'theme_green':      'VERDE',
        'theme_orange':     'NARANJA',
        'theme_blue':       'AZUL',
        'theme_rose':       'ROSA',
        'theme_celeste':    'CELESTE',
        'theme_aqua':       'AQUA',
        'theme_red':        'ROJO',
        'theme_white':      'BLANCO',
        'theme_dark':       'NEGRO',
        'track':            'PISTA',
        'artist':           'ARTISTA',
        'album':            'ALBUM',
        'stopped':          '▼  detenido',
        'playing':          '▶  reproduciendo',
        'paused':           '▼  pausado',
        'spectrum':         'ESPECTRO',
        'vol':              '♪ VOL',
        'scroll_on':        'auto-scroll  █  activado',
        'scroll_off':       'auto-scroll  █  desactivado',
        'lyrics':           '♪  letras',
        'offline':          'desconectado',
        'online':           'en linea',
        'linking':          'cargando...',
        'error':            'sin pista',
        'no_track_radar':   'no hay pista',
        'connect_radar':    'biblioteca vacia\nselecciona una carpeta',
        'connect_lyric':    '█  carga musica\n   para ver letras',
        'search_lyric':     '⏳  buscando letra...',
        'no_lyric':         '♪  letra no disponible  ♪\n\n¡disfruta la musica!  █',
        'sync_ok':          '◉ sincronizado ✓',
        'sync_est':         '◉ estimado',
        'sync_none':        '◉ sin letra',
        'queue_title':      'SIGUIENTE  █',
        'queue_empty':      'sin canciones\nen la cola',
        'queue_offline':    'biblioteca vacia',
    },
    'en': {
        'cfg_title':        ' CONFIGURATION ',
        'cfg_creds':        'LOCAL LIBRARY',
        'cfg_folder':       'MUSIC FOLDER:',
        'cfg_browse':       '[ BROWSE ]',
        'cfg_name':         'YOUR NAME / USERNAME:',
        'cfg_theme':        'THEME',
        'cfg_lang':         'LANGUAGE',
        'cfg_spectrum':     'SPECTRUM',
        'spectrum_compact': 'COMPACT',
        'spectrum_large':   'LARGE',
        'cfg_lyric_style':  'LYRIC STYLE',
        'lyric_classic':    'CLASSIC',
        'lyric_large':      'LARGE',
        'cfg_art_style':    'ALBUM ART STYLE',
        'art_normal':       'NORMAL',
        'art_crt':          'CRT / OLD TV',
        'cfg_auto_theme':   'THEME FROM COVER',
        'auto_theme_on':    'AUTO',
        'auto_theme_off':   'MANUAL',
        'cfg_fl_title':     'FL STUDIO / COMPOSER',
        'cfg_fl_watch':     'WATCH FL STUDIO',
        'cfg_fl_export':    'EXPORT FOLDER (RENDERS):',
        'cfg_fl_samples':   'SAMPLES FOLDER:',
        'cfg_fl_autoplay':  'AUTO-PLAY RENDER',
        'cfg_fl_target':    'TARGET LUFS:',
        'fl_on':            'ON',
        'fl_off':           'OFF',
        'studio_title':     '◉  STUDIO ANALYSIS  ◉',
        'studio_lufs':      'LOUDNESS (LUFS)',
        'studio_peak':      'TRUE PEAK',
        'studio_clip':      'CLIPPING',
        'studio_balance':   'SPECTRAL BALANCE',
        'studio_bass':      'BASS',
        'studio_mid':       'MIDS',
        'studio_treble':    'TREBLE',
        'studio_stereo':    'STEREO / PHASE',
        'studio_width':     'WIDTH',
        'studio_corr':      'CORRELATION',
        'studio_export_opt':'[ EXPORT OPTIMIZED ]',
        'studio_none':      'no analysis yet',
        'studio_analyzing': 'analyzing render...',
        'studio_mono':      'mono',
        'v_ok':             'streaming ready  ✓',
        'v_clip':           '⚠ clipping detected',
        'v_phase':          '⚠ phase issue (mono?)',
        'v_loud':           'too loud vs target',
        'v_quiet':          'quiet vs target',
        'v_bright':         'too bright',
        'v_dark':           'too dark',
        'fl_new_render':    '◉ new render detected',
        'fl_samples_added': 'new samples: ',
        'cfg_save':         '[ SAVE & APPLY ]',
        'cfg_follow':       '[ FOLLOW MY SOCIALS ]',
        'cfg_scanning':     'scanning folder...',
        'cfg_scanned':      'tracks found: ',
        'theme_purple':     'PURPLE',
        'theme_green':      'GREEN',
        'theme_orange':     'ORANGE',
        'theme_blue':       'BLUE',
        'theme_rose':       'ROSE',
        'theme_celeste':    'CELESTE',
        'theme_aqua':       'AQUA',
        'theme_red':        'RED',
        'theme_white':      'WHITE',
        'theme_dark':       'DARK',
        'track':            'TRACK',
        'artist':           'ARTIST',
        'album':            'ALBUM',
        'stopped':          '▼  stopped',
        'playing':          '▶  playing',
        'paused':           '▼  paused',
        'spectrum':         'SPECTRUM',
        'vol':              '♪ VOL',
        'scroll_on':        'auto-scroll  █  on',
        'scroll_off':       'auto-scroll  █  off',
        'lyrics':           '♪  lyrics',
        'offline':          'offline',
        'online':           'online',
        'linking':          'loading...',
        'error':            'no track playing',
        'no_track_radar':   'no track playing',
        'connect_radar':    'empty library\nselect a folder',
        'connect_lyric':    '█  load music\n   to see lyrics',
        'search_lyric':     '⏳  searching lyrics...',
        'no_lyric':         '♪  lyrics not available  ♪\n\nenjoy the music!  █',
        'sync_ok':          '◉ sync ✓',
        'sync_est':         '◉ estimated',
        'sync_none':        '◉ no lyrics',
        'queue_title':      'UP NEXT  █',
        'queue_empty':      'no songs\nin queue',
        'queue_offline':    'empty library',
    },
}
CURRENT_LANG = 'es'


def _T(key):
    return LANGS.get(CURRENT_LANG, LANGS['es']).get(key, key)


# ==============================================================================
#   TEMAS (10) - extraidos del disassembly hex por hex
# ==============================================================================
THEMES = {
    'purple': {
        'name': 'PURPLE',
        'BG': '#0a0015', 'MANTLE': '#0f0020', 'CRUST': '#13002a',
        'SURFACE0': '#1e0040', 'SURFACE1': '#280055',
        'MAIN': '#cba6f7', 'MAIN_DIM': '#7c4fa0', 'MAIN_DK': '#3d1060', 'MAIN_GLW': '#a855f7',
        'SEC': '#b4befe', 'SEC_DIM': '#5a5a99',
        'ACCENT': '#e879f9', 'ACC_DIM': '#7a1a7a',
        'GRID': '#110028', 'SCANLINE': '#0a0015',
        'MATRIX1': '#a855f7', 'MATRIX2': '#3d1060',
    },
    'green': {
        'name': 'GREEN',
        'BG': '#000e06', 'MANTLE': '#001a0a', 'CRUST': '#002810',
        'SURFACE0': '#003d18', 'SURFACE1': '#005220',
        'MAIN': '#a3f7b5', 'MAIN_DIM': '#3a9955', 'MAIN_DK': '#1a4d2a', 'MAIN_GLW': '#22dd66',
        'SEC': '#c8ffd4', 'SEC_DIM': '#4a8855',
        'ACCENT': '#00ff99', 'ACC_DIM': '#006633',
        'GRID': '#001a08', 'SCANLINE': '#000e06',
        'MATRIX1': '#22dd66', 'MATRIX2': '#1a4d2a',
    },
    'orange': {
        'name': 'ORANGE',
        'BG': '#0f0800', 'MANTLE': '#1a0e00', 'CRUST': '#261500',
        'SURFACE0': '#3d2200', 'SURFACE1': '#522e00',
        'MAIN': '#ffb347', 'MAIN_DIM': '#a06020', 'MAIN_DK': '#5c3300', 'MAIN_GLW': '#ff8800',
        'SEC': '#ffd9a0', 'SEC_DIM': '#996633',
        'ACCENT': '#ff5500', 'ACC_DIM': '#7a2200',
        'GRID': '#1a0e00', 'SCANLINE': '#0f0800',
        'MATRIX1': '#ff8800', 'MATRIX2': '#5c3300',
    },
    'blue': {
        'name': 'BLUE',
        'BG': '#00050f', 'MANTLE': '#000d1a', 'CRUST': '#001226',
        'SURFACE0': '#001f40', 'SURFACE1': '#002855',
        'MAIN': '#89b4fa', 'MAIN_DIM': '#3a6aaa', 'MAIN_DK': '#1a3d66', 'MAIN_GLW': '#4488ff',
        'SEC': '#b9d1fa', 'SEC_DIM': '#4466aa',
        'ACCENT': '#00d4ff', 'ACC_DIM': '#005566',
        'GRID': '#000d1a', 'SCANLINE': '#00050f',
        'MATRIX1': '#4488ff', 'MATRIX2': '#1a3d66',
    },
    'rose': {
        'name': 'ROSE',
        'BG': '#0f0008', 'MANTLE': '#1a0010', 'CRUST': '#260018',
        'SURFACE0': '#3d0028', 'SURFACE1': '#520035',
        'MAIN': '#f7a8c4', 'MAIN_DIM': '#aa4470', 'MAIN_DK': '#660040', 'MAIN_GLW': '#ff4488',
        'SEC': '#ffd6e8', 'SEC_DIM': '#995566',
        'ACCENT': '#ff0066', 'ACC_DIM': '#7a0033',
        'GRID': '#1a0010', 'SCANLINE': '#0f0008',
        'MATRIX1': '#ff4488', 'MATRIX2': '#660040',
    },
    'celeste': {
        'name': 'CELESTE',
        'BG': '#000a14', 'MANTLE': '#001122', 'CRUST': '#001a33',
        'SURFACE0': '#00274d', 'SURFACE1': '#003566',
        'MAIN': '#8be9fd', 'MAIN_DIM': '#5ab0c2', 'MAIN_DK': '#2d6978', 'MAIN_GLW': '#66d9ff',
        'SEC': '#cceeff', 'SEC_DIM': '#80cce6',
        'ACCENT': '#00bfff', 'ACC_DIM': '#0080b3',
        'GRID': '#001428', 'SCANLINE': '#000a14',
        'MATRIX1': '#8be9fd', 'MATRIX2': '#2d6978',
    },
    'aqua': {
        'name': 'AQUA',
        'BG': '#000a08', 'MANTLE': '#001411', 'CRUST': '#00211c',
        'SURFACE0': '#00332b', 'SURFACE1': '#00473c',
        'MAIN': '#a3f7eb', 'MAIN_DIM': '#54b3a4', 'MAIN_DK': '#2a665d', 'MAIN_GLW': '#33ffdb',
        'SEC': '#b3fff0', 'SEC_DIM': '#4dccb6',
        'ACCENT': '#00e6bc', 'ACC_DIM': '#008068',
        'GRID': '#001411', 'SCANLINE': '#000a08',
        'MATRIX1': '#a3f7eb', 'MATRIX2': '#2a665d',
    },
    'red': {
        'name': 'RED',
        'BG': '#0d0000', 'MANTLE': '#1a0000', 'CRUST': '#260000',
        'SURFACE0': '#400000', 'SURFACE1': '#590000',
        'MAIN': '#ff8080', 'MAIN_DIM': '#b33939', 'MAIN_DK': '#661414', 'MAIN_GLW': '#ff3333',
        'SEC': '#ffb3b3', 'SEC_DIM': '#cc6666',
        'ACCENT': '#ff0000', 'ACC_DIM': '#990000',
        'GRID': '#1a0000', 'SCANLINE': '#0d0000',
        'MATRIX1': '#ff8080', 'MATRIX2': '#661414',
    },
    'white': {
        'name': 'WHITE',
        'BG': '#050505', 'MANTLE': '#0d0d0d', 'CRUST': '#141414',
        'SURFACE0': '#242424', 'SURFACE1': '#333333',
        'MAIN': '#e6e6e6', 'MAIN_DIM': '#a6a6a6', 'MAIN_DK': '#595959', 'MAIN_GLW': '#ffffff',
        'SEC': '#f2f2f2', 'SEC_DIM': '#8c8c8c',
        'ACCENT': '#cccccc', 'ACC_DIM': '#666666',
        'GRID': '#0d0d0d', 'SCANLINE': '#050505',
        'MATRIX1': '#e6e6e6', 'MATRIX2': '#595959',
    },
    'dark': {
        'name': 'DARK',
        'BG': '#000000', 'MANTLE': '#050505', 'CRUST': '#0a0a0a',
        'SURFACE0': '#141414', 'SURFACE1': '#1f1f1f',
        'MAIN': '#999999', 'MAIN_DIM': '#666666', 'MAIN_DK': '#333333', 'MAIN_GLW': '#b3b3b3',
        'SEC': '#777777', 'SEC_DIM': '#444444',
        'ACCENT': '#888888', 'ACC_DIM': '#444444',
        'GRID': '#050505', 'SCANLINE': '#000000',
        'MATRIX1': '#999999', 'MATRIX2': '#333333',
    },
}

T = THEMES['purple'].copy()


def apply_theme(name):
    global T
    if name in THEMES:
        T = THEMES[name].copy()


def BG():        return T['BG']
def MANTLE():    return T['MANTLE']
def CRUST():     return T['CRUST']
def SURFACE0():  return T['SURFACE0']
def SURFACE1():  return T['SURFACE1']
def MAIN():      return T['MAIN']
def MAIN_DIM():  return T['MAIN_DIM']
def MAIN_DK():   return T['MAIN_DK']
def MAIN_GLW():  return T['MAIN_GLW']
def SEC():       return T['SEC']
def SEC_DIM():   return T['SEC_DIM']
def ACCENT():    return T['ACCENT']
def ACC_DIM():   return T['ACC_DIM']

# constantes fijas (no por tema)
SUBTEXT  = '#a6adc8'
MUTED    = '#585b70'
OVERLAY  = '#313244'
PINK_ERR = '#f38ba8'


def LYR_ACTIVE():  return MAIN_GLW()
def LYR_NEAR1():   return MAIN()
def LYR_NEAR2():   return SEC()
def LYR_NORMAL():  return MUTED


# ==============================================================================
#   ALMACENAMIENTO
# ==============================================================================
try:
    # perfil PROPIO de la version PRO (no pisa la config del player normal)
    APP_DATA_DIR = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~'), 'UtmostFM_PRO')
    os.makedirs(APP_DATA_DIR, exist_ok=True)
except Exception:
    APP_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Migracion suave: si existe la config del player normal, la usamos de base inicial
_BASE_CREDS = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~'),
                           'UtmostFM', '.utmostfm_local')
CREDS_FILE = os.path.join(APP_DATA_DIR, '.utmostfm_pro')
if not os.path.exists(CREDS_FILE) and os.path.exists(_BASE_CREDS):
    try:
        import shutil
        shutil.copy(_BASE_CREDS, CREDS_FILE)
    except Exception:
        pass
ART_CACHE_DIR = os.path.join(APP_DATA_DIR, 'artcache')
os.makedirs(ART_CACHE_DIR, exist_ok=True)
# carpeta donde se escriben los renders "optimizados"
OPT_OUT_DIR = os.path.join(APP_DATA_DIR, 'optimized')
os.makedirs(OPT_OUT_DIR, exist_ok=True)


def open_tiktok(event=None):
    """Abre el linktree con todas las redes."""
    import webbrowser
    try:
        webbrowser.open('https://linktr.ee/bri_serrubz')
    except Exception:
        pass


def save_credentials(music_folder, username='User', theme='purple', lang='es',
                     spectrum_mode='compact', lyric_style='classic',
                     art_style='normal', auto_theme=False, fl=None):
    try:
        data = {
            'music_folder': music_folder,
            'username': username,
            'theme': theme,
            'lang': lang,
            'spectrum_mode': spectrum_mode,
            'lyric_style': lyric_style,
            'art_style': art_style,
            'auto_theme': bool(auto_theme),
            'fl': fl or {},   # config FL Studio (PRO)
        }
        with open(CREDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_credentials():
    try:
        with open(CREDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def lerp(a, b, t):
    return a + (b - a) * t


# ==============================================================================
#   PARSEO DE LETRAS .LRC + LRCLIB
# ==============================================================================
_LRC_LINE_RE = re.compile(r'\[(\d+):(\d+)(?:\.(\d+))?\](.*)')


def parse_lrc(lrc_text):
    lines = []
    for raw in (lrc_text or '').splitlines():
        m = _LRC_LINE_RE.match(raw.strip())
        if not m:
            continue
        mm, ss, fr, txt = m.groups()
        ms = int(mm) * 60_000 + int(ss) * 1000
        if fr:
            ms += int(fr[:3].ljust(3, '0'))
        txt = txt.strip()
        if txt:
            lines.append({'time': ms, 'text': txt})
    lines.sort(key=lambda x: x['time'])
    return lines


LRCLIB_HEADERS = {
    'User-Agent': 'UtmostFM 2.0 Local (https://linktr.ee/bri_serrubz)'
}


def _lrclib_request(url, params, timeout=12, retries=2):
    """GET robusto contra LRCLIB: User-Agent, timeout amplio y reintentos.
    Devuelve el JSON decodificado, o None si 404 / fallo definitivo."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params,
                             headers=LRCLIB_HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None  # no existe: no tiene sentido reintentar
            # otros codigos (5xx, 429...) -> reintentar
        except requests.RequestException as e:
            last_exc = e
        if attempt < retries:
            time.sleep(0.8)
    if last_exc:
        print('[lrclib]', type(last_exc).__name__, last_exc)
    return None


def fetch_lrclib(artist, title, duration_s=None):
    """Busca letras en LRCLIB en cascada:
    1) /api/get con duracion exacta  2) /api/get sin duracion  3) /api/search (mejor match)."""
    # 1) match exacto con duracion
    if duration_s:
        data = _lrclib_request('https://lrclib.net/api/get', {
            'artist_name': artist, 'track_name': title, 'duration': int(duration_s),
        })
        if data:
            return {'synced': data.get('syncedLyrics') or '',
                    'plain':  data.get('plainLyrics')  or ''}
    # 2) sin duracion (mas tolerante)
    data = _lrclib_request('https://lrclib.net/api/get', {
        'artist_name': artist, 'track_name': title,
    })
    if data:
        return {'synced': data.get('syncedLyrics') or '',
                'plain':  data.get('plainLyrics')  or ''}
    # 3) busqueda libre: priorizar resultado CON letra sincronizada
    arr = _lrclib_request('https://lrclib.net/api/search', {
        'track_name': title, 'artist_name': artist,
    })
    if isinstance(arr, list) and arr:
        best = next((e for e in arr if e.get('syncedLyrics')), None) or arr[0]
        return {'synced': best.get('syncedLyrics') or '',
                'plain':  best.get('plainLyrics')  or ''}
    return None


def fetch_plain_fallback(artist, title):
    """Ultimo recurso: busqueda libre con query combinada."""
    arr = _lrclib_request('https://lrclib.net/api/search', {'q': f'{artist} {title}'})
    if isinstance(arr, list) and arr:
        best = next((e for e in arr if e.get('syncedLyrics') or e.get('plainLyrics')), None)
        if best:
            txt = best.get('plainLyrics') or best.get('syncedLyrics') or ''
            return txt if txt.strip() else None
    return None


# ==============================================================================
#   MOTOR DE AUDIO LOCAL (sustituye Spotify)
# ==============================================================================
AUDIO_EXTS = {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus', '.wma'}


def _extract_metadata(path):
    info = {
        'path': path,
        'title': os.path.splitext(os.path.basename(path))[0],
        'artist': 'Unknown',
        'album': 'Unknown',
        'duration_ms': 0,
        'art_bytes': None,
    }
    if not MUTAGEN_AVAILABLE:
        return info
    try:
        mf = MutagenFile(path)
        if mf is None:
            return info
        # duracion
        try:
            info['duration_ms'] = int(mf.info.length * 1000)
        except Exception:
            pass
        # tags
        def _t(*keys):
            for k in keys:
                v = mf.tags.get(k) if mf.tags else None
                if v:
                    if isinstance(v, list):
                        v = v[0]
                    return str(v).strip()
            return None
        title  = _t('TIT2', 'title', '\xa9nam')
        artist = _t('TPE1', 'artist', '\xa9ART')
        album  = _t('TALB', 'album', '\xa9alb')
        if title:  info['title']  = title
        if artist: info['artist'] = artist
        if album:  info['album']  = album
        # caratula embebida
        art = None
        if hasattr(mf, 'tags') and mf.tags is not None:
            # MP3 (ID3)
            for k in list(mf.tags.keys()):
                if k.startswith('APIC'):
                    art = mf.tags[k].data
                    break
            # FLAC
            if art is None and hasattr(mf, 'pictures') and mf.pictures:
                art = mf.pictures[0].data
            # MP4 / M4A
            if art is None:
                covr = mf.tags.get('covr') if hasattr(mf.tags, 'get') else None
                if covr:
                    art = bytes(covr[0])
        info['art_bytes'] = art
    except Exception:
        pass
    return info


# Matiz (hue, en grados) representativo de cada tema, derivado de su MAIN_GLW.
THEME_HUES = {
    'red':     0.0,
    'orange':  32.0,
    'green':   140.0,
    'aqua':    168.0,
    'celeste': 198.0,
    'blue':    220.0,
    'purple':  271.0,
    'rose':    340.0,
}


def _theme_for_hue(deg):
    """Devuelve el tema cuyo matiz esta mas cerca (distancia circular) del dado."""
    best, bestd = 'purple', 1e9
    for name, h in THEME_HUES.items():
        d = abs((deg - h + 180.0) % 360.0 - 180.0)
        if d < bestd:
            bestd, best = d, name
    return best


def pick_theme_for_image(img):
    """Analiza la portada y devuelve el nombre del tema que mejor combina, o None.
    - Si la imagen es practicamente gris -> 'white' (clara) o 'dark' (oscura).
    - Si tiene color -> matiz medio (circular, ponderado por saturacion) -> tema mas cercano."""
    if not PIL_AVAILABLE:
        return None
    try:
        small = img.convert('RGB').resize((48, 48))
    except Exception:
        return None

    if AUDIO_FFT_AVAILABLE:
        arr = np.asarray(small, dtype=np.float32) / 255.0
        r = arr[..., 0]; g = arr[..., 1]; b = arr[..., 2]
        mx = np.maximum(np.maximum(r, g), b)
        mn = np.minimum(np.minimum(r, g), b)
        diff = mx - mn
        val = mx
        sat = np.where(mx > 1e-6, diff / np.maximum(mx, 1e-6), 0.0)
        d_safe = np.maximum(diff, 1e-6)
        hue = np.zeros_like(mx)
        rm = (mx == r) & (diff > 1e-6)
        gm = (mx == g) & (diff > 1e-6) & ~rm
        bm = (mx == b) & (diff > 1e-6) & ~rm & ~gm
        hue[rm] = ((g[rm] - b[rm]) / d_safe[rm]) % 6.0
        hue[gm] = ((b[gm] - r[gm]) / d_safe[gm]) + 2.0
        hue[bm] = ((r[bm] - g[bm]) / d_safe[bm]) + 4.0
        hue = (hue / 6.0) % 1.0
        mask = (val > 0.15) & (val < 0.97) & (sat > 0.22)
        if int(mask.sum()) < 20:
            return 'white' if float(val.mean()) > 0.45 else 'dark'
        h = hue[mask]; s = sat[mask]
        ang = h * 2.0 * math.pi
        sx = float(np.sum(s * np.cos(ang)))
        sy = float(np.sum(s * np.sin(ang)))
        avg_hue = (math.atan2(sy, sx) / (2.0 * math.pi)) % 1.0
        return _theme_for_hue(avg_hue * 360.0)

    # fallback pure-python
    import colorsys
    px = list(small.getdata())
    sx = sy = 0.0; n = 0; vsum = 0.0
    for (r, g, b) in px:
        hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        vsum += vv
        if 0.15 < vv < 0.97 and ss > 0.22:
            ang = hh * 2.0 * math.pi
            sx += ss * math.cos(ang); sy += ss * math.sin(ang); n += 1
    if n < 20:
        return 'white' if (vsum / max(1, len(px))) > 0.45 else 'dark'
    avg_hue = (math.atan2(sy, sx) / (2.0 * math.pi)) % 1.0
    return _theme_for_hue(avg_hue * 360.0)


def _apply_crt_filter(img):
    """Aplica efecto CRT/TV antigua: scanlines + saturacion realzada + viñeta + aberracion cromatica.
    img: PIL.Image RGB. Devuelve PIL.Image RGB."""
    if not PIL_AVAILABLE:
        return img
    # 1. Boost de contraste y saturacion (look fosforo)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.35)
    img = ImageEnhance.Brightness(img).enhance(0.92)

    if AUDIO_FFT_AVAILABLE:  # numpy disponible
        arr = np.array(img, dtype=np.float32)
        h, w, _ = arr.shape
        # 2. Scanlines: cada fila par se oscurece
        arr[::2] *= 0.55
        # 3. Aberracion cromatica leve: desplazar canal R 1px izq, B 1px der
        r_shift = np.roll(arr[..., 0], -1, axis=1)
        b_shift = np.roll(arr[..., 2],  1, axis=1)
        arr[..., 0] = r_shift
        arr[..., 2] = b_shift
        # 4. Vignette radial
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2, h / 2
        d2 = ((xx - cx) / (w / 2)) ** 2 + ((yy - cy) / (h / 2)) ** 2
        vignette = np.clip(1.0 - d2 * 0.45, 0.35, 1.0)
        arr *= vignette[..., None]
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)
    else:
        # fallback pure-PIL: solo scanlines
        from PIL import ImageDraw
        overlay = img.copy()
        draw = ImageDraw.Draw(overlay)
        w, h = img.size
        for y in range(0, h, 2):
            draw.line([(0, y), (w, y)], fill=(0, 0, 0))
        return Image.blend(img, overlay, 0.45)


# ==============================================================================
#   FUENTE ASCII 5x5 PARA RENDERIZAR LA HORA COMO ARTE EN BLOQUES
# ==============================================================================
ASCII_FONT_5x5 = {
    'A': [' ██ ', '█  █', '████', '█  █', '█  █'],
    'B': ['███ ', '█  █', '███ ', '█  █', '███ '],
    'C': [' ███', '█   ', '█   ', '█   ', ' ███'],
    'D': ['███ ', '█  █', '█  █', '█  █', '███ '],
    'E': ['████', '█   ', '███ ', '█   ', '████'],
    'F': ['████', '█   ', '███ ', '█   ', '█   '],
    'G': [' ███', '█   ', '█ ██', '█  █', ' ███'],
    'H': ['█  █', '█  █', '████', '█  █', '█  █'],
    'I': ['███', ' █ ', ' █ ', ' █ ', '███'],
    'J': ['████', '   █', '   █', '█  █', ' ██ '],
    'K': ['█  █', '█ █ ', '██  ', '█ █ ', '█  █'],
    'L': ['█   ', '█   ', '█   ', '█   ', '████'],
    'M': ['█   █', '██ ██', '█ █ █', '█   █', '█   █'],
    'N': ['█   █', '██  █', '█ █ █', '█  ██', '█   █'],
    'O': [' ██ ', '█  █', '█  █', '█  █', ' ██ '],
    'P': ['███ ', '█  █', '███ ', '█   ', '█   '],
    'Q': [' ██ ', '█  █', '█  █', '█ ██', ' ███'],
    'R': ['███ ', '█  █', '███ ', '█ █ ', '█  █'],
    'S': [' ███', '█   ', ' ██ ', '   █', '███ '],
    'T': ['████', ' █  ', ' █  ', ' █  ', ' █  '],
    'U': ['█  █', '█  █', '█  █', '█  █', ' ██ '],
    'V': ['█   █', '█   █', '█   █', ' █ █ ', '  █  '],
    'W': ['█   █', '█   █', '█ █ █', '██ ██', '█   █'],
    'X': ['█   █', ' █ █ ', '  █  ', ' █ █ ', '█   █'],
    'Y': ['█   █', ' █ █ ', '  █  ', '  █  ', '  █  '],
    'Z': ['█████', '   █ ', '  █  ', ' █   ', '█████'],
    '0': [' ██ ', '█  █', '█  █', '█  █', ' ██ '],
    '1': [' █ ', '██ ', ' █ ', ' █ ', '███'],
    '2': [' ██ ', '█  █', '  █ ', ' █  ', '████'],
    '3': ['███ ', '   █', ' ██ ', '   █', '███ '],
    '4': ['█  █', '█  █', '████', '   █', '   █'],
    '5': ['████', '█   ', '███ ', '   █', '███ '],
    '6': [' ███', '█   ', '███ ', '█  █', ' ██ '],
    '7': ['████', '   █', '  █ ', ' █  ', '█   '],
    '8': [' ██ ', '█  █', ' ██ ', '█  █', ' ██ '],
    '9': [' ██ ', '█  █', ' ███', '   █', '███ '],
    ' ': ['  ',  '  ',  '  ',  '  ',  '  '],
    '_': ['    ', '    ', '    ', '    ', '████'],
    '-': ['    ', '    ', '████', '    ', '    '],
    '.': ['  ', '  ', '  ', '  ', '██'],
    ':': [' ', '█', ' ', '█', ' '],
}


def render_name_block(name, max_chars=8):
    """Renderiza el nombre del usuario como arte ASCII de 5 lineas usando bloques █."""
    name = (name or 'USER').upper()[:max_chars]
    fallback = ASCII_FONT_5x5[' ']
    rows = ['', '', '', '', '']
    for ch in name:
        glyph = ASCII_FONT_5x5.get(ch, fallback)
        for i in range(5):
            rows[i] += glyph[i] + ' '
    return '\n'.join(rows)


def _compute_spectrum_frames(path, n_bands=48, fps=30):
    """Lee el archivo entero y precomputa el espectro frame-por-frame.
    Devuelve (frames[n_frames, n_bands], fps) con valores 0..1, o (None, fps) si falla."""
    if not AUDIO_FFT_AVAILABLE:
        return None, fps
    try:
        data, sr = sf.read(path, dtype='float32', always_2d=True)
    except Exception as e:
        print(f'[fft] no se pudo leer {os.path.basename(path)}: {e}')
        return None, fps
    if data.size == 0:
        return None, fps
    mono = data.mean(axis=1)
    # downsample a 22050 para ahorrar trabajo
    target_sr = 22050
    if sr > target_sr:
        step = max(1, sr // target_sr)
        mono = mono[::step]
        sr = sr // step
    chunk = max(1, sr // fps)
    fft_size = 1024
    n_frames = max(0, (len(mono) - fft_size) // chunk + 1)
    if n_frames < 2:
        return None, fps
    # binning log-frecuencia 40Hz..sr/2
    freq_min, freq_max = 40.0, sr / 2.0
    edges = np.logspace(np.log10(freq_min), np.log10(freq_max), n_bands + 1)
    bin_lo = np.clip((edges[:-1] / sr * fft_size).astype(int), 1, fft_size // 2 - 1)
    bin_hi = np.clip((edges[1:]  / sr * fft_size).astype(int), 1, fft_size // 2 - 1)
    bin_hi = np.maximum(bin_hi, bin_lo + 1)
    window = np.hanning(fft_size).astype(np.float32)
    frames = np.zeros((n_frames, n_bands), dtype=np.float32)
    for f in range(n_frames):
        start = f * chunk
        block = mono[start:start + fft_size]
        if len(block) < fft_size:
            block = np.pad(block, (0, fft_size - len(block)))
        spec = np.abs(np.fft.rfft(block * window))
        for b in range(n_bands):
            frames[f, b] = spec[bin_lo[b]:bin_hi[b]].mean()
    # normalizacion + curva log perceptual
    mx = frames.max()
    if mx > 0:
        frames /= mx
    frames = np.log10(frames * 9.0 + 1.0).astype(np.float32)  # 0..1
    return frames, fps


# ==============================================================================
#   MOTOR DE ANALISIS DE AUDIO (modo Studio / compositor)
# ==============================================================================
def _db(x):
    """Lineal -> dB con piso para evitar log(0)."""
    return 20.0 * math.log10(max(float(x), 1e-9))


def _approx_lufs(mono):
    """Estimacion de loudness por RMS (cuando no hay pyloudnorm).
    No es BS.1770 real; sirve de referencia relativa. Devuelve dB aprox."""
    rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
    # offset empirico para acercar el RMS a una escala tipo LUFS
    return _db(rms) - 3.0


def _true_peak_db(data):
    """True peak aprox por sobremuestreo lineal 4x (sin scipy)."""
    if data.ndim == 1:
        chans = [data]
    else:
        chans = [data[:, c] for c in range(data.shape[1])]
    peak = 0.0
    for ch in chans:
        if ch.size < 2:
            peak = max(peak, float(np.max(np.abs(ch))) if ch.size else 0.0)
            continue
        # interpolar 4x
        x = np.arange(ch.size, dtype=np.float32)
        xi = np.linspace(0, ch.size - 1, ch.size * 4)
        up = np.interp(xi, x, ch)
        peak = max(peak, float(np.max(np.abs(up))))
    return _db(peak)


def analyze_audio(path, target_lufs=-14.0):
    """Analiza un archivo de audio y devuelve metricas de mastering.
    Corre offline (pensado para hilo de fondo). Devuelve dict o None si falla."""
    if not AUDIO_FFT_AVAILABLE:
        return None
    try:
        data, sr = sf.read(path, dtype='float32', always_2d=True)
    except Exception as e:
        print(f'[analyze] no se pudo leer {os.path.basename(path)}: {e}')
        return None
    if data.size == 0:
        return None
    n_ch = data.shape[1]
    mono = data.mean(axis=1)
    duration = data.shape[0] / float(sr)

    # ---- LUFS integrado ----
    lufs_approx = False
    lufs = None
    if PYLOUDNORM_AVAILABLE:
        try:
            meter = pyln.Meter(sr)
            lufs = float(meter.integrated_loudness(data if n_ch > 1 else mono))
        except Exception:
            lufs = None
    if lufs is None or not math.isfinite(lufs):
        lufs = _approx_lufs(mono)
        lufs_approx = True

    # ---- pico de muestra, true peak, clipping ----
    sample_peak_db = _db(float(np.max(np.abs(data))))
    true_peak_db = _true_peak_db(data)
    clip_count = int(np.count_nonzero(np.abs(data) >= 0.999))
    clipping = clip_count > 0

    # ---- balance espectral (graves/medios/agudos) ----
    fft_size = 4096
    if mono.size >= fft_size:
        # promediar magnitud sobre varios bloques repartidos
        n_blocks = min(40, max(1, mono.size // fft_size))
        idxs = np.linspace(0, mono.size - fft_size, n_blocks).astype(int)
        window = np.hanning(fft_size).astype(np.float32)
        acc = np.zeros(fft_size // 2 + 1, dtype=np.float64)
        for st in idxs:
            block = mono[st:st + fft_size] * window
            acc += np.abs(np.fft.rfft(block)) ** 2
        acc /= len(idxs)
        freqs = np.fft.rfftfreq(fft_size, 1.0 / sr)
        bass = float(acc[(freqs >= 20) & (freqs < 250)].sum())
        mid = float(acc[(freqs >= 250) & (freqs < 4000)].sum())
        treble = float(acc[(freqs >= 4000) & (freqs < 20000)].sum())
        total = bass + mid + treble
        if total <= 0:
            total = 1.0
        balance = {'bass': bass / total, 'mid': mid / total, 'treble': treble / total}
    else:
        balance = {'bass': 0.34, 'mid': 0.40, 'treble': 0.26}

    # veredicto de brillo segun proporcion agudos vs graves
    if balance['treble'] > balance['bass'] * 1.6:
        spectral_verdict = 'bright'
    elif balance['bass'] > balance['treble'] * 2.2:
        spectral_verdict = 'dark'
    else:
        spectral_verdict = 'balanced'

    # ---- estereo: correlacion de fase + anchura ----
    if n_ch >= 2:
        L = data[:, 0]; R = data[:, 1]
        denom = float(np.sqrt(np.sum(L * L) * np.sum(R * R)))
        corr = float(np.sum(L * R) / denom) if denom > 1e-9 else 1.0
        mid_e = float(np.sum(((L + R) * 0.5) ** 2))
        side_e = float(np.sum(((L - R) * 0.5) ** 2))
        width = (side_e / (mid_e + 1e-9)) if mid_e > 0 else 0.0
        is_mono = corr > 0.999
    else:
        corr = 1.0
        width = 0.0
        is_mono = True

    # ---- veredicto global ----
    if clipping:
        verdict = 'clip'
    elif corr < -0.1:
        verdict = 'phase'
    elif lufs > target_lufs + 2.0:
        verdict = 'loud'
    elif lufs < target_lufs - 4.0:
        verdict = 'quiet'
    elif spectral_verdict != 'balanced':
        verdict = spectral_verdict
    else:
        verdict = 'ok'

    return {
        'path': path,
        'duration': duration,
        'sample_rate': sr,
        'channels': n_ch,
        'lufs': lufs,
        'lufs_approx': lufs_approx,
        'target_lufs': target_lufs,
        'sample_peak_db': sample_peak_db,
        'true_peak_db': true_peak_db,
        'clipping': clipping,
        'clip_count': clip_count,
        'balance': balance,
        'spectral_verdict': spectral_verdict,
        'stereo_corr': corr,
        'stereo_width': width,
        'is_mono': is_mono,
        'verdict': verdict,
    }


def normalize_export(path, target_lufs=-14.0, ceiling_db=-1.0, out_dir=None, out_format=None):
    """Genera una copia normalizada al LUFS objetivo con techo de pico.
    Devuelve la ruta de salida o None si falla."""
    if not AUDIO_FFT_AVAILABLE:
        return None
    try:
        data, sr = sf.read(path, dtype='float32', always_2d=True)
    except Exception as e:
        print(f'[normalize] no se pudo leer: {e}')
        return None
    if data.size == 0:
        return None

    # ganancia para alcanzar el objetivo
    if PYLOUDNORM_AVAILABLE:
        try:
            meter = pyln.Meter(sr)
            cur = meter.integrated_loudness(data)
            gain_db = target_lufs - cur
        except Exception:
            gain_db = target_lufs - _approx_lufs(data.mean(axis=1))
    else:
        gain_db = target_lufs - _approx_lufs(data.mean(axis=1))

    gain = 10.0 ** (gain_db / 20.0)
    out = data * gain

    # techo de pico (limitador duro suave): si excede el ceiling, bajar todo
    ceiling = 10.0 ** (ceiling_db / 20.0)
    peak = float(np.max(np.abs(out)))
    if peak > ceiling and peak > 0:
        out *= (ceiling / peak)
    out = np.clip(out, -1.0, 1.0)

    out_dir = out_dir or OPT_OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    ext = (out_format or os.path.splitext(path)[1].lstrip('.') or 'wav').lower()
    if ext not in ('wav', 'flac', 'ogg'):
        ext = 'wav'  # formatos que soundfile escribe sin libs extra
    out_path = os.path.join(out_dir, f'{base}__opt_{int(abs(target_lufs))}LUFS.{ext}')
    try:
        sf.write(out_path, out, sr)
        return out_path
    except Exception as e:
        print(f'[normalize] no se pudo escribir: {e}')
        return None


class LocalAudioEngine:
    """Motor de reproduccion local. API parecida a Spotify (get_state)."""

    def __init__(self):
        self.tracks = []          # lista de metadatos
        self.queue_order = []     # indices en self.tracks
        self.current_idx = -1
        self.is_playing = False
        self.is_paused = False
        self.volume = 70          # 0-100
        self._duration_ms = 0
        self._start_wall = 0.0    # time.time() al iniciar play
        self._pause_offset_ms = 0 # acumulado de pos al pausar
        self.shuffle = False
        self.loop = 0             # 0=no, 1=playlist, 2=track
        self._lock = threading.Lock()
        pygame.mixer.music.set_volume(self.volume / 100.0)

    # ----- biblioteca -----
    def scan_folder(self, folder, progress_cb=None):
        if not folder or not os.path.isdir(folder):
            return 0
        # recordar la pista que esta sonando para preservarla tras el re-escaneo
        playing_path = None
        cur = self.current_track()
        if cur:
            playing_path = cur['path']

        found = []
        for root, dirs, files in os.walk(folder):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in AUDIO_EXTS:
                    found.append(os.path.join(root, fn))

        # construir listas nuevas en locales (no tocar el estado en vivo hasta el final)
        new_tracks = []
        for i, path in enumerate(found):
            new_tracks.append(_extract_metadata(path))
            if progress_cb:
                try: progress_cb(i + 1, len(found))
                except Exception: pass
        new_order = list(range(len(new_tracks)))
        if self.shuffle:
            random.shuffle(new_order)

        # localizar la pista que estaba sonando en el nuevo orden
        new_idx = -1
        if playing_path:
            for qpos, tidx in enumerate(new_order):
                if new_tracks[tidx]['path'] == playing_path:
                    new_idx = qpos
                    break

        # swap atomico del estado bajo lock para no romper a los lectores (poll / anim)
        with self._lock:
            self.tracks = new_tracks
            self.queue_order = new_order
            if new_idx >= 0:
                # la pista sonando sigue existiendo: conservar su posicion (persistencia)
                self.current_idx = new_idx
            elif playing_path is not None:
                # la pista sonando ya no esta en la carpeta: no perder la reproduccion actual,
                # pero apuntar al inicio para futuros next/prev
                self.current_idx = 0 if new_tracks else -1
            else:
                # no habia nada sonando
                if self.current_idx >= len(new_order):
                    self.current_idx = -1
        return len(new_tracks)

    def add_folder(self, folder, progress_cb=None):
        """Fusiona audios de una carpeta en la biblioteca actual sin borrar la cola."""
        if not folder or not os.path.isdir(folder):
            return 0
        with self._lock:
            known = {
                os.path.normcase(os.path.abspath(t.get('path', '')))
                for t in self.tracks
            }

        found = []
        for root, dirs, files in os.walk(folder):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in AUDIO_EXTS:
                    path = os.path.abspath(os.path.join(root, fn))
                    if os.path.normcase(path) not in known:
                        found.append(path)

        metas = []
        for i, path in enumerate(found):
            metas.append(_extract_metadata(path))
            if progress_cb:
                try: progress_cb(i + 1, len(found))
                except Exception: pass

        added = 0
        with self._lock:
            known = {
                os.path.normcase(os.path.abspath(t.get('path', '')))
                for t in self.tracks
            }
            for meta in metas:
                path_key = os.path.normcase(os.path.abspath(meta.get('path', '')))
                if path_key in known:
                    continue
                self.tracks.append(meta)
                self.queue_order.append(len(self.tracks) - 1)
                known.add(path_key)
                added += 1
            if self.current_idx < 0 and self.queue_order:
                self.current_idx = 0
        return added

    # ----- control -----
    def play(self, qpos=None):
        if not self.tracks:
            return
        if qpos is None:
            qpos = self.current_idx if self.current_idx >= 0 else 0
        qpos = max(0, min(qpos, len(self.queue_order) - 1))
        self.current_idx = qpos
        idx = self.queue_order[qpos]
        track = self.tracks[idx]
        try:
            pygame.mixer.music.load(track['path'])
            pygame.mixer.music.set_volume(self.volume / 100.0)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self._duration_ms = track['duration_ms'] or 0
            self._start_wall = time.time()
            self._pause_offset_ms = 0
        except Exception as e:
            print(f"[audio] no se pudo cargar {track['path']}: {e}")
            self.is_playing = False

    def load_external(self, path, autoplay=True):
        """Carga un archivo suelto (ej. render de FL Studio) que NO esta en la cola.
        Lo inserta al frente como pista actual sin destruir la cola existente."""
        if not path or not os.path.isfile(path):
            return False
        meta = _extract_metadata(path)
        with self._lock:
            # si ya existe en tracks, reutilizar; si no, añadir
            existing = next((i for i, t in enumerate(self.tracks)
                             if t['path'] == path), None)
            if existing is None:
                self.tracks.append(meta)
                tidx = len(self.tracks) - 1
            else:
                self.tracks[existing] = meta  # refrescar metadatos (el render cambio)
                tidx = existing
            # poner como siguiente en la cola, justo despues de la posicion actual
            if tidx in self.queue_order:
                self.queue_order.remove(tidx)
            insert_pos = max(0, self.current_idx + 1) if self.current_idx >= 0 else 0
            self.queue_order.insert(insert_pos, tidx)
            target_qpos = insert_pos
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume / 100.0)
            if autoplay:
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
            self.current_idx = target_qpos
            self._duration_ms = meta['duration_ms'] or 0
            self._start_wall = time.time()
            self._pause_offset_ms = 0
            return True
        except Exception as e:
            print(f"[audio] load_external fallo: {e}")
            return False

    def toggle_play(self):
        if not self.tracks:
            return
        if self.current_idx < 0:
            self.play(0)
            return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self._start_wall = time.time()
        elif self.is_playing:
            pygame.mixer.music.pause()
            self.is_paused = True
            self._pause_offset_ms = self.position_ms()
        else:
            self.play(self.current_idx)

    def seek_to(self, ms):
        """Salta a la posicion dada (ms) en la pista actual. Conserva el estado play/pausa."""
        if self.current_idx < 0 or not self.queue_order:
            return
        ms = max(0, int(ms))
        was_paused = self.is_paused
        try:
            pygame.mixer.music.play(start=ms / 1000.0)
            self._start_wall = time.time()
            self._pause_offset_ms = ms
            self.is_playing = True
            self.is_paused = False
            if was_paused:
                # mantener en pausa pero en la nueva posicion
                pygame.mixer.music.pause()
                self.is_paused = True
        except Exception as e:
            print('[seek]', e)

    def next_track(self):
        if not self.queue_order:
            return
        nxt = self.current_idx + 1
        if nxt >= len(self.queue_order):
            if self.loop == 1:
                nxt = 0
            else:
                return
        self.play(nxt)

    def prev_track(self):
        if not self.queue_order:
            return
        if self.position_ms() > 3000:
            self.play(self.current_idx)
            return
        prv = self.current_idx - 1
        if prv < 0:
            if self.loop == 1:
                prv = len(self.queue_order) - 1
            else:
                prv = 0
        self.play(prv)

    def set_volume(self, vol):
        self.volume = max(0, min(100, int(vol)))
        pygame.mixer.music.set_volume(self.volume / 100.0)

    def position_ms(self):
        if self.is_paused:
            return self._pause_offset_ms
        if not self.is_playing:
            return 0
        try:
            p = pygame.mixer.music.get_pos()
            if p < 0:
                return self._pause_offset_ms
            return self._pause_offset_ms + p
        except Exception:
            return 0

    def current_track(self):
        if self.current_idx < 0 or not self.queue_order:
            return None
        try:
            return self.tracks[self.queue_order[self.current_idx]]
        except Exception:
            return None

    def upcoming(self, n=6):
        if not self.queue_order:
            return []
        out = []
        for i in range(self.current_idx + 1, min(self.current_idx + 1 + n, len(self.queue_order))):
            out.append(self.tracks[self.queue_order[i]])
        return out

    def auto_advance_if_finished(self):
        """Llamar periodicamente: si pygame termino la pista, avanza."""
        if self.is_playing and not self.is_paused:
            try:
                if not pygame.mixer.music.get_busy():
                    if self.loop == 2:
                        self.play(self.current_idx)
                    else:
                        nxt = self.current_idx + 1
                        if nxt < len(self.queue_order):
                            self.play(nxt)
                        elif self.loop == 1:
                            self.play(0)
                        else:
                            self.is_playing = False
            except Exception:
                pass

    def get_state(self):
        """Snapshot estilo Spotify para el poller."""
        self.auto_advance_if_finished()
        tr = self.current_track()
        if not tr:
            return {
                'is_playing': False,
                'item': None,
                'progress_ms': 0,
                'device_volume': self.volume,
            }
        return {
            'is_playing': self.is_playing and not self.is_paused,
            'item': {
                'id':       tr['path'],
                'name':     tr['title'],
                'artists':  [{'name': tr['artist']}],
                'album':    {'name': tr['album'], 'images': []},
                'duration_ms': tr['duration_ms'],
                'art_bytes': tr.get('art_bytes'),
            },
            'progress_ms': self.position_ms(),
            'device_volume': self.volume,
        }


# ==============================================================================
#   SLIDER DE VOLUMEN RETRO
# ==============================================================================
class IconButton(tk.Canvas):
    """Boton circular con icono dibujado a mano (play / pause / prev / next / gear)."""

    def __init__(self, parent, kind='play', size=48, on_click=None, bg_color=None):
        bg = bg_color if bg_color is not None else BG()
        super().__init__(parent, width=size, height=size,
                         bg=bg, highlightthickness=0, bd=0)
        self.size = size
        self.kind = kind
        self.on_click = on_click
        self._hover = False
        self._primary = True   # True = relleno; False = solo contorno
        self.bind('<Button-1>', lambda e: self.on_click() if self.on_click else None)
        self.bind('<Enter>', lambda e: self._set_hover(True))
        self.bind('<Leave>', lambda e: self._set_hover(False))
        self.configure(cursor='hand2')
        self.draw()

    def set_primary(self, p):
        self._primary = p
        self.draw()

    def _set_hover(self, h):
        self._hover = h
        self.draw()

    def set_kind(self, k):
        self.kind = k
        self.draw()

    def update_theme(self, bg_color=None):
        if bg_color is not None:
            self.configure(bg=bg_color)
        self.draw()

    def draw(self):
        self.delete('all')
        s = self.size
        cx = cy = s // 2
        r = s // 2 - 2
        # circulo de fondo
        if self._primary:
            fill = MAIN_GLW() if self._hover else MAIN()
            outline = ACCENT() if self._hover else MAIN_DIM()
            icon = BG()
        else:
            fill = SURFACE0() if not self._hover else SURFACE1()
            outline = MAIN_DIM()
            icon = MAIN_GLW() if self._hover else MAIN()
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         fill=fill, outline=outline, width=2)

        if self.kind == 'play':
            tw = r * 0.55
            th = r * 0.75
            off = r * 0.08
            self.create_polygon(
                cx - tw / 2 + off, cy - th / 2,
                cx - tw / 2 + off, cy + th / 2,
                cx + tw / 2 + off, cy,
                fill=icon, outline='')
        elif self.kind == 'pause':
            bw = max(2, int(r * 0.18))
            bh = int(r * 0.7)
            gap = max(2, int(r * 0.12))
            self.create_rectangle(cx - gap - bw, cy - bh // 2,
                                  cx - gap,      cy + bh // 2,
                                  fill=icon, outline='')
            self.create_rectangle(cx + gap,      cy - bh // 2,
                                  cx + gap + bw, cy + bh // 2,
                                  fill=icon, outline='')
        elif self.kind == 'prev':
            tw = r * 0.45
            th = r * 0.6
            bw = max(2, int(r * 0.15))
            self.create_rectangle(cx - r * 0.45, cy - th // 2,
                                  cx - r * 0.45 + bw, cy + th // 2,
                                  fill=icon, outline='')
            self.create_polygon(
                cx + tw / 2,     cy - th / 2,
                cx + tw / 2,     cy + th / 2,
                cx - tw / 2 + bw * 1.5, cy,
                fill=icon, outline='')
        elif self.kind == 'next':
            tw = r * 0.45
            th = r * 0.6
            bw = max(2, int(r * 0.15))
            self.create_polygon(
                cx - tw / 2,     cy - th / 2,
                cx - tw / 2,     cy + th / 2,
                cx + tw / 2 - bw * 0.5, cy,
                fill=icon, outline='')
            self.create_rectangle(cx + r * 0.45 - bw, cy - th // 2,
                                  cx + r * 0.45,      cy + th // 2,
                                  fill=icon, outline='')
        elif self.kind == 'gear':
            # rueda dentada: 8 dientes + circulo + nucleo
            n_teeth = 8
            r_out = r * 0.95
            r_in = r * 0.7
            r_core = r * 0.30
            pts = []
            for i in range(n_teeth * 2):
                ang = i * math.pi / n_teeth
                rr = r_out if (i % 2 == 0) else r_in
                pts.append(cx + rr * math.cos(ang))
                pts.append(cy + rr * math.sin(ang))
            self.create_polygon(*pts, fill=icon, outline=icon, width=1)
            self.create_oval(cx - r_core, cy - r_core,
                             cx + r_core, cy + r_core,
                             fill=fill, outline=fill)
        elif self.kind == 'collapse':
            # flecha doble apuntando a la derecha (ocultar columna derecha)
            self.create_polygon(
                cx - r * 0.4, cy - r * 0.5,
                cx + r * 0.0, cy,
                cx - r * 0.4, cy + r * 0.5,
                fill=icon, outline='')
            self.create_polygon(
                cx - r * 0.0, cy - r * 0.5,
                cx + r * 0.4, cy,
                cx - r * 0.0, cy + r * 0.5,
                fill=icon, outline='')
        elif self.kind == 'expand':
            # flecha doble apuntando a la izquierda (mostrar columna)
            self.create_polygon(
                cx + r * 0.4, cy - r * 0.5,
                cx + r * 0.0, cy,
                cx + r * 0.4, cy + r * 0.5,
                fill=icon, outline='')
            self.create_polygon(
                cx + r * 0.0, cy - r * 0.5,
                cx - r * 0.4, cy,
                cx + r * 0.0, cy + r * 0.5,
                fill=icon, outline='')


class RetroVolumeSlider(tk.Canvas):
    def __init__(self, parent, command, **kw):
        super().__init__(parent, bg=CRUST(), highlightthickness=0,
                         height=22, **kw)
        self.command = command
        self.level = 0.7
        self._hover = False
        self.bind('<Configure>', self._draw)
        self.bind('<Button-1>', self._on_click)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<Enter>', lambda e: self._set_hover(True))
        self.bind('<Leave>', lambda e: self._set_hover(False))
        # scroll del raton: sube/baja volumen 5% por tick, solo con puntero encima
        self.bind('<MouseWheel>', self._on_wheel)   # Windows / macOS
        self.bind('<Button-4>',   self._on_wheel)   # Linux scroll-up
        self.bind('<Button-5>',   self._on_wheel)   # Linux scroll-down

    def _on_wheel(self, event):
        # delta normalizado: +1 arriba, -1 abajo
        if hasattr(event, 'delta') and event.delta:
            step = 1 if event.delta > 0 else -1
        elif getattr(event, 'num', None) == 4:
            step = 1
        elif getattr(event, 'num', None) == 5:
            step = -1
        else:
            step = 0
        new_level = max(0.0, min(1.0, self.level + step * 0.05))
        if new_level == self.level:
            return
        self.level = new_level
        if self.command:
            try:
                self.command(int(self.level * 100))
            except Exception:
                pass
        self._draw()

    def _set_hover(self, state):
        self._hover = state
        self._draw()

    def set_level(self, level):
        self.level = max(0.0, min(1.0, level))
        self._draw()

    def _on_click(self, event):
        self._update_level_from_mouse(event.x)

    def _on_drag(self, event):
        self._update_level_from_mouse(event.x)

    def _update_level_from_mouse(self, x):
        w = max(1, self.winfo_width())
        pad = 6
        usable = max(1, w - 2 * pad)
        lvl = (x - pad) / usable
        self.level = max(0.0, min(1.0, lvl))
        if self.command:
            try:
                self.command(int(self.level * 100))
            except Exception:
                pass
        self._draw()

    def _draw(self, event=None):
        self.delete('all')
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return
        pad = 6
        cy = h // 2
        # carril
        self.create_rectangle(pad, cy - 2, w - pad, cy + 2,
                              fill=SURFACE0(), outline='')
        # nivel
        filled = pad + int((w - 2 * pad) * self.level)
        self.create_rectangle(pad, cy - 2, filled, cy + 2,
                              fill=MAIN_GLW(), outline='')
        # marcas (ticks)
        for i in range(0, 11):
            x = pad + int((w - 2 * pad) * (i / 10))
            tone = MAIN() if i / 10 <= self.level else MAIN_DK()
            self.create_line(x, cy - 5, x, cy + 5, fill=tone)
        # cabezal
        hr = 7 if self._hover else 5
        self.create_oval(filled - hr, cy - hr, filled + hr, cy + hr,
                         fill=MAIN_GLW(), outline=ACCENT(), width=2)

    def update_theme(self):
        self.configure(bg=CRUST())
        self._draw()


# ==============================================================================
#   SINCRONIZADOR DE LETRAS
# ==============================================================================
class LyricSyncer:
    def __init__(self):
        self.synced = []   # [{'time':ms, 'text':str}]
        self.plain = ''
        self.plain_lines = []
        self.has_synced = False
        self.has_plain = False

    def set_synced(self, lines):
        self.synced = lines or []
        self.has_synced = bool(self.synced)

    def set_plain(self, text):
        self.plain = text or ''
        self.plain_lines = [ln.strip() for ln in self.plain.splitlines() if ln.strip()]
        self.has_plain = bool(self.plain_lines)

    def clear(self):
        self.synced = []
        self.plain = ''
        self.plain_lines = []
        self.has_synced = False
        self.has_plain = False

    def get_active_synced(self, progress_ms):
        """Devuelve indices con (idx, distancia) para resaltar."""
        if not self.synced:
            return []
        cur = 0
        for i, ln in enumerate(self.synced):
            if ln['time'] <= progress_ms:
                cur = i
            else:
                break
        return cur

    def get_active_plain(self, progress_ms, duration_ms):
        """Estima linea activa interpolando linealmente."""
        if not self.plain_lines or not duration_ms:
            return 0, 0.0
        frac = max(0.0, min(1.0, progress_ms / max(1, duration_ms)))
        idx = int(frac * len(self.plain_lines))
        idx = min(idx, len(self.plain_lines) - 1)
        return idx, frac


# ==============================================================================
#   VENTANA DE CONFIGURACION (carpeta local + tema + idioma)
# ==============================================================================
class ConfigWindow(tk.Toplevel):
    def __init__(self, parent, on_save, on_rescan=None,
                 current_theme='purple', current_lang='es',
                 current_folder='', current_user='User',
                 current_spectrum='compact', current_lyric='classic',
                 current_art='normal', current_auto_theme=False,
                 current_fl=None):
        super().__init__(parent)
        self.parent = parent
        self.on_save = on_save
        self.on_rescan = on_rescan
        self._theme = current_theme
        self._lang = current_lang
        self._folder = current_folder or ''
        self._spectrum = current_spectrum
        self._lyric = current_lyric
        self._art = current_art
        self._auto_theme = bool(current_auto_theme)
        self._fl = dict(current_fl or {})

        # ---- ventana con diseño propio (sin chrome del SO) ----
        W, H = 560, 820
        self.configure(bg=MAIN_GLW())  # borde exterior del tema
        self.resizable(False, False)
        try:
            self.update_idletasks()
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + max(0, (pw - W) // 2)
            y = py + max(0, (ph - H) // 2)
            if y < 0:
                y = 20
            self.geometry(f'{W}x{H}+{x}+{y}')
        except Exception:
            self.geometry(f'{W}x{H}')
        self.transient(parent)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.after(150, lambda: self._safe_untop())
        self.after(120, self._take_focus)
        self.bind('<Escape>', lambda e: self.destroy())

        # marco interior (2px borde tematico)
        inner = tk.Frame(self, bg=MANTLE())
        inner.pack(fill='both', expand=True, padx=2, pady=2)

        # ---- barra de titulo personalizada ----
        titlebar = tk.Frame(inner, bg=CRUST())
        titlebar.pack(fill='x', side='top')
        self._tbar_lbl = tk.Label(titlebar, text=_T('cfg_title'),
                                  font=('Courier', 11, 'bold'),
                                  fg=MAIN_GLW(), bg=CRUST())
        self._tbar_lbl.pack(side='left', padx=14, pady=9)
        close_btn = tk.Label(titlebar, text='✕', font=('Courier', 12, 'bold'),
                             fg=MAIN(), bg=CRUST(), cursor='hand2')
        close_btn.pack(side='right', padx=12)
        close_btn.bind('<Button-1>', lambda e: self.destroy())
        close_btn.bind('<Enter>', lambda e: close_btn.configure(fg=PINK_ERR))
        close_btn.bind('<Leave>', lambda e: close_btn.configure(fg=MAIN()))
        for w in (titlebar, self._tbar_lbl):
            w.bind('<Button-1>', self._start_move)
            w.bind('<B1-Motion>', self._do_move)
        tk.Frame(inner, bg=MAIN_GLW(), height=2).pack(fill='x', side='top')

        # ---- viewport con scroll (muchas secciones en PRO) ----
        _vsb = ttk.Scrollbar(inner, orient='vertical')
        _vsb.pack(side='right', fill='y')
        _cv = tk.Canvas(inner, bg=MANTLE(), highlightthickness=0,
                        yscrollcommand=_vsb.set)
        _cv.pack(side='left', fill='both', expand=True)
        _vsb.configure(command=_cv.yview)
        outer = tk.Frame(_cv, bg=MANTLE(), padx=22, pady=16)
        _cid = _cv.create_window((0, 0), window=outer, anchor='nw')
        outer.bind('<Configure>',
                   lambda e: _cv.configure(scrollregion=_cv.bbox('all')))
        _cv.bind('<Configure>',
                 lambda e: _cv.itemconfigure(_cid, width=e.width))
        self.bind('<MouseWheel>',
                  lambda e: _cv.yview_scroll(-1 if e.delta > 0 else 1, 'units'))

        tk.Label(outer, text=_T('cfg_creds'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(0, 6))

        # ---- carpeta de musica ----
        tk.Label(outer, text=_T('cfg_folder'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x')
        folder_row = tk.Frame(outer, bg=MANTLE())
        folder_row.pack(fill='x', pady=(2, 8))
        self.folder_entry = tk.Entry(
            folder_row,
            font=('Courier', 10), bg=CRUST(), fg=SEC(), insertbackground=MAIN(),
            relief=tk.FLAT, highlightthickness=1,
            highlightcolor=MAIN(), highlightbackground=OVERLAY,
        )
        self.folder_entry.insert(0, self._folder)
        self.folder_entry.pack(side='left', fill='x', expand=True, ipady=4)
        self.folder_entry.bind('<Button-1>', lambda e: e.widget.focus_set())
        tk.Button(folder_row, text=_T('cfg_browse'),
                  font=('Courier', 8, 'bold'),
                  bg=SURFACE0(), fg=MAIN(), activebackground=SURFACE1(),
                  activeforeground=MAIN_GLW(), relief=tk.FLAT, cursor='hand2',
                  bd=0, padx=10,
                  command=self._pick_folder).pack(side='left', padx=(6, 0))
        # boton rescan (refresca canciones nuevas sin cambiar la carpeta)
        tk.Button(folder_row, text='⟳',
                  font=('Courier', 11, 'bold'),
                  bg=ACC_DIM(), fg=MAIN_GLW(),
                  activebackground=ACCENT(), activeforeground=BG(),
                  relief=tk.FLAT, cursor='hand2',
                  bd=0, padx=10,
                  command=self._do_rescan).pack(side='left', padx=(4, 0))

        # ---- usuario ----
        tk.Label(outer, text=_T('cfg_name'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(6, 2))
        self.user_entry = tk.Entry(
            outer,
            font=('Courier', 11), bg=CRUST(), fg=SEC(), insertbackground=MAIN(),
            relief=tk.FLAT, highlightthickness=1,
            highlightcolor=MAIN(), highlightbackground=OVERLAY,
        )
        self.user_entry.insert(0, current_user or 'User')
        self.user_entry.pack(fill='x', ipady=6, pady=(0, 12))
        self.user_entry.bind('<Button-1>', lambda e: e.widget.focus_set())

        # estado scan
        self.scan_lbl = tk.Label(outer, text='',
                                 font=('Courier', 8),
                                 fg='#94e2d5', bg=MANTLE(), anchor='w')
        self.scan_lbl.pack(fill='x')

        # ---- tema ----
        tk.Label(outer, text=_T('cfg_theme'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(12, 4))
        themes_frame = tk.Frame(outer, bg=MANTLE())
        themes_frame.pack(fill='x')
        self._theme_btns = {}
        keys = list(THEMES.keys())
        rows = 2
        cols = 5
        for i, name in enumerate(keys):
            tk_btn = tk.Label(
                themes_frame,
                text=_T(f'theme_{name}'),
                font=('Courier', 8, 'bold'),
                fg=THEMES[name]['MAIN'],
                bg=THEMES[name]['BG'],
                padx=6, pady=6, bd=2, relief=tk.FLAT,
                cursor='hand2',
            )
            r, c = divmod(i, cols)
            tk_btn.grid(row=r, column=c, padx=2, pady=2, sticky='nsew')
            themes_frame.grid_columnconfigure(c, weight=1)
            tk_btn.bind('<Button-1>', lambda e, n=name: self._select_theme(n))
            self._theme_btns[name] = tk_btn
        self._select_theme(self._theme)

        # ---- tema automatico segun portada ----
        tk.Label(outer, text=_T('cfg_auto_theme'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(12, 4))
        auto_frame = tk.Frame(outer, bg=MANTLE())
        auto_frame.pack(fill='x')
        self._auto_btns = {}
        for val, key in [(True, 'auto_theme_on'), (False, 'auto_theme_off')]:
            b = tk.Label(auto_frame, text=_T(key),
                         font=('Courier', 9, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=8, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, v=val: self._select_auto_theme(v))
            self._auto_btns[val] = b
        self._select_auto_theme(self._auto_theme)

        # ---- idioma ----
        tk.Label(outer, text=_T('cfg_lang'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(12, 4))
        lang_frame = tk.Frame(outer, bg=MANTLE())
        lang_frame.pack(fill='x')
        self._lang_btns = {}
        for code, label in [('es', 'ESPANOL'), ('en', 'ENGLISH')]:
            b = tk.Label(lang_frame, text=label,
                         font=('Courier', 9, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=8, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, c=code: self._select_lang(c))
            self._lang_btns[code] = b
        self._select_lang(self._lang)

        # ---- posicion del espectro ----
        tk.Label(outer, text=_T('cfg_spectrum'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(12, 4))
        spec_frame = tk.Frame(outer, bg=MANTLE())
        spec_frame.pack(fill='x')
        self._spec_btns = {}
        for mode, key in [('compact', 'spectrum_compact'), ('large', 'spectrum_large')]:
            b = tk.Label(spec_frame, text=_T(key),
                         font=('Courier', 9, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=8, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, m=mode: self._select_spectrum(m))
            self._spec_btns[mode] = b
        self._select_spectrum(self._spectrum)

        # ---- estilo de letras ----
        tk.Label(outer, text=_T('cfg_lyric_style'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(12, 4))
        lyr_frame = tk.Frame(outer, bg=MANTLE())
        lyr_frame.pack(fill='x')
        self._lyr_btns = {}
        for mode, key in [('classic', 'lyric_classic'), ('large', 'lyric_large')]:
            b = tk.Label(lyr_frame, text=_T(key),
                         font=('Courier', 9, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=8, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, m=mode: self._select_lyric_style(m))
            self._lyr_btns[mode] = b
        self._select_lyric_style(self._lyric)

        # ---- estilo de portada (CRT) ----
        tk.Label(outer, text=_T('cfg_art_style'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(12, 4))
        art_frame = tk.Frame(outer, bg=MANTLE())
        art_frame.pack(fill='x')
        self._art_btns = {}
        for mode, key in [('normal', 'art_normal'), ('crt', 'art_crt')]:
            b = tk.Label(art_frame, text=_T(key),
                         font=('Courier', 9, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=8, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, m=mode: self._select_art_style(m))
            self._art_btns[mode] = b
        self._select_art_style(self._art)

        # =================== SECCION FL STUDIO (PRO) ===================
        tk.Frame(outer, bg=SURFACE0(), height=2).pack(fill='x', pady=(16, 8))
        tk.Label(outer, text=_T('cfg_fl_title'),
                 font=('Courier', 11, 'bold'),
                 fg=MAIN_GLW(), bg=MANTLE(), anchor='w').pack(fill='x', pady=(0, 8))

        # toggle vigilancia
        tk.Label(outer, text=_T('cfg_fl_watch'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(2, 4))
        watch_frame = tk.Frame(outer, bg=MANTLE())
        watch_frame.pack(fill='x')
        self._fl_watch_btns = {}
        for val, key in [(True, 'fl_on'), (False, 'fl_off')]:
            b = tk.Label(watch_frame, text=_T(key),
                         font=('Courier', 9, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=8, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, v=val: self._select_fl_watch(v))
            self._fl_watch_btns[val] = b
        self._select_fl_watch(bool(self._fl.get('watch', False)))

        # carpeta export
        tk.Label(outer, text=_T('cfg_fl_export'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(8, 2))
        exp_row = tk.Frame(outer, bg=MANTLE())
        exp_row.pack(fill='x', pady=(0, 4))
        self.fl_export_entry = tk.Entry(
            exp_row, font=('Courier', 10), bg=CRUST(), fg=SEC(),
            insertbackground=MAIN(), relief=tk.FLAT, highlightthickness=1,
            highlightcolor=MAIN(), highlightbackground=OVERLAY)
        self.fl_export_entry.insert(0, self._fl.get('export_folder', ''))
        self.fl_export_entry.pack(side='left', fill='x', expand=True, ipady=4)
        self.fl_export_entry.bind('<Button-1>', lambda e: e.widget.focus_set())
        tk.Button(exp_row, text=_T('cfg_browse'),
                  font=('Courier', 8, 'bold'), bg=SURFACE0(), fg=MAIN(),
                  activebackground=SURFACE1(), activeforeground=MAIN_GLW(),
                  relief=tk.FLAT, cursor='hand2', bd=0, padx=10,
                  command=lambda: self._pick_into(
                      self.fl_export_entry,
                      'Selecciona la carpeta de renders')).pack(side='left', padx=(6, 0))

        # carpeta samples
        tk.Label(outer, text=_T('cfg_fl_samples'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(8, 2))
        smp_row = tk.Frame(outer, bg=MANTLE())
        smp_row.pack(fill='x', pady=(0, 4))
        self.fl_samples_entry = tk.Entry(
            smp_row, font=('Courier', 10), bg=CRUST(), fg=SEC(),
            insertbackground=MAIN(), relief=tk.FLAT, highlightthickness=1,
            highlightcolor=MAIN(), highlightbackground=OVERLAY)
        self.fl_samples_entry.insert(0, self._fl.get('samples_folder', ''))
        self.fl_samples_entry.pack(side='left', fill='x', expand=True, ipady=4)
        self.fl_samples_entry.bind('<Button-1>', lambda e: e.widget.focus_set())
        tk.Button(smp_row, text=_T('cfg_browse'),
                  font=('Courier', 8, 'bold'), bg=SURFACE0(), fg=MAIN(),
                  activebackground=SURFACE1(), activeforeground=MAIN_GLW(),
                  relief=tk.FLAT, cursor='hand2', bd=0, padx=10,
                  command=lambda: self._pick_into(
                      self.fl_samples_entry,
                      'Selecciona la carpeta de samples')).pack(side='left', padx=(6, 0))

        # auto-reproducir render
        tk.Label(outer, text=_T('cfg_fl_autoplay'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(8, 4))
        ap_frame = tk.Frame(outer, bg=MANTLE())
        ap_frame.pack(fill='x')
        self._fl_autoplay_btns = {}
        for val, key in [(True, 'fl_on'), (False, 'fl_off')]:
            b = tk.Label(ap_frame, text=_T(key),
                         font=('Courier', 9, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=8, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, v=val: self._select_fl_autoplay(v))
            self._fl_autoplay_btns[val] = b
        self._select_fl_autoplay(bool(self._fl.get('autoplay', True)))

        # objetivo LUFS
        tk.Label(outer, text=_T('cfg_fl_target'),
                 font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(8, 4))
        lufs_frame = tk.Frame(outer, bg=MANTLE())
        lufs_frame.pack(fill='x')
        self._fl_lufs_btns = {}
        for val, label in [(-14.0, '-14 (streaming)'), (-9.0, '-9 (club)'),
                           (-16.0, '-16 (suave)')]:
            b = tk.Label(lufs_frame, text=label,
                         font=('Courier', 8, 'bold'),
                         fg=MAIN(), bg=SURFACE0(),
                         padx=6, pady=5, cursor='hand2', bd=2, relief=tk.FLAT)
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, v=val: self._select_fl_lufs(v))
            self._fl_lufs_btns[val] = b
        self._select_fl_lufs(float(self._fl.get('target_lufs', -14.0)))

        # ---- save + tiktok ----
        btns = tk.Frame(outer, bg=MANTLE())
        btns.pack(fill='x', pady=(20, 0))

        save_btn = tk.Label(btns, text=_T('cfg_save'),
                            font=('Courier', 11, 'bold'),
                            fg=BG(), bg=MAIN(), padx=14, pady=8,
                            cursor='hand2')
        save_btn.pack(fill='x', pady=(0, 6))
        save_btn.bind('<Button-1>', lambda e: self._save())

        tk_btn = tk.Label(btns, text=_T('cfg_follow'),
                          font=('Courier', 9, 'bold'),
                          fg=MAIN_GLW(), bg=CRUST(), padx=10, pady=6,
                          cursor='hand2')
        tk_btn.pack(fill='x')
        tk_btn.bind('<Button-1>', open_tiktok)

    # ---- ventana custom: arrastre y topmost ----
    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_move(self, event):
        try:
            x = self.winfo_x() + event.x - self._drag_x
            y = self.winfo_y() + event.y - self._drag_y
            self.geometry(f'+{x}+{y}')
        except Exception:
            pass

    def _safe_untop(self):
        try:
            self.attributes('-topmost', False)
        except Exception:
            pass

    def _take_focus(self):
        # con overrideredirect, grab_set + focus_force enrutan el teclado a los Entry
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass

    def _normalize_folder(self, folder):
        folder = (folder or '').strip().strip('"')
        if not folder:
            return ''
        return os.path.normpath(os.path.abspath(os.path.expanduser(folder)))

    def _ask_directory(self, title, current=''):
        current = self._normalize_folder(current)
        initial = current if os.path.isdir(current) else os.path.expanduser('~')
        try:
            self.attributes('-topmost', False)
            self.grab_release()   # liberar grab para que el filedialog reciba eventos
            self.update_idletasks()
        except Exception:
            pass
        try:
            folder = filedialog.askdirectory(
                parent=self,       # usar self (ConfigWindow) como padre, no la ventana raiz
                title=title,
                initialdir=initial,
                mustexist=True,
            )
        finally:
            try:
                self.grab_set()   # restaurar grab al volver
                self.lift()
                self.focus_force()
            except Exception:
                pass
        return self._normalize_folder(folder)

    def _pick_folder(self):
        folder = self._ask_directory(
            'Selecciona la carpeta de musica',
            self.folder_entry.get() or self._folder,
        )
        if folder:
            self._folder = folder
            self.folder_entry.delete(0, 'end')
            self.folder_entry.insert(0, folder)

    def _do_rescan(self):
        folder = self._normalize_folder(self.folder_entry.get())
        if not folder or not os.path.isdir(folder):
            self.scan_lbl.configure(text='× ruta invalida', fg=PINK_ERR)
            return
        self.scan_lbl.configure(text='⟳ ' + _T('cfg_scanning'), fg=MAIN_GLW())
        if self.on_rescan:
            def _done(n):
                try:
                    self.scan_lbl.configure(
                        text=f'✓ {_T("cfg_scanned")}{n}', fg=MAIN_GLW())
                except Exception:
                    pass
            self.on_rescan(folder, _done)

    def _select_lang(self, lang):
        global CURRENT_LANG
        self._lang = lang
        CURRENT_LANG = lang
        for code, b in self._lang_btns.items():
            if code == lang:
                b.configure(fg=BG(), bg=MAIN_GLW())
            else:
                b.configure(fg=MAIN(), bg=SURFACE0())

    def _select_theme(self, name):
        self._theme = name
        apply_theme(name)
        for n, b in self._theme_btns.items():
            if n == name:
                b.configure(relief=tk.SOLID, bd=2,
                            highlightbackground=THEMES[n]['MAIN_GLW'])
            else:
                b.configure(relief=tk.FLAT, bd=2)

    def _select_spectrum(self, mode):
        self._spectrum = mode
        for m, b in self._spec_btns.items():
            if m == mode:
                b.configure(fg=BG(), bg=MAIN_GLW())
            else:
                b.configure(fg=MAIN(), bg=SURFACE0())

    def _select_lyric_style(self, mode):
        self._lyric = mode
        for m, b in self._lyr_btns.items():
            if m == mode:
                b.configure(fg=BG(), bg=MAIN_GLW())
            else:
                b.configure(fg=MAIN(), bg=SURFACE0())

    def _select_art_style(self, mode):
        self._art = mode
        for m, b in self._art_btns.items():
            if m == mode:
                b.configure(fg=BG(), bg=MAIN_GLW())
            else:
                b.configure(fg=MAIN(), bg=SURFACE0())

    def _select_auto_theme(self, val):
        self._auto_theme = bool(val)
        for v, b in self._auto_btns.items():
            if v == self._auto_theme:
                b.configure(fg=BG(), bg=MAIN_GLW())
            else:
                b.configure(fg=MAIN(), bg=SURFACE0())

    # ---- FL Studio (PRO) ----
    def _pick_into(self, entry, title='Selecciona carpeta'):
        folder = self._ask_directory(title, entry.get())
        if folder:
            entry.delete(0, 'end')
            entry.insert(0, folder)

    def _select_fl_watch(self, val):
        self._fl['watch'] = bool(val)
        for v, b in self._fl_watch_btns.items():
            b.configure(fg=BG() if v == bool(val) else MAIN(),
                        bg=MAIN_GLW() if v == bool(val) else SURFACE0())

    def _select_fl_autoplay(self, val):
        self._fl['autoplay'] = bool(val)
        for v, b in self._fl_autoplay_btns.items():
            b.configure(fg=BG() if v == bool(val) else MAIN(),
                        bg=MAIN_GLW() if v == bool(val) else SURFACE0())

    def _select_fl_lufs(self, val):
        self._fl['target_lufs'] = float(val)
        for v, b in self._fl_lufs_btns.items():
            b.configure(fg=BG() if v == float(val) else MAIN(),
                        bg=MAIN_GLW() if v == float(val) else SURFACE0())

    def _save(self):
        folder = self._normalize_folder(self.folder_entry.get())
        user = self.user_entry.get().strip() or 'User'
        # recoger config FL
        self._fl['export_folder'] = self._normalize_folder(
            self.fl_export_entry.get())
        self._fl['samples_folder'] = self._normalize_folder(
            self.fl_samples_entry.get())
        fl = dict(self._fl)
        save_credentials(folder, user, self._theme, self._lang,
                         self._spectrum, self._lyric, self._art, self._auto_theme, fl)
        try:
            self.on_save(folder, user, self._theme, self._lang,
                         self._spectrum, self._lyric, self._art, self._auto_theme, fl)
        finally:
            self.destroy()


# ==============================================================================
#   PANEL STUDIO (analisis de mastering)
# ==============================================================================
class StudioPanel(tk.Toplevel):
    def __init__(self, parent, analysis=None, on_export=None):
        super().__init__(parent)
        self.parent = parent
        self.on_export = on_export
        self._src_path = None

        # ---- ventana con diseño propio (sin chrome del SO) ----
        W, H = 460, 620
        self.configure(bg=MAIN_GLW())
        self.resizable(False, False)
        try:
            self.update_idletasks()
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + max(0, (pw - W) // 2)
            y = py + max(0, (ph - H) // 2)
            if y < 0:
                y = 20
            self.geometry(f'{W}x{H}+{x}+{y}')
        except Exception:
            self.geometry(f'{W}x{H}')
        self.transient(parent)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.after(150, lambda: self._safe_untop())
        self.after(120, self._take_focus)
        self.bind('<Escape>', lambda e: self.destroy())

        inner = tk.Frame(self, bg=MANTLE())
        inner.pack(fill='both', expand=True, padx=2, pady=2)

        # barra de titulo custom
        titlebar = tk.Frame(inner, bg=CRUST())
        titlebar.pack(fill='x', side='top')
        self._tbar_lbl = tk.Label(titlebar, text=_T('studio_title'),
                                  font=('Courier', 11, 'bold'),
                                  fg=MAIN_GLW(), bg=CRUST())
        self._tbar_lbl.pack(side='left', padx=14, pady=9)
        close_btn = tk.Label(titlebar, text='✕', font=('Courier', 12, 'bold'),
                             fg=MAIN(), bg=CRUST(), cursor='hand2')
        close_btn.pack(side='right', padx=12)
        close_btn.bind('<Button-1>', lambda e: self.destroy())
        close_btn.bind('<Enter>', lambda e: close_btn.configure(fg=PINK_ERR))
        close_btn.bind('<Leave>', lambda e: close_btn.configure(fg=MAIN()))
        for w in (titlebar, self._tbar_lbl):
            w.bind('<Button-1>', self._start_move)
            w.bind('<B1-Motion>', self._do_move)
        tk.Frame(inner, bg=MAIN_GLW(), height=2).pack(fill='x', side='top')

        outer = tk.Frame(inner, bg=MANTLE(), padx=22, pady=16)
        outer.pack(fill='both', expand=True)

        # archivo
        self.file_lbl = tk.Label(outer, text='-', font=('Courier', 8),
                                 fg=SEC_DIM(), bg=MANTLE(), anchor='w')
        self.file_lbl.pack(fill='x', pady=(0, 10))

        # --- LUFS ---
        tk.Label(outer, text=_T('studio_lufs'), font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x')
        self.lufs_val = tk.Label(outer, text='--', font=('Courier', 18, 'bold'),
                                 fg=MAIN_GLW(), bg=MANTLE(), anchor='w')
        self.lufs_val.pack(fill='x')
        self.lufs_canvas = tk.Canvas(outer, bg=CRUST(), highlightthickness=0, height=18)
        self.lufs_canvas.pack(fill='x', pady=(2, 12))

        # --- peak + clip ---
        pk = tk.Frame(outer, bg=MANTLE()); pk.pack(fill='x', pady=(0, 12))
        pkl = tk.Frame(pk, bg=MANTLE()); pkl.pack(side='left', expand=True, fill='x')
        tk.Label(pkl, text=_T('studio_peak'), font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x')
        self.peak_val = tk.Label(pkl, text='--', font=('Courier', 14, 'bold'),
                                 fg=MAIN(), bg=MANTLE(), anchor='w')
        self.peak_val.pack(fill='x')
        pkr = tk.Frame(pk, bg=MANTLE()); pkr.pack(side='left', expand=True, fill='x')
        tk.Label(pkr, text=_T('studio_clip'), font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x')
        self.clip_val = tk.Label(pkr, text='--', font=('Courier', 14, 'bold'),
                                 fg=MAIN(), bg=MANTLE(), anchor='w')
        self.clip_val.pack(fill='x')

        # --- balance espectral ---
        tk.Label(outer, text=_T('studio_balance'), font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x', pady=(0, 4))
        self.bal_canvas = tk.Canvas(outer, bg=CRUST(), highlightthickness=0, height=72)
        self.bal_canvas.pack(fill='x', pady=(0, 12))

        # --- estereo ---
        tk.Label(outer, text=_T('studio_stereo'), font=('Courier', 9, 'bold'),
                 fg=SUBTEXT, bg=MANTLE(), anchor='w').pack(fill='x')
        self.stereo_val = tk.Label(outer, text='--', font=('Courier', 10, 'bold'),
                                   fg=SEC(), bg=MANTLE(), anchor='w')
        self.stereo_val.pack(fill='x')
        self.stereo_canvas = tk.Canvas(outer, bg=CRUST(), highlightthickness=0, height=18)
        self.stereo_canvas.pack(fill='x', pady=(2, 12))

        # --- veredicto global ---
        self.verdict_lbl = tk.Label(outer, text='', font=('Courier', 11, 'bold'),
                                    fg=MAIN_GLW(), bg=MANTLE(), anchor='center')
        self.verdict_lbl.pack(fill='x', pady=(2, 12))

        # --- export ---
        self.export_btn = tk.Label(outer, text=_T('studio_export_opt'),
                                   font=('Courier', 10, 'bold'),
                                   fg=BG(), bg=MAIN(), padx=12, pady=8, cursor='hand2')
        self.export_btn.pack(fill='x')
        self.export_btn.bind('<Button-1>', lambda e: self._do_export())
        self.export_status = tk.Label(outer, text='', font=('Courier', 8),
                                      fg='#94e2d5', bg=MANTLE(), anchor='w')
        self.export_status.pack(fill='x', pady=(6, 0))

        if analysis:
            self.update_data(analysis)

    # ---- ventana custom: arrastre y topmost ----
    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_move(self, event):
        try:
            x = self.winfo_x() + event.x - self._drag_x
            y = self.winfo_y() + event.y - self._drag_y
            self.geometry(f'+{x}+{y}')
        except Exception:
            pass

    def _safe_untop(self):
        try:
            self.attributes('-topmost', False)
        except Exception:
            pass

    def _take_focus(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass

    # ---- helpers de dibujo ----
    def _bar(self, canvas, frac, color, marker_frac=None):
        canvas.delete('all')
        canvas.update_idletasks()
        w = canvas.winfo_width() or 400
        h = canvas.winfo_height() or 18
        canvas.create_rectangle(0, 0, w, h, fill=SURFACE0(), outline='')
        fw = int(max(0.0, min(1.0, frac)) * w)
        canvas.create_rectangle(0, 0, fw, h, fill=color, outline='')
        if marker_frac is not None:
            mx = int(max(0.0, min(1.0, marker_frac)) * w)
            canvas.create_line(mx, 0, mx, h, fill=MAIN_GLW(), width=2)

    def _zone_color(self, ok):
        return MAIN_GLW() if ok == 'ok' else (ACCENT() if ok == 'warn' else PINK_ERR)

    def update_data(self, res):
        self._src_path = res.get('path')
        try:
            self.file_lbl.configure(text=os.path.basename(res.get('path', '-')))
            # LUFS
            lufs = res['lufs']; tgt = res['target_lufs']
            approx = ' (approx)' if res.get('lufs_approx') else ''
            self.lufs_val.configure(text=f"{lufs:+.1f}{approx}  →  obj {tgt:+.0f}")
            frac = (lufs - (-30.0)) / 30.0
            mfrac = (tgt - (-30.0)) / 30.0
            diff = abs(lufs - tgt)
            zone = 'ok' if diff <= 1.0 else ('warn' if diff <= 3.0 else 'bad')
            self.after(20, lambda: self._bar(self.lufs_canvas, frac, self._zone_color(zone), mfrac))
            # peak / clip
            self.peak_val.configure(text=f"{res['true_peak_db']:+.1f} dBTP")
            if res['clipping']:
                self.clip_val.configure(text=f"⚠ {res['clip_count']}", fg=PINK_ERR)
            else:
                self.clip_val.configure(text='OK ✓', fg=MAIN_GLW())
            # balance
            self.after(20, lambda: self._draw_balance(res['balance']))
            # estereo
            if res['is_mono']:
                self.stereo_val.configure(text=_T('studio_mono'))
                self.after(20, lambda: self._bar(self.stereo_canvas, 1.0, MAIN_DIM(), 0.5))
            else:
                corr = res['stereo_corr']; width = res['stereo_width']
                self.stereo_val.configure(
                    text=f"{_T('studio_corr')} {corr:+.2f}   {_T('studio_width')} {width:.2f}")
                cfrac = (corr + 1.0) / 2.0
                ccol = PINK_ERR if corr < -0.1 else (MAIN_GLW() if corr > 0.2 else ACCENT())
                self.after(20, lambda: self._bar(self.stereo_canvas, cfrac, ccol, 0.5))
            # veredicto
            v = res['verdict']
            vtxt = _T('v_' + v) if ('v_' + v) in LANGS.get(CURRENT_LANG, {}) else v
            vcol = PINK_ERR if v in ('clip', 'phase') else (MAIN_GLW() if v == 'ok' else ACCENT())
            self.verdict_lbl.configure(text=vtxt, fg=vcol)
        except Exception as e:
            print('[studiopanel]', e)

    def _draw_balance(self, balance):
        c = self.bal_canvas
        c.delete('all')
        c.update_idletasks()
        w = c.winfo_width() or 400
        h = c.winfo_height() or 72
        rows = [(_T('studio_bass'), balance['bass']),
                (_T('studio_mid'), balance['mid']),
                (_T('studio_treble'), balance['treble'])]
        rh = h // 3
        for i, (label, val) in enumerate(rows):
            y = i * rh
            c.create_text(6, y + rh // 2, text=label, anchor='w',
                          font=('Courier', 8, 'bold'), fill=SEC())
            bx0 = 70
            bw = w - bx0 - 50
            c.create_rectangle(bx0, y + 4, bx0 + bw, y + rh - 4,
                               fill=SURFACE0(), outline='')
            fw = int(max(0.0, min(1.0, val)) * bw)
            c.create_rectangle(bx0, y + 4, bx0 + fw, y + rh - 4,
                               fill=MAIN_GLW(), outline='')
            c.create_text(w - 6, y + rh // 2, text=f'{val*100:.0f}%', anchor='e',
                          font=('Courier', 8, 'bold'), fill=MAIN())

    def _do_export(self):
        if self.on_export and self._src_path:
            self.export_status.configure(text='...', fg=ACCENT())
            self.on_export(self._src_path)

    def on_exported(self, out_path):
        self.export_status.configure(text='✓ ' + os.path.basename(out_path), fg=MAIN_GLW())


# ==============================================================================
#   PLAYER PRINCIPAL
# ==============================================================================
class SevenFMPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('UTMOST.FM PRO 2.0  ·  Studio')
        self.geometry('1280x780')
        self.minsize(880, 560)
        self.configure(bg=BG())
        self._set_window_icon()

        # estado
        self.audio = LocalAudioEngine()
        self.lyrics = LyricSyncer()
        self._lyric_widgets = []
        self._lyric_scroll_target = 0.0
        self._lyric_scroll_current = 0.0
        self._auto_scroll = True
        self._current_track_id = None
        self._last_status = 'offline'
        self._sync_state = 'none'    # 'ok' | 'est' | 'none'
        self._fullscreen = False
        self._art_tk = None
        self._current_art_bytes = None  # bytes de la caratula actual (para re-render)
        self._current_track_info = ('-', '-', '-')  # (name, artist, album)
        self._theme_name = 'purple'
        self._anim_phase = 0.0
        self._n_bands = 48
        self._vis_bars = [0.0] * self._n_bands
        self._spectrum_mode = 'compact'   # 'compact' (arriba de controles) o 'large' (arriba de letras)
        self._lyric_style = 'classic'     # 'classic' (Courier monospace) o 'large' (proporcional grande)
        self._art_style = 'normal'        # 'normal' o 'crt' (efecto TV antigua)
        self._auto_theme = False          # elegir tema segun la portada de la cancion
        self._crt_bar_y = -60.0            # posicion vertical de la barra rodante CRT
        self._name_base_arr = None         # numpy RGB del reloj pre-renderizado
        self._name_text_mask = None        # numpy bool: True donde hay pixel
        self._name_canvas_dims = (280, 72)
        self._name_photo = None            # PhotoImage (kept alive)
        self._name_img_id = None
        self._clock_str = time.strftime('%H:%M:%S')  # hora dibujada en bloques
        self._spectrum_frames = None     # numpy array [n_frames, n_bands] o None
        self._spectrum_fps = 30
        self._spectrum_track_id = None
        self._spectrum_lock = threading.Lock()
        self._scale = 1.0
        self.username = 'User'
        # ---- mini player ----
        self._mini_mode = False
        self._mini_win = None
        self._mini_art_tk = None
        self._mini_compact = False
        self._mini_last_pos = None

        # cola UI (dispatch desde hilos)
        self._ui_queue = queue.Queue()
        self.after(50, self._process_ui_queue)

        # cargar credenciales
        creds = load_credentials() or {}
        theme = creds.get('theme', 'purple')
        lang = creds.get('lang', 'es')
        folder = creds.get('music_folder', '')
        self.username = creds.get('username', 'User')
        self._theme_name = theme
        self._spectrum_mode = creds.get('spectrum_mode', 'compact')
        self._lyric_style = creds.get('lyric_style', 'classic')
        self._art_style = creds.get('art_style', 'normal')
        self._auto_theme = bool(creds.get('auto_theme', False))
        # ---- config FL Studio (PRO) ----
        fl = creds.get('fl', {}) or {}
        self._fl_watch = bool(fl.get('watch', False))
        self._fl_export_folder = fl.get('export_folder', '')
        self._fl_samples_folder = fl.get('samples_folder', '')
        self._fl_autoplay = bool(fl.get('autoplay', True))
        self._fl_target_lufs = float(fl.get('target_lufs', -14.0))
        self._fl_seen = {}            # {path: (mtime, size)} para el watcher
        self._fl_pending = {}         # archivos en debounce de escritura
        self._fl_initialized = False  # primera pasada (no auto-cargar lo ya existente)
        self._last_analysis = None    # ultimo dict de analyze_audio
        self._studio_panel = None     # referencia a StudioPanel abierto
        global CURRENT_LANG
        CURRENT_LANG = lang
        apply_theme(theme)

        # build UI
        self._build_ui()
        self._set_titlebar_color()

        # carga inicial de biblioteca + samples PRO
        if ((folder and os.path.isdir(folder)) or
                (self._fl_samples_folder and os.path.isdir(self._fl_samples_folder))):
            threading.Thread(
                target=self._scan_config_folders_in_bg,
                args=(folder, self._fl_samples_folder),
                daemon=True,
            ).start()

        # binds
        self.bind('<Configure>', self._on_resize)
        self.bind('<F11>', self._toggle_fullscreen)
        self.bind('<Escape>', self._exit_fullscreen)
        self.bind('<space>', lambda e: self._play_pause())
        self.bind('<Right>', lambda e: self._next())
        self.bind('<Left>', lambda e: self._prev())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # El binding de clase de Canvas consume <space> para hacer scroll;
        # se elimina para que el evento llegue a la ventana raiz.
        self.unbind_class('Canvas', '<space>')
        self.bind('<Control-m>', self._toggle_mini_mode)
        self.bind('<Control-M>', self._toggle_mini_mode)

        # arrancar polling y animacion
        self._start_polling()
        self._animate()
        self._tick_clock()
        self._start_fl_watcher()

    # ------------------------------------------------------------------ UI dispatch
    def _ui_dispatch(self, fn, *a, **kw):
        self._ui_queue.put(('run', fn, a, kw))

    def _ui_dispatch_after(self, ms, fn, *a, **kw):
        self.after(ms, lambda: fn(*a, **kw))

    def _process_ui_queue(self):
        try:
            while True:
                tag, fn, a, kw = self._ui_queue.get_nowait()
                if tag == 'run':
                    try:
                        fn(*a, **kw)
                    except tk.TclError:
                        pass  # widget destruido durante rebuild
                    except Exception as e:
                        print('[ui]', e)
        except queue.Empty:
            pass
        try:
            self.after(50, self._process_ui_queue)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ Icono de ventana
    def _set_window_icon(self):
        # cuando esta congelado con PyInstaller (--onefile) los recursos viven en _MEIPASS
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        ico = os.path.join(base, 'icon.ico')
        png = os.path.join(base, 'icon.png')
        try:
            if os.path.exists(ico):
                self.iconbitmap(default=ico)
        except Exception:
            pass
        try:
            if PIL_AVAILABLE and os.path.exists(png):
                self._win_icon = ImageTk.PhotoImage(Image.open(png))
                self.iconphoto(True, self._win_icon)
        except Exception:
            pass

    # ------------------------------------------------------------------ Windows API
    def _set_titlebar_color(self):
        if sys.platform != 'win32':
            return
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            color_hex = BG().lstrip('#')
            r, g, b = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
            color = ctypes.c_int(b << 16 | g << 8 | r)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(color), ctypes.sizeof(color)
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ resize
    def _on_resize(self, event):
        if event.widget is self:
            self.after_idle(lambda: self._apply_dynamic_scale(event.width, event.height))

    def _apply_dynamic_scale(self, w, h):
        base_w, base_h = 1280, 780
        sx = w / base_w
        sy = h / base_h
        s = min(max(min(sx, sy), 0.7), 1.6)
        self._scale = s

    # ------------------------------------------------------------------ Build UI
    def _build_ui(self):
        self.configure(bg=BG())
        # contenedor superior
        self.main = tk.Frame(self, bg=BG())
        self.main.pack(fill='both', expand=True)
        # canvas fondo
        self.bg_canvas = tk.Canvas(self.main, bg=BG(), highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        # contenido
        self.content = tk.Frame(self.main, bg=BG())
        self.content.place(x=0, y=0, relwidth=1, relheight=1)
        # header
        self._build_header(self.content)
        # contenedor central
        center = tk.Frame(self.content, bg=BG())
        center.pack(fill='both', expand=True, padx=24, pady=(4, 0))
        # tres columnas
        self._build_left(center)
        self._build_middle(center)
        self._build_right(center)
        # barra inferior
        self._build_progressbar()

    def _build_header(self, p):
        hdr = tk.Frame(p, bg=BG())
        hdr.pack(fill='x', padx=24, pady=(14, 4))
        self.hdr = hdr

        self.title_lbl = tk.Label(
            hdr, text='UTMOST.FM',
            font=('Courier', 22, 'bold'), fg=MAIN_GLW(), bg=BG())
        self.title_lbl.pack(side='left')

        self.subtitle_lbl = tk.Label(
            hdr, text='█ PRO  ·  studio · compositor',
            font=('Courier', 9), fg=SEC_DIM(), bg=BG())
        self.subtitle_lbl.pack(side='left', padx=(10, 0), pady=(8, 0))

        # solo un punto indicador de estado, sin texto
        self.status_dot = tk.Label(
            hdr, text='●',
            font=('Courier', 14, 'bold'), fg=MAIN_DIM(), bg=BG())
        self.status_dot.pack(side='right', padx=(0, 4))

        # boton de ajustes en el header, estilo flat (mismo formato que controles)
        # Courier no tiene glifo decente para ⚙: usamos Segoe UI Symbol que si lo trae
        # entero sin recortes. Tamaño visual equivalente al anterior 12pt Courier.
        self.cfg_btn = tk.Label(
            hdr, text='⚙',
            font=('Segoe UI Symbol', 12),
            fg=MAIN(), bg=BG(),
            padx=6, pady=4, cursor='hand2',
            bd=0, relief=tk.FLAT, highlightthickness=0)
        self.cfg_btn.bind('<Button-1>', lambda e: self._show_config())
        self.cfg_btn.bind('<Enter>', lambda e: self.cfg_btn.configure(fg=MAIN_GLW()))
        self.cfg_btn.bind('<Leave>', lambda e: self.cfg_btn.configure(fg=MAIN()))
        self.cfg_btn.pack(side='right', padx=(0, 10))

        self.mini_mode_btn = tk.Label(
            hdr, text='▬',
            font=('Courier', 11),
            fg=MAIN(), bg=BG(),
            padx=6, pady=4, cursor='hand2',
            bd=0, relief=tk.FLAT, highlightthickness=0)
        self.mini_mode_btn.bind('<Button-1>', lambda e: self._toggle_mini_mode())
        self.mini_mode_btn.bind('<Enter>', lambda e: self.mini_mode_btn.configure(fg=MAIN_GLW()))
        self.mini_mode_btn.bind('<Leave>', lambda e: self.mini_mode_btn.configure(fg=MAIN()))
        self.mini_mode_btn.pack(side='right', padx=(0, 2))

    def _build_left(self, parent):
        col = tk.Frame(parent, bg=BG(), width=320)
        col.pack(side='left', fill='y', padx=(0, 12))
        col.pack_propagate(False)

        # caratula
        self.art_canvas = tk.Canvas(col, bg=CRUST(), highlightthickness=0,
                                    width=300, height=300)
        self.art_canvas.pack(pady=(8, 12))
        self._draw_default_art()

        # info pista
        self.track_name_lbl = tk.Label(col, text='-',
                                       font=('Courier', 13, 'bold'),
                                       fg=MAIN_GLW(), bg=BG(),
                                       wraplength=300, justify='left',
                                       anchor='w')
        self.track_name_lbl.pack(fill='x')
        self.track_artist_lbl = tk.Label(col, text='-',
                                         font=('Courier', 10),
                                         fg=SEC(), bg=BG(),
                                         wraplength=300, justify='left',
                                         anchor='w')
        self.track_artist_lbl.pack(fill='x', pady=(2, 0))
        self.track_album_lbl = tk.Label(col, text='-',
                                        font=('Courier', 8),
                                        fg=MUTED, bg=BG(),
                                        wraplength=300, justify='left',
                                        anchor='w')
        self.track_album_lbl.pack(fill='x', pady=(2, 8))

        # estado de reproduccion
        self.play_state_lbl = tk.Label(col, text=_T('stopped'),
                                       font=('Courier', 9, 'bold'),
                                       fg=MAIN_DIM(), bg=BG(),
                                       anchor='w')
        self.play_state_lbl.pack(fill='x', pady=(4, 6))

        # ====== ESPECTRO compacto encima de los controles (solo si modo=compact) ======
        if self._spectrum_mode == 'compact':
            self.vis_canvas = tk.Canvas(col, bg=CRUST(), highlightthickness=0,
                                        height=72)
            self.vis_canvas.pack(fill='x', pady=(2, 8))

        # botones de control: solo iconos, sin bordes ni fondos
        controls = tk.Frame(col, bg=BG())
        controls.pack(fill='x', pady=(2, 8))

        def _flat_btn(parent, text, cmd, font_size=14, base_fg=None):
            base = base_fg if base_fg is not None else MAIN()
            b = tk.Label(parent, text=text,
                         font=('Courier', font_size, 'bold'),
                         fg=base, bg=BG(),
                         padx=10, pady=6, cursor='hand2',
                         bd=0, relief=tk.FLAT, highlightthickness=0)
            b.bind('<Button-1>', lambda e: cmd())
            b.bind('<Enter>', lambda e: b.configure(fg=MAIN_GLW()))
            b.bind('<Leave>', lambda e: b.configure(fg=base))
            return b

        self.prev_btn = _flat_btn(controls, '⏮', self._prev, font_size=16)
        self.prev_btn.pack(side='left', expand=True, fill='x')

        self.play_btn = _flat_btn(controls, '⏵', self._play_pause, font_size=16)
        self.play_btn.pack(side='left', expand=True, fill='x')

        self.next_btn = _flat_btn(controls, '⏭', self._next, font_size=16)
        self.next_btn.pack(side='left', expand=True, fill='x')

        # volumen
        vol_row = tk.Frame(col, bg=BG())
        vol_row.pack(fill='x', pady=(6, 4))
        self.vol_lbl = tk.Label(vol_row, text=_T('vol') + '  70%',
                                font=('Courier', 9, 'bold'),
                                fg=SEC(), bg=BG(), anchor='w')
        self.vol_lbl.pack(fill='x')
        self.vol_slider = RetroVolumeSlider(col, command=self._set_volume)
        self.vol_slider.pack(fill='x', pady=(2, 4))
        self.vol_slider.set_level(0.7)

        # cola
        self._build_queue_section(col)

    def _build_queue_section(self, parent):
        sep = tk.Frame(parent, bg=SURFACE0(), height=1)
        sep.pack(fill='x', pady=(10, 8))
        tk.Label(parent, text=_T('queue_title'),
                 font=('Courier', 9, 'bold'),
                 fg=ACCENT(), bg=BG(), anchor='w').pack(fill='x')
        self.queue_frame = tk.Frame(parent, bg=BG())
        self.queue_frame.pack(fill='both', expand=True, pady=(6, 0))
        self.queue_empty_lbl = tk.Label(
            self.queue_frame, text=_T('queue_offline'),
            font=('Courier', 9), fg=MUTED, bg=BG(), anchor='w',
            justify='left')
        self.queue_empty_lbl.pack(fill='x', pady=(8, 0))

    def _apply_scrollbar_style(self):
        """Configura un estilo ttk personalizado segun el tema actual."""
        try:
            style = self._ttk_style
        except AttributeError:
            self._ttk_style = ttk.Style(self)
            style = self._ttk_style
        try:
            style.theme_use('clam')  # clam permite mas customizacion
        except Exception:
            pass
        style.configure('Utmost.Vertical.TScrollbar',
                        gripcount=0,
                        background=MAIN_DIM(),
                        darkcolor=CRUST(),
                        lightcolor=CRUST(),
                        troughcolor=MANTLE(),
                        bordercolor=CRUST(),
                        arrowcolor=MAIN(),
                        arrowsize=12,
                        relief='flat',
                        borderwidth=0)
        style.map('Utmost.Vertical.TScrollbar',
                  background=[('active', MAIN_GLW()), ('!active', MAIN_DIM())],
                  arrowcolor=[('active', MAIN_GLW()), ('!active', MAIN())])

    def _build_middle(self, parent):
        col = tk.Frame(parent, bg=BG())
        col.pack(side='left', fill='both', expand=True, padx=(0, 12))
        self._apply_scrollbar_style()

        # ====== ESPECTRO grande encima de letras (solo si modo=large) ======
        if self._spectrum_mode == 'large':
            tk.Label(col, text=_T('spectrum'),
                     font=('Courier', 9, 'bold'),
                     fg=MAIN(), bg=BG(), anchor='w').pack(fill='x', pady=(8, 2))
            self.vis_canvas = tk.Canvas(col, bg=CRUST(), highlightthickness=0,
                                        height=180)
            self.vis_canvas.pack(fill='x', pady=(0, 12))

        # letras
        self.lyric_label_title = tk.Label(col, text=_T('lyrics'),
                                          font=('Courier', 9, 'bold'),
                                          fg=MAIN(), bg=BG(), anchor='w')
        self.lyric_label_title.pack(fill='x', pady=(2, 2))

        self.sync_label = tk.Label(col, text=_T('sync_none'),
                                   font=('Courier', 8),
                                   fg=SEC_DIM(), bg=BG(), anchor='w')
        self.sync_label.pack(fill='x', pady=(0, 4))

        lyr_container = tk.Frame(col, bg=CRUST())
        lyr_container.pack(fill='both', expand=True, pady=(0, 4))
        self.lyric_canvas = tk.Canvas(lyr_container, bg=CRUST(),
                                      highlightthickness=0)
        self.lyric_canvas.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(lyr_container, orient='vertical',
                           style='Utmost.Vertical.TScrollbar',
                           command=self.lyric_canvas.yview)
        sb.pack(side='right', fill='y')
        self.lyric_canvas.configure(yscrollcommand=sb.set)
        self.lyric_inner = tk.Frame(self.lyric_canvas, bg=CRUST())
        self.lyric_inner_id = self.lyric_canvas.create_window(
            (0, 0), window=self.lyric_inner, anchor='nw'
        )
        self.lyric_inner.bind(
            '<Configure>',
            lambda e: self.lyric_canvas.configure(
                scrollregion=self.lyric_canvas.bbox('all')))
        # mantener el ancho del frame interior == ancho del canvas
        def _on_lyric_resize(e):
            self.lyric_canvas.itemconfigure(self.lyric_inner_id, width=e.width)
            # actualizar wraplength en modo large para que abarque todo el ancho
            if self._lyric_style == 'large':
                wrap = max(200, e.width - 60)
                for w in self._lyric_widgets:
                    try: w.configure(wraplength=wrap)
                    except Exception: pass
        self.lyric_canvas.bind('<Configure>', _on_lyric_resize)
        self.lyric_canvas.bind('<MouseWheel>', self._wheel)
        self.lyric_canvas.bind('<Button-4>', self._wheel)
        self.lyric_canvas.bind('<Button-5>', self._wheel)

        # toggle auto-scroll
        self.scroll_btn = tk.Label(col, text=_T('scroll_on'),
                                   font=('Courier', 8, 'bold'),
                                   fg=ACCENT(), bg=BG(), anchor='w',
                                   cursor='hand2')
        self.scroll_btn.pack(fill='x', pady=(2, 0))
        self.scroll_btn.bind('<Button-1>', lambda e: self._toggle_scroll())

        self._render_plain(_T('connect_lyric'))

    def _build_right(self, parent):
        col = tk.Frame(parent, bg=BG(), width=300)
        col.pack(side='left', fill='y')
        col.pack_propagate(False)
        self.right_col = col
        self._right_visible = True

        # user
        self.user_lbl = tk.Label(col, text=f'█ {self.username}',
                                 font=('Courier', 11, 'bold'),
                                 fg=MAIN(), bg=BG(), anchor='w')
        self.user_lbl.pack(fill='x', pady=(8, 4))
        # divider
        tk.Frame(col, bg=SURFACE0(), height=1).pack(fill='x', pady=4)
        # decorative info panel
        for txt, fnt, fg in [
            ('// SISTEMA RETRO //', ('Courier', 8, 'bold'), MAIN()),
            ('canal     :  local', ('Courier', 8), SEC()),
            ('bitrate   :  variable', ('Courier', 8), SEC()),
            ('motor     :  pygame.mixer', ('Courier', 8), SEC_DIM()),
            ('letras    :  lrclib + .lrc', ('Courier', 8), SEC_DIM()),
            ('', None, None),
        ]:
            if fnt is None:
                tk.Frame(col, bg=BG(), height=4).pack()
            else:
                tk.Label(col, text=txt, font=fnt, fg=fg, bg=BG(),
                         anchor='w').pack(fill='x', pady=1)

        tk.Frame(col, bg=SURFACE0(), height=1).pack(fill='x', pady=4)

        # nombre del usuario como arte ASCII en bloques (sobre canvas para soportar
        # el efecto CRT y las barras rodantes igual que la caratula)
        self.name_art_canvas = tk.Canvas(col, bg=BG(), highlightthickness=0,
                                         height=72, width=280)
        self.name_art_canvas.pack(pady=(10, 4))
        self._draw_name_art()
        tk.Label(col, text='UTMOST █ FM PRO  ·  studio edition',
                 font=('Courier', 7),
                 fg=MUTED, bg=BG(),
                 anchor='center').pack(fill='x', pady=(0, 6))

        tk.Frame(col, bg=SURFACE0(), height=1).pack(fill='x', pady=4)

        # ---- mini-readout STUDIO (clic -> panel completo) ----
        studio_box = tk.Frame(col, bg=CRUST(), cursor='hand2')
        studio_box.pack(fill='x', pady=(4, 4))
        studio_box.bind('<Button-1>', lambda e: self._show_studio_panel())
        self.studio_title_lbl = tk.Label(
            studio_box, text='FL ◉ STUDIO', font=('Courier', 8, 'bold'),
            fg=MAIN_GLW(), bg=CRUST(), anchor='w', cursor='hand2')
        self.studio_title_lbl.pack(fill='x', padx=6, pady=(4, 0))
        self.studio_mini_lbl = tk.Label(
            studio_box, text=_T('studio_none'), font=('Courier', 8),
            fg=MUTED, bg=CRUST(), anchor='w', justify='left', cursor='hand2')
        self.studio_mini_lbl.pack(fill='x', padx=6, pady=(0, 4))
        for w in (self.studio_title_lbl, self.studio_mini_lbl):
            w.bind('<Button-1>', lambda e: self._show_studio_panel())
        # si ya hay un analisis previo, mostrarlo
        if self._last_analysis:
            self._update_studio_readout(self._last_analysis)

        tk.Frame(col, bg=SURFACE0(), height=1).pack(fill='x', pady=4)

        # hint
        tk.Label(col,
                 text='█ espacio = play/pausa\n'
                      '█ ← →     = prev/next\n'
                      '█ F11      = fullscreen\n'
                      '█ click letra = saltar',
                 font=('Courier', 8), fg=MUTED, bg=BG(),
                 justify='left', anchor='w').pack(fill='x', pady=(8, 0))

    # ------------------------------------------------------------------ Progressbar
    def _build_progressbar(self):
        bar = tk.Frame(self.content, bg=BG())
        bar.pack(fill='x', side='bottom', padx=24, pady=(4, 12))
        self.time_now_lbl = tk.Label(bar, text='00:00',
                                     font=('Courier', 9, 'bold'),
                                     fg=SEC(), bg=BG(), width=6)
        self.time_now_lbl.pack(side='left')
        self.pb_canvas = tk.Canvas(bar, bg=CRUST(), highlightthickness=0,
                                   height=12)
        self.pb_canvas.pack(side='left', fill='x', expand=True, padx=8)
        self.pb_canvas.bind('<Configure>', lambda e: self._draw_progressbar())
        self.pb_canvas.bind('<Enter>', lambda e: self._pb_hover(True))
        self.pb_canvas.bind('<Leave>', lambda e: self._pb_hover(False))
        self.pb_canvas.bind('<Button-1>', self._on_seek)
        self._pb_hovered = False
        self.time_tot_lbl = tk.Label(bar, text='00:00',
                                     font=('Courier', 9, 'bold'),
                                     fg=SEC(), bg=BG(), width=6)
        self.time_tot_lbl.pack(side='left')

        # ---- toggle de columna derecha (mismo estilo flat que los transport buttons) ----
        self.side_toggle_btn = tk.Label(
            bar, text='»',
            font=('Courier', 16, 'bold'),
            fg=MAIN(), bg=BG(),
            padx=8, pady=2, cursor='hand2',
            bd=0, relief=tk.FLAT, highlightthickness=0)
        self.side_toggle_btn.bind('<Button-1>',
                                  lambda e: self._toggle_right_panel())
        self.side_toggle_btn.bind('<Enter>',
                                  lambda e: self.side_toggle_btn.configure(fg=MAIN_GLW()))
        self.side_toggle_btn.bind('<Leave>',
                                  lambda e: self.side_toggle_btn.configure(fg=MAIN()))
        self.side_toggle_btn.pack(side='left', padx=(8, 0))

    def _pb_hover(self, state):
        self._pb_hovered = state
        self._draw_progressbar()

    def _on_seek(self, event):
        # pygame.mixer no soporta seek con get_pos confiablemente para mp3
        # pero podemos intentar set_pos
        st = self.audio.get_state()
        if not st['item'] or not st['item']['duration_ms']:
            return
        w = max(1, self.pb_canvas.winfo_width())
        frac = max(0.0, min(1.0, event.x / w))
        target_ms = int(st['item']['duration_ms'] * frac)
        try:
            pygame.mixer.music.play(start=target_ms / 1000.0)
            self.audio._start_wall = time.time()
            self.audio._pause_offset_ms = target_ms
        except Exception as e:
            print('[seek]', e)

    def _draw_progressbar(self):
        c = self.pb_canvas
        c.delete('all')
        w = c.winfo_width(); h = c.winfo_height()
        if w < 2 or h < 2:
            return
        st = self.audio.get_state()
        dur = (st['item'] or {}).get('duration_ms') or 1
        prog = st['progress_ms'] or 0
        frac = max(0.0, min(1.0, prog / max(1, dur)))
        # carril
        c.create_rectangle(0, h // 2 - 2, w, h // 2 + 2,
                           fill=SURFACE0(), outline='')
        # avance
        c.create_rectangle(0, h // 2 - 2, int(w * frac), h // 2 + 2,
                           fill=MAIN_GLW(), outline='')
        if self._pb_hovered:
            c.create_oval(int(w * frac) - 5, h // 2 - 5,
                          int(w * frac) + 5, h // 2 + 5,
                          fill=ACCENT(), outline=MAIN_GLW())

    # ------------------------------------------------------------------ Caratula
    def _draw_default_art(self):
        c = self.art_canvas
        c.delete('all')
        c.configure(bg=CRUST())
        w, h = 300, 300
        # marco
        c.create_rectangle(2, 2, w - 2, h - 2, outline=MAIN_DK(), width=2)
        # grid
        grid_col = MAIN_DK()
        for i in range(0, w, 14):
            c.create_line(i, 0, i, h, fill=grid_col, width=1)
        for j in range(0, h, 14):
            c.create_line(0, j, w, j, fill=grid_col, width=1)
        # circulo centro
        cx, cy = w // 2, h // 2
        for r in range(10, 110, 12):
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          outline=MAIN_DIM(), width=1)
        # texto UTMOST.FM
        c.create_text(cx, cy - 10, text='UTMOST.FM',
                      font=('Courier', 16, 'bold'), fill=MAIN_GLW())
        c.create_text(cx, cy + 12, text='█ PRO █',
                      font=('Courier', 8, 'bold'), fill=ACCENT())

    def _load_album_art(self, art_bytes, track_id):
        if not PIL_AVAILABLE or not art_bytes:
            self._ui_dispatch(self._draw_default_art)
            return
        crt_mode = (self._art_style == 'crt')
        auto_theme = self._auto_theme
        def _bg():
            try:
                img = Image.open(io.BytesIO(art_bytes)).convert('RGB')
                img = img.resize((296, 296), Image.Resampling.LANCZOS)
                # tema automatico segun la portada (antes de aplicar el filtro CRT)
                if auto_theme:
                    theme = pick_theme_for_image(img)
                    if theme:
                        self._ui_dispatch(self._apply_auto_theme, theme, track_id)
                if crt_mode:
                    img = _apply_crt_filter(img)
                tk_img = ImageTk.PhotoImage(img)
                self._ui_dispatch(self._paint_art, tk_img, track_id)
            except Exception as e:
                print('[art]', e)
                self._ui_dispatch(self._draw_default_art)
        threading.Thread(target=_bg, daemon=True).start()

    def _apply_auto_theme(self, theme, track_id):
        """Aplica el tema detectado de la portada, si auto-tema esta activo y la pista sigue siendo
        la actual. El guard 'theme == self._theme_name' evita rebuilds en cascada."""
        if not self._auto_theme:
            return
        if track_id != self._current_track_id:
            return
        if theme == self._theme_name:
            return
        apply_theme(theme)
        self._theme_name = theme
        self._refresh_theme()

    def _paint_art(self, tk_img, track_id):
        if track_id != self._current_track_id:
            return
        self._art_tk = tk_img
        c = self.art_canvas
        c.delete('all')
        c.create_image(150, 150, image=tk_img, anchor='center')
        c.create_rectangle(2, 2, 298, 298, outline=MAIN_DK(), width=2)

    # ------------------------------------------------------------------ Letras
    def _lyric_font(self, distance=None):
        """Devuelve la tupla font (family, size, style) segun el modo y la distancia al activo.
        distance=None => base (sin highlight todavia, en _render_*)."""
        if self._lyric_style == 'large':
            family = 'Cambria'
            if distance is None:  return (family, 22)
            if distance == 0:     return (family, 30, 'bold')
            if distance == 1:     return (family, 26, 'bold')
            if distance == 2:     return (family, 24)
            return (family, 22)
        else:  # classic monospace
            if distance is None:  return ('Courier', 11)
            if distance == 0:     return ('Courier', 13, 'bold')
            if distance == 1:     return ('Courier', 12, 'bold')
            if distance == 2:     return ('Courier', 11)
            return ('Courier', 10)

    def _lyric_padding(self):
        return (12 if self._lyric_style == 'large' else 4)

    def _render_synced(self, lines):
        for w in self._lyric_widgets:
            try: w.destroy()
            except Exception: pass
        self._lyric_widgets = []
        if not lines:
            self._render_plain(_T('no_lyric'))
            return
        pad = self._lyric_padding()
        large = (self._lyric_style == 'large')
        wrap = 1400 if large else 600
        justify = 'left' if large else 'center'
        anchor  = 'w'    if large else 'center'
        padx    = 22     if large else 10
        for ln in lines:
            lbl = tk.Label(self.lyric_inner, text=ln['text'],
                           font=self._lyric_font(), fg=LYR_NORMAL(),
                           bg=CRUST(), wraplength=wrap,
                           justify=justify, anchor=anchor,
                           padx=padx, pady=pad, cursor='hand2')
            lbl.pack(fill='x')
            lbl._time = ln['time']
            # click-to-seek: saltar al momento de esa linea (estilo Spotify)
            lbl.bind('<Button-1>', lambda e, t=ln['time']: self._on_lyric_click(t))
            self._lyric_widgets.append(lbl)
        self._lyric_canvas_refresh()

    def _render_plain(self, text):
        for w in self._lyric_widgets:
            try: w.destroy()
            except Exception: pass
        self._lyric_widgets = []
        pad = self._lyric_padding()
        large = (self._lyric_style == 'large')
        wrap = 1400 if large else 600
        justify = 'left' if large else 'center'
        anchor  = 'w'    if large else 'center'
        padx    = 22     if large else 10
        for line in (text or '').splitlines():
            lbl = tk.Label(self.lyric_inner, text=line,
                           font=self._lyric_font(), fg=LYR_NORMAL(),
                           bg=CRUST(), wraplength=wrap,
                           justify=justify, anchor=anchor,
                           padx=padx, pady=pad)
            lbl.pack(fill='x')
            lbl._time = -1
            self._lyric_widgets.append(lbl)
        self._lyric_canvas_refresh()

    def _lyric_canvas_refresh(self):
        try:
            self.lyric_canvas.update_idletasks()
            self.lyric_canvas.configure(scrollregion=self.lyric_canvas.bbox('all'))
        except Exception:
            pass

    def _recolor_lyrics(self):
        for w in self._lyric_widgets:
            try:
                w.configure(bg=CRUST(), fg=LYR_NORMAL())
            except Exception:
                pass

    def _update_lyric_highlight(self):
        if not self._lyric_widgets:
            return
        st = self.audio.get_state()
        prog = st['progress_ms']
        dur = (st['item'] or {}).get('duration_ms') or 1
        if self.lyrics.has_synced:
            active = self.lyrics.get_active_synced(prog)
        else:
            active, _ = self.lyrics.get_active_plain(prog, dur)
        n = len(self._lyric_widgets)
        large = (self._lyric_style == 'large')
        for i, w in enumerate(self._lyric_widgets):
            d = abs(i - active)
            if d == 0:
                color = LYR_ACTIVE()
            elif d == 1:
                color = LYR_NEAR1()
            elif d == 2:
                color = LYR_NEAR2()
            else:
                color = LYR_NORMAL()
            font = self._lyric_font(d)
            # en modo GRANDE la linea activa lleva una franja con el color del tema
            if large and d == 0:
                bg_color = MAIN_DK()
                fg_color = MAIN_GLW()
            else:
                bg_color = CRUST()
                fg_color = color
            try:
                w.configure(fg=fg_color, bg=bg_color, font=font)
            except Exception:
                pass
        if self._auto_scroll and 0 <= active < n:
            self._scroll_to(self._lyric_widgets[active])

    def _on_lyric_click(self, time_ms):
        """Click en una linea de letra sincronizada -> salta a ese momento de la cancion."""
        if not self.lyrics.has_synced:
            return
        if time_ms is None or time_ms < 0:
            return
        # pequeño margen para entrar justo antes de que se cante la linea
        target = max(0, int(time_ms) - 150)
        threading.Thread(target=self.audio.seek_to, args=(target,), daemon=True).start()

    def _scroll_to(self, label):
        try:
            self.lyric_canvas.update_idletasks()
            ly = label.winfo_y()
            ch = self.lyric_canvas.winfo_height()
            sh = max(1, self.lyric_inner.winfo_height())
            target = max(0.0, min(1.0, (ly - ch / 2) / max(1, sh - ch)))
            self._lyric_scroll_target = target
        except Exception:
            pass

    def _smooth_scroll_loop(self):
        delta = self._lyric_scroll_target - self._lyric_scroll_current
        if abs(delta) > 0.001:
            self._lyric_scroll_current += delta * 0.15
            try:
                self.lyric_canvas.yview_moveto(self._lyric_scroll_current)
            except Exception:
                pass

    def _wheel(self, event):
        delta = 0
        if hasattr(event, 'delta') and event.delta:
            delta = -1 if event.delta > 0 else 1
        elif event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        try:
            self.lyric_canvas.yview_scroll(delta, 'units')
            self._lyric_scroll_current = self.lyric_canvas.yview()[0]
            self._lyric_scroll_target = self._lyric_scroll_current
        except Exception:
            pass

    def _toggle_scroll(self):
        self._auto_scroll = not self._auto_scroll
        self._update_scroll_btn()

    def _update_scroll_btn(self):
        self.scroll_btn.configure(
            text=_T('scroll_on') if self._auto_scroll else _T('scroll_off'),
            fg=ACCENT() if self._auto_scroll else MUTED,
        )

    # ------------------------------------------------------------------ Visualizador
    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip('#')
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    @staticmethod
    def _rgb_to_hex(r, g, b):
        return f'#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}'

    @classmethod
    def _mix(cls, c1, c2, t):
        r1, g1, b1 = cls._hex_to_rgb(c1)
        r2, g2, b2 = cls._hex_to_rgb(c2)
        return cls._rgb_to_hex(
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        )

    def _bar_color(self, t):
        """Color gradiente segun altura t (0=bajo, 1=arriba). Usa la paleta del tema."""
        # 0 -> MAIN_DK, 0.4 -> MAIN_DIM, 0.7 -> MAIN_GLW, 1.0 -> ACCENT
        if t < 0.4:
            return self._mix(MAIN_DK(), MAIN_DIM(), t / 0.4)
        elif t < 0.7:
            return self._mix(MAIN_DIM(), MAIN_GLW(), (t - 0.4) / 0.3)
        else:
            return self._mix(MAIN_GLW(), ACCENT(), (t - 0.7) / 0.3)

    def _draw_vis(self):
        c = self.vis_canvas
        c.delete('all')
        w = c.winfo_width(); h = c.winfo_height()
        if w < 4 or h < 4:
            return
        c.configure(bg=CRUST())
        # marco fino
        c.create_rectangle(0, 0, w - 1, h - 1, outline=MAIN_DK(), width=1)
        # grid sutil
        step = 12
        for x in range(0, w, step):
            c.create_line(x, 0, x, h, fill=T.get('GRID', MAIN_DK()))
        # scanline
        sl_y = int((self._anim_phase * 22) % h)
        c.create_line(0, sl_y, w, sl_y, fill=T.get('SCANLINE', BG()))

        st = self.audio.get_state()
        playing = st['is_playing']
        prog_ms = st['progress_ms']
        n = len(self._vis_bars)

        # === obtener targets reales del FFT precomputado, o fallback sintetico ===
        targets = None
        with self._spectrum_lock:
            if (self._spectrum_frames is not None
                    and self._spectrum_track_id == self._current_track_id):
                fps = self._spectrum_fps
                frame_idx = int((prog_ms / 1000.0) * fps)
                if 0 <= frame_idx < len(self._spectrum_frames):
                    targets = self._spectrum_frames[frame_idx]

        if targets is not None and playing:
            for i in range(n):
                t = float(targets[i]) if i < len(targets) else 0.0
                # smoothing
                self._vis_bars[i] += (t - self._vis_bars[i]) * 0.45
        else:
            # idle / loading: sintetico tenue
            for i in range(n):
                if playing:
                    target = (
                        0.20
                        + 0.20 * math.sin(self._anim_phase * 1.7 + i * 0.18)
                        + 0.10 * random.random()
                    )
                else:
                    target = 0.04 + 0.02 * math.sin(self._anim_phase + i * 0.3)
                self._vis_bars[i] += (target - self._vis_bars[i]) * 0.18

        # === pintar barras ===
        margin_x = 4
        bot = h - 3
        top = 3
        avail = bot - top
        usable = w - 2 * margin_x
        bw = max(1, usable // n - 1)
        gap = 1
        seg = 3  # alto de cada segmento
        for i in range(n):
            v = max(0.0, min(1.0, self._vis_bars[i]))
            bh = int(v * avail)
            x = margin_x + i * (bw + gap)
            if bh < 2:
                continue
            y_cursor = bot
            while y_cursor > bot - bh:
                y_next = max(bot - bh, y_cursor - seg)
                t = (bot - y_cursor) / max(1, bh)
                color = self._bar_color(t)
                c.create_rectangle(x, y_next, x + bw, y_cursor,
                                   fill=color, outline='')
                y_cursor = y_next - 1
            # punta
            cap_y = bot - bh
            c.create_rectangle(x, max(top, cap_y - 1),
                               x + bw, cap_y,
                               fill=ACCENT(), outline='')

    # ------------------------------------------------------------------ Animacion
    def _animate(self):
        self._anim_phase += 0.08
        try:
            if not self._mini_mode:
                self._draw_bg()
                self._draw_vis()
                self._draw_progressbar()
                self._smooth_scroll_loop()
                self._update_lyric_highlight()
                self._animate_art()
                self._update_carol_overlay()
            else:
                self._update_mini_player()
        except tk.TclError:
            pass  # widget destruido durante rebuild de tema
        except Exception as e:
            print('[anim]', e)
        try:
            self.after(40, self._animate)
        except tk.TclError:
            pass

    def _build_name_image(self):
        """Pre-renderiza el nombre como PIL.Image con su mascara de pixeles de texto.
        Guarda numpy arrays para que _animate_name_crt aplique las barras solo sobre los pixeles
        de las letras y no sobre el fondo."""
        self._name_base_arr = None
        self._name_text_mask = None
        self._name_canvas_dims = (280, 72)
        if not (PIL_AVAILABLE and AUDIO_FFT_AVAILABLE):
            return
        from PIL import ImageFont, ImageDraw
        text = render_name_block(self._clock_str)
        # buscar una fuente monospace embebida en Windows
        font = None
        for fname in ['cour.ttf', 'consola.ttf', 'consolas.ttf', 'lucon.ttf']:
            try:
                font = ImageFont.truetype(fname, 11)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        lines = text.split('\n')
        widths, heights = [], []
        for line in lines:
            try:
                bb = font.getbbox(line)
                widths.append(bb[2] - bb[0])
                heights.append(bb[3] - bb[1] + 2)
            except Exception:
                widths.append(len(line) * 6)
                heights.append(13)
        max_w = max(widths) if widths else 200
        total_h = sum(heights) if heights else 60
        pad = 10
        img_w = max(max_w + pad * 2, 200)
        img_h = max(total_h + pad * 2, 60)
        bg_rgb = self._hex_to_rgb(BG())
        fg_rgb = self._hex_to_rgb(ACCENT())
        base_img = Image.new('RGB', (img_w, img_h), bg_rgb)
        mask_img = Image.new('L', (img_w, img_h), 0)
        d_base = ImageDraw.Draw(base_img)
        d_mask = ImageDraw.Draw(mask_img)
        y = pad
        for i, line in enumerate(lines):
            x = (img_w - widths[i]) // 2
            d_base.text((x, y), line, fill=fg_rgb, font=font)
            d_mask.text((x, y), line, fill=255, font=font)
            y += heights[i]
        self._name_base_arr = np.array(base_img, dtype=np.uint8)
        self._name_text_mask = np.array(mask_img, dtype=np.uint8) > 128
        self._name_canvas_dims = (img_w, img_h)

    def _tick_clock(self):
        """Actualiza la hora dibujada en bloques cada segundo (solo re-renderiza si cambia)."""
        try:
            now = time.strftime('%H:%M:%S')
            if now != self._clock_str:
                self._clock_str = now
                self._draw_name_art()
        except Exception:
            pass
        try:
            self.after(1000, self._tick_clock)
        except tk.TclError:
            pass

    def _draw_name_art(self):
        """Pinta el reloj estatico (sin barras CRT) en su canvas."""
        try:
            c = self.name_art_canvas
        except AttributeError:
            return
        self._build_name_image()
        try:
            c.delete('all')
            c.configure(bg=BG())
            if self._name_base_arr is not None:
                w, h = self._name_canvas_dims
                c.configure(width=w, height=h)
                img = Image.fromarray(self._name_base_arr)
                self._name_photo = ImageTk.PhotoImage(img)
                self._name_img_id = c.create_image(0, 0, image=self._name_photo,
                                                   anchor='nw', tags='name_img')
            else:
                # fallback sin PIL/numpy: texto plano sobre el canvas
                w = int(c.cget('width'))
                h = int(c.cget('height'))
                c.create_text(w // 2, h // 2,
                              text=render_name_block(self._clock_str),
                              font=('Courier', 8, 'bold'),
                              fill=ACCENT(),
                              anchor='center', justify='center',
                              tags='name_img')
        except Exception:
            pass

    def _animate_name_crt(self):
        """Compone el frame del nombre con las barras enmascaradas por las letras."""
        if not (PIL_AVAILABLE and AUDIO_FFT_AVAILABLE):
            return
        if self._name_base_arr is None or self._name_text_mask is None:
            return
        try:
            c = self.name_art_canvas
            if not c.winfo_exists():
                return
        except Exception:
            return
        base = self._name_base_arr
        mask = self._name_text_mask
        h, w, _ = base.shape
        cycle = h + 20
        spacing = 8
        n_bars = cycle // spacing + 2
        bar_y = self._crt_bar_y

        # intensidad de barra por fila
        bar_int = np.zeros(h, dtype=np.float32)
        for i in range(1, n_bars):
            y = int((bar_y + i * spacing) % cycle - 10)
            if 0 <= y < h:
                bar_int[y] = 1.0
        # barra principal con penumbra (mismo perfil que el canvas grande)
        y_main = bar_y % cycle - 10
        for off in range(-3, 13):
            y = int(y_main + off)
            if 0 <= y < h:
                if 0 <= off < 9:
                    bar_int[y] = 1.0
                else:
                    bar_int[y] = max(bar_int[y], 0.5)

        # aplicar oscurecimiento solo donde el pixel pertenece a una letra
        darken = bar_int[:, None] * mask.astype(np.float32) * 0.92  # (h, w)
        arr = base.astype(np.float32) * (1.0 - darken[..., None])
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        try:
            img = Image.fromarray(arr)
            self._name_photo = ImageTk.PhotoImage(img)
            if hasattr(self, '_name_img_id') and self._name_img_id is not None:
                c.itemconfigure(self._name_img_id, image=self._name_photo)
            else:
                c.delete('all')
                self._name_img_id = c.create_image(0, 0, image=self._name_photo,
                                                   anchor='nw', tags='name_img')
        except Exception:
            pass

    def _draw_crt_pattern(self, canvas, base_y, height_target, width):
        """Pinta el patron de barritas rodantes sobre cualquier canvas en modo CRT."""
        try:
            if not canvas.winfo_exists():
                return
        except Exception:
            return
        cycle = max(40, height_target + 20)
        spacing = 8
        n_bars = cycle // spacing + 2
        try:
            canvas.delete('crt_bar')
            # patron denso de barritas finas de 1px
            for i in range(1, n_bars):
                y = (base_y + i * spacing) % cycle - 10
                canvas.create_rectangle(2, y, width - 2, y + 1,
                                        fill='#000000', outline='',
                                        tags='crt_bar')
            # barra principal con penumbras
            y = base_y % cycle - 10
            canvas.create_rectangle(2, y - 3, width - 2, y,
                                    fill='#0a0a0a', outline='', tags='crt_bar')
            canvas.create_rectangle(2, y, width - 2, y + 9,
                                    fill='#000000', outline='', tags='crt_bar')
            canvas.create_rectangle(2, y + 9, width - 2, y + 12,
                                    fill='#0a0a0a', outline='', tags='crt_bar')
        except Exception:
            pass

    def _animate_art(self):
        """Anima el patron rolling-shutter sobre la caratula (a ancho completo) y sobre el
        nombre del usuario (enmascarado: solo sobre los pixeles de las letras)."""
        if self._art_style != 'crt':
            return
        # avance compartido por todos los canvases (mismo ritmo visual)
        self._crt_bar_y = (self._crt_bar_y + 0.50) % 9999.0
        base = self._crt_bar_y

        # --- caratula 300x300: barras a ancho completo ---
        try:
            if self.art_canvas.winfo_exists():
                self._draw_crt_pattern(self.art_canvas, base, 300, 300)
        except Exception:
            pass

        # --- nombre del usuario: barras solo en los pixeles de las letras ---
        try:
            self._animate_name_crt()
        except Exception:
            pass

    # ------------------------------------------------------------------ Detalle Carol
    def _is_carol(self):
        return (self.username or '').strip().lower() == 'carol'

    def _heart_color(self, size):
        """Color del corazon segun su tamaño (profundidad) -> adapta al tema."""
        if size >= 16:
            return ACCENT()
        if size >= 13:
            return MAIN_GLW()
        if size >= 11:
            return MAIN()
        return MAIN_DIM()

    def _make_carol_overlay(self):
        """Ventana overlay transparente (click-through) para la lluvia de corazones."""
        try:
            ov = tk.Toplevel(self)
            ov.overrideredirect(True)
            ov.attributes('-topmost', True)
            key = '#0b0b0b'
            try:
                ov.attributes('-transparentcolor', key)
            except Exception:
                ov.destroy()
                return None
            ov.configure(bg=key)
            cv = tk.Canvas(ov, bg=key, highlightthickness=0, bd=0)
            cv.pack(fill='both', expand=True)
            ov._canvas = cv
            ov._parts = []
            return ov
        except Exception:
            return None

    def _update_carol_overlay(self):
        if self._mini_mode:
            ov = getattr(self, '_carol_overlay', None)
            if ov is not None:
                try: ov.withdraw()
                except Exception: pass
            return
        carol = self._is_carol()
        ov = getattr(self, '_carol_overlay', None)
        dialog_open = any(isinstance(ch, (ConfigWindow, StudioPanel)) and ch.winfo_exists()
                          for ch in self.winfo_children())
        if not carol:
            if ov is not None:
                try: ov.destroy()
                except Exception: pass
                self._carol_overlay = None
            return
        if dialog_open:
            if ov is not None:
                try: ov.withdraw()
                except Exception: pass
            return
        if ov is None or not ov.winfo_exists():
            ov = self._make_carol_overlay()
            self._carol_overlay = ov
            if ov is None:
                return
        try:
            if self.state() == 'iconic':
                ov.withdraw(); return
            x = self.winfo_rootx(); y = self.winfo_rooty()
            w = self.winfo_width(); h = self.winfo_height()
            if w < 8 or h < 8:
                return
            ov.deiconify()
            ov.geometry(f'{w}x{h}+{x}+{y}')
            ov.lift()
        except Exception:
            return
        self._draw_overlay_hearts(ov, w, h)

    def _draw_overlay_hearts(self, ov, w, h):
        cv = ov._canvas
        try:
            cv.delete('all')
        except Exception:
            return
        if not ov._parts:
            for _ in range(46):
                ov._parts.append({
                    'x': random.randint(0, max(1, w)),
                    'y': random.randint(-h, h),
                    'vy': random.uniform(1.4, 4.0),
                    'size': random.choice([10, 11, 12, 14, 16, 18]),
                    'sway': random.uniform(0, 6.28),
                })
        for p in ov._parts:
            p['y'] += p['vy']
            if p['y'] > h + 18:
                p['y'] = -18
                p['x'] = random.randint(0, max(1, w))
                p['vy'] = random.uniform(1.4, 4.0)
                p['size'] = random.choice([10, 11, 12, 14, 16, 18])
            sway = math.sin(self._anim_phase * 0.8 + p['sway']) * 6
            cv.create_text(p['x'] + sway, p['y'], text='♥',
                           font=('Courier', p['size']),
                           fill=self._heart_color(p['size']))

    def _draw_bg(self):
        c = self.bg_canvas
        c.delete('all')
        w = c.winfo_width(); h = c.winfo_height()
        if w < 4 or h < 4:
            return
        c.configure(bg=BG())
        # grid sutil
        step = 36
        for x in range(0, w, step):
            c.create_line(x, 0, x, h, fill=T.get('GRID', MANTLE()))
        for y in range(0, h, step):
            c.create_line(0, y, w, y, fill=T.get('GRID', MANTLE()))
        # scanline animada
        sl = int((self._anim_phase * 18) % h)
        c.create_line(0, sl, w, sl, fill=T.get('SCANLINE', BG()))
        # matrix dots
        random.seed(int(self._anim_phase * 3) & 0xff)
        for _ in range(40):
            x = random.randint(0, w)
            y = random.randint(0, h)
            col = T.get('MATRIX1', MAIN_GLW()) if random.random() < 0.4 else T.get('MATRIX2', MAIN_DK())
            c.create_text(x, y, text=random.choice('01█.'),
                          font=('Courier', 8), fill=col)
        random.seed()

    # ------------------------------------------------------------------ Hud
    def _update_hud(self, st):
        item = st.get('item')
        if not item:
            self.play_state_lbl.configure(text=_T('stopped'), fg=MAIN_DIM())
            try:
                self.play_btn.configure(text='⏵')
            except Exception:
                pass
            return
        if st['is_playing']:
            self.play_state_lbl.configure(text=_T('playing'), fg=MAIN_GLW())
            try:
                self.play_btn.configure(text='⏸')
            except Exception:
                pass
        else:
            self.play_state_lbl.configure(text=_T('paused'), fg=ACCENT())
            try:
                self.play_btn.configure(text='⏵')
            except Exception:
                pass
        # tiempos
        prog = st['progress_ms'] // 1000
        dur = (item['duration_ms'] or 0) // 1000
        def fmt(s):
            return f'{s // 60:02d}:{s % 60:02d}'
        self.time_now_lbl.configure(text=fmt(prog))
        self.time_tot_lbl.configure(text=fmt(dur))
        # volumen
        self.vol_lbl.configure(text=f'{_T("vol")}  {self.audio.volume}%')

    # ------------------------------------------------------------------ Controles
    def _play_pause(self):
        threading.Thread(target=self.audio.toggle_play, daemon=True).start()

    def _next(self):
        threading.Thread(target=self.audio.next_track, daemon=True).start()

    def _prev(self):
        threading.Thread(target=self.audio.prev_track, daemon=True).start()

    def _set_volume(self, val):
        self.audio.set_volume(val)

    # ------------------------------------------------------------------ Config
    def _show_config(self):
        creds = load_credentials() or {}
        _restored = [False]
        def _restore_focus(_e):
            if not _restored[0]:
                _restored[0] = True
                self.after(150, self.focus_force)
        cfg = ConfigWindow(
            self, self._on_config_saved,
            on_rescan=self._on_rescan_request,
            current_theme=self._theme_name,
            current_lang=CURRENT_LANG,
            current_folder=creds.get('music_folder', ''),
            current_user=self.username,
            current_spectrum=self._spectrum_mode,
            current_lyric=self._lyric_style,
            current_art=self._art_style,
            current_auto_theme=self._auto_theme,
            current_fl={
                'watch': self._fl_watch,
                'export_folder': self._fl_export_folder,
                'samples_folder': self._fl_samples_folder,
                'autoplay': self._fl_autoplay,
                'target_lufs': self._fl_target_lufs,
            },
        )
        cfg.bind('<Destroy>', _restore_focus)

    def _toggle_right_panel(self):
        """Oculta/expande la columna derecha (sistema retro / hints)."""
        try:
            if self._right_visible:
                self.right_col.pack_forget()
                self._right_visible = False
                self.side_toggle_btn.configure(text='«')
            else:
                self.right_col.pack(side='left', fill='y')
                self._right_visible = True
                self.side_toggle_btn.configure(text='»')
        except Exception:
            pass

    def _on_rescan_request(self, folder, done_cb):
        """Llamado desde el boton ⟳ del config. Re-escanea la carpeta en background."""
        def _bg():
            n = self.audio.scan_folder(folder)
            # actualizar UI principal
            self._ui_dispatch(self._set_status, 'online' if n else 'offline')
            self._ui_dispatch(self._update_queue_ui)
            # guardar la nueva ruta como ultima usada
            try:
                creds = load_credentials() or {}
                fl = creds.get('fl', {}) or {}
                if not fl:
                    fl = {
                        'watch': self._fl_watch,
                        'export_folder': self._fl_export_folder,
                        'samples_folder': self._fl_samples_folder,
                        'autoplay': self._fl_autoplay,
                        'target_lufs': self._fl_target_lufs,
                    }
                save_credentials(folder,
                                 creds.get('username', self.username),
                                 creds.get('theme', self._theme_name),
                                 creds.get('lang', CURRENT_LANG),
                                 creds.get('spectrum_mode', self._spectrum_mode),
                                 creds.get('lyric_style', self._lyric_style),
                                 creds.get('art_style', self._art_style),
                                 creds.get('auto_theme', self._auto_theme),
                                 fl)
            except Exception:
                pass
            # notificar al config
            try:
                self._ui_dispatch(done_cb, n)
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    def _on_config_saved(self, folder, user, theme, lang,
                         spectrum_mode='compact', lyric_style='classic',
                         art_style='normal', auto_theme=False, fl=None):
        was_mini = self._mini_mode
        was_compact = self._mini_compact
        if was_mini:
            self._exit_mini_mode()
        global CURRENT_LANG
        CURRENT_LANG = lang
        apply_theme(theme)
        self._theme_name = theme
        self._spectrum_mode = spectrum_mode
        self._lyric_style = lyric_style
        self._art_style = art_style
        self._auto_theme = bool(auto_theme)
        # aplicar config FL Studio
        fl = fl or {}
        self._fl_watch = bool(fl.get('watch', False))
        self._fl_export_folder = fl.get('export_folder', '')
        self._fl_samples_folder = fl.get('samples_folder', '')
        self._fl_autoplay = bool(fl.get('autoplay', True))
        self._fl_target_lufs = float(fl.get('target_lufs', -14.0))
        # reiniciar watcher: re-escanear desde cero las carpetas elegidas
        self._fl_seen = {}
        self._fl_pending = {}
        self._fl_initialized = False
        self.username = user or 'User'
        self.configure(bg=BG())
        self._refresh_theme()
        if ((folder and os.path.isdir(folder)) or
                (self._fl_samples_folder and os.path.isdir(self._fl_samples_folder))):
            threading.Thread(
                target=self._scan_config_folders_in_bg,
                args=(folder, self._fl_samples_folder),
                daemon=True,
            ).start()
        if was_mini:
            self._mini_compact = was_compact
            self.after(400, self._enter_mini_mode)

    def _refresh_theme(self):
        """Rebuild de toda la UI preservando estado (pista, caratula, letras, status, vol)."""
        # ---- snapshot del estado actual ----
        name, artist, album = self._current_track_info
        art_bytes = self._current_art_bytes
        track_id = self._current_track_id
        last_status = self._last_status
        sync_state = self._sync_state
        vol_level = self.audio.volume / 100.0
        auto_scroll = self._auto_scroll
        right_was_visible = getattr(self, '_right_visible', True)
        lyrics_snapshot = None
        if self.lyrics.has_synced:
            lyrics_snapshot = ('synced', list(self.lyrics.synced))
        elif self.lyrics.has_plain:
            lyrics_snapshot = ('plain', self.lyrics.plain)
        elif self._lyric_widgets:
            # texto generico (no_lyric / connect / search...)
            txt = '\n'.join(w.cget('text') for w in self._lyric_widgets)
            lyrics_snapshot = ('text', txt)

        # ---- destruir y reconstruir ----
        try:
            self.main.destroy()
        except Exception:
            pass
        self._lyric_widgets = []
        self._art_tk = None
        self._name_img_id = None        # se recrea cuando _draw_name_art repinta
        self._name_photo = None
        self._build_ui()
        self._set_titlebar_color()
        # restaurar visibilidad de la columna derecha
        if not right_was_visible:
            self._toggle_right_panel()

        # ---- restaurar ----
        self.user_lbl.configure(text=f'█ {self.username}')
        self._auto_scroll = auto_scroll
        self._update_scroll_btn()
        try:
            self.vol_slider.set_level(vol_level)
            self.vol_lbl.configure(text=f'{_T("vol")}  {self.audio.volume}%')
        except Exception:
            pass
        if track_id is not None:
            self._current_track_id = track_id
            self._current_track_info = (name, artist, album)
            self._set_track(name, artist, album, art_bytes, track_id)
        self._sync_state = sync_state
        self._refresh_sync_label_text()
        self._set_status(last_status)
        # restaurar letras
        if lyrics_snapshot:
            kind, payload = lyrics_snapshot
            if kind == 'synced':
                self.lyrics.set_synced(payload)
                self._render_synced(payload)
            elif kind == 'plain':
                self.lyrics.set_plain(payload)
                self._render_plain(payload)
            else:
                self._render_plain(payload)
        # refrescar cola
        self._update_queue_ui()

    # ------------------------------------------------------------------ Biblioteca
    def _same_folder(self, a, b):
        if not a or not b:
            return False
        try:
            return (
                os.path.normcase(os.path.abspath(a)) ==
                os.path.normcase(os.path.abspath(b))
            )
        except Exception:
            return False

    def _scan_config_folders_in_bg(self, folder, samples_folder=''):
        self._ui_dispatch(self._set_status, 'linking')
        n = 0
        if folder and os.path.isdir(folder):
            n += self.audio.scan_folder(folder)
        if (samples_folder and os.path.isdir(samples_folder) and
                not self._same_folder(folder, samples_folder)):
            n += self.audio.add_folder(samples_folder)
        self._ui_dispatch(self._set_status, 'online' if n else 'offline')
        self._ui_dispatch(self._update_queue_ui)
        if n and self.audio.current_idx < 0:
            self.audio.current_idx = 0

    def _scan_in_bg(self, folder):
        self._scan_config_folders_in_bg(folder)

    def _set_status(self, key):
        color = MAIN_GLW() if key == 'online' else (ACCENT() if key == 'linking' else MAIN_DIM())
        try:
            self.status_dot.configure(fg=color)
        except Exception:
            pass
        self._last_status = key

    # ------------------------------------------------------------------ Cola
    def _update_queue_ui(self):
        # limpiar
        for w in list(self.queue_frame.children.values()):
            try: w.destroy()
            except Exception: pass
        upcoming = self.audio.upcoming(8)
        if not upcoming:
            text = _T('queue_offline') if not self.audio.tracks else _T('queue_empty')
            self.queue_empty_lbl = tk.Label(
                self.queue_frame, text=text,
                font=('Courier', 9), fg=MUTED, bg=BG(),
                anchor='w', justify='left')
            self.queue_empty_lbl.pack(fill='x', pady=(8, 0))
            return
        for i, tr in enumerate(upcoming):
            row = tk.Frame(self.queue_frame, bg=BG())
            row.pack(fill='x', pady=2)
            tk.Label(row, text=f'{i+1:02d}',
                     font=('Courier', 8, 'bold'),
                     fg=MAIN_DIM(), bg=BG(), width=3, anchor='w').pack(side='left')
            tk.Label(row, text=tr['title'],
                     font=('Courier', 9), fg=SEC(), bg=BG(),
                     anchor='w').pack(side='left', fill='x', expand=True)
            tk.Label(row, text=tr['artist'],
                     font=('Courier', 8), fg=MUTED, bg=BG(),
                     anchor='e').pack(side='right')

    # ------------------------------------------------------------------ FL Studio watcher
    def _start_fl_watcher(self):
        """Hilo que vigila las carpetas export/samples de FL Studio cada ~1s."""
        def _watch():
            while True:
                try:
                    if self._fl_watch:
                        self._fl_poll_once()
                except Exception as e:
                    print('[fl]', e)
                time.sleep(1.0)
        threading.Thread(target=_watch, daemon=True).start()

    def _fl_scan_dir(self, folder):
        """Devuelve {path: (mtime, size)} de los audios de una carpeta (no recursivo)."""
        out = {}
        if not folder or not os.path.isdir(folder):
            return out
        try:
            for fn in os.listdir(folder):
                ext = os.path.splitext(fn)[1].lower()
                if ext in AUDIO_EXTS:
                    p = os.path.join(folder, fn)
                    try:
                        stt = os.stat(p)
                        out[p] = (stt.st_mtime, stt.st_size)
                    except OSError:
                        pass
        except OSError:
            pass
        return out

    def _fl_poll_once(self):
        exp = self._fl_scan_dir(self._fl_export_folder)
        smp = self._fl_scan_dir(self._fl_samples_folder)
        current = {}
        current.update({('export', p): v for p, v in exp.items()})
        current.update({('sample', p): v for p, v in smp.items()})

        # primera pasada: registrar lo que ya existe sin disparar nada
        if not self._fl_initialized:
            self._fl_seen = current
            self._fl_pending = {}
            self._fl_initialized = True
            return

        changed_exports = []
        new_samples = []
        for key, val in current.items():
            kind, path = key
            prev = self._fl_seen.get(key)
            if prev == val:
                continue  # sin cambios
            # cambio detectado -> debounce de escritura
            pend = self._fl_pending.get(key)
            if pend == val:
                # estable entre dos sondeos -> ya termino de escribirse
                if kind == 'export':
                    changed_exports.append((path, val))
                else:
                    new_samples.append(path)
                self._fl_pending.pop(key, None)
                self._fl_seen[key] = val
            else:
                # marcar pendiente, esperar al proximo sondeo para confirmar estabilidad
                self._fl_pending[key] = val

        # limpiar archivos desaparecidos
        for key in list(self._fl_seen.keys()):
            if key not in current:
                self._fl_seen.pop(key, None)

        # actuar: render mas reciente de export
        if changed_exports:
            latest = max(changed_exports, key=lambda pv: pv[1][0])[0]
            self._ui_dispatch(self._on_fl_export_changed, latest)
        if new_samples:
            self._ui_dispatch(self._on_fl_sample_added, new_samples)

    def _on_fl_export_changed(self, path):
        """Render nuevo/actualizado: auto-cargar, (auto)reproducir y analizar."""
        self._set_status('linking')
        ok = self.audio.load_external(path, autoplay=self._fl_autoplay)
        if not ok:
            return
        self._set_status('online')
        # el poll normal detectara la pista nueva y refrescara HUD/cola.
        # disparar analisis en background
        threading.Thread(target=self._run_analysis, args=(path,), daemon=True).start()

    def _on_fl_sample_added(self, paths):
        """Samples nuevos: añadir a la biblioteca sin interrumpir la reproduccion."""
        folder = self._fl_samples_folder
        if folder and os.path.isdir(folder):
            # re-escanea la carpeta de samples y la fusiona; scan_folder preserva la pista
            # actual. Para no perder la biblioteca principal, añadimos solo los nuevos.
            for p in paths:
                meta = _extract_metadata(p)
                with self.audio._lock:
                    if not any(t['path'] == p for t in self.audio.tracks):
                        self.audio.tracks.append(meta)
                        self.audio.queue_order.append(len(self.audio.tracks) - 1)
        self._fl_samples_added_count = getattr(self, '_fl_samples_added_count', 0) + len(paths)
        self._update_queue_ui()
        # aviso discreto en el readout de estado
        try:
            self._flash_studio_msg(_T('fl_samples_added') + str(len(paths)))
        except Exception:
            pass

    def _run_analysis(self, path):
        """Analiza el render en background y manda el resultado a la UI."""
        self._ui_dispatch(self._set_studio_analyzing)
        res = analyze_audio(path, target_lufs=self._fl_target_lufs)
        if res:
            self._last_analysis = res
            self._ui_dispatch(self._on_analysis_ready, res)

    # ------------------------------------------------------------------ Studio UI
    def _set_studio_analyzing(self):
        try:
            self.studio_mini_lbl.configure(text=_T('studio_analyzing'), fg=ACCENT())
            self.studio_title_lbl.configure(fg=ACCENT())
        except Exception:
            pass

    def _flash_studio_msg(self, msg):
        try:
            self.studio_mini_lbl.configure(text=msg, fg=MAIN_GLW())
        except Exception:
            pass

    def _on_analysis_ready(self, res):
        self._update_studio_readout(res)
        # actualizar panel si esta abierto
        if self._studio_panel is not None:
            try:
                if self._studio_panel.winfo_exists():
                    self._studio_panel.update_data(res)
            except Exception:
                self._studio_panel = None

    def _update_studio_readout(self, res):
        """Refresca el mini-readout del panel derecho con las metricas clave."""
        try:
            approx = ' approx' if res.get('lufs_approx') else ''
            lufs = res['lufs']; peak = res['true_peak_db']
            line1 = f"{lufs:+.1f} LUFS{approx}  ·  {peak:+.1f} dBTP"
            verdict = res['verdict']
            vtxt = _T('v_' + verdict) if ('v_' + verdict) in LANGS.get(CURRENT_LANG, {}) else ''
            self.studio_mini_lbl.configure(text=line1 + ('\n' + vtxt if vtxt else ''))
            # color segun veredicto
            if verdict in ('clip', 'phase'):
                col = PINK_ERR
            elif verdict in ('ok',):
                col = MAIN_GLW()
            else:
                col = ACCENT()
            self.studio_mini_lbl.configure(fg=col)
            self.studio_title_lbl.configure(fg=MAIN_GLW())
        except Exception as e:
            print('[studio]', e)

    def _show_studio_panel(self):
        if self._studio_panel is not None:
            try:
                if self._studio_panel.winfo_exists():
                    self._studio_panel.lift()
                    return
            except Exception:
                pass
        self._studio_panel = StudioPanel(self, self._last_analysis,
                                         on_export=self._export_optimized)

    def _export_optimized(self, src_path):
        """Genera la version normalizada del render actual en un hilo."""
        def _bg():
            out = normalize_export(src_path, target_lufs=self._fl_target_lufs)
            if out and self._studio_panel is not None:
                try:
                    self._ui_dispatch(self._studio_panel.on_exported, out)
                except Exception:
                    pass
        threading.Thread(target=_bg, daemon=True).start()

    # ------------------------------------------------------------------ Polling
    def _start_polling(self):
        def _poll():
            while True:
                try:
                    self._poll_once()
                except Exception as e:
                    print('[poll]', e)
                time.sleep(0.5)
        threading.Thread(target=_poll, daemon=True).start()

    def _poll_once(self):
        st = self.audio.get_state()
        item = st['item']
        if item:
            tid = item['id']
            if tid != self._current_track_id:
                self._current_track_id = tid
                self._ui_dispatch(self._set_track,
                                  item['name'], item['artists'][0]['name'],
                                  item['album']['name'], item.get('art_bytes'),
                                  tid)
                # disparar busqueda de letras
                threading.Thread(
                    target=self._fetch_all_lyrics,
                    args=(item['artists'][0]['name'], item['name'],
                          item['album']['name'],
                          (item['duration_ms'] or 0) // 1000, tid),
                    daemon=True
                ).start()
        else:
            if self._current_track_id is not None:
                self._current_track_id = None
                self._ui_dispatch(self._set_track, '-', '-', '-', None, None)
        # hud + queue refresh
        self._ui_dispatch(self._update_hud, st)
        # refrescar cola si cambio el indice
        self._ui_dispatch(self._update_queue_ui)

    def _set_track(self, name, artist, album, art_bytes, track_id):
        def truncate(t, limit):
            if not t: return '-'
            return t if len(t) <= limit else t[:limit - 1] + '…'
        self.track_name_lbl.configure(text=truncate(name or '-', 38))
        self.track_artist_lbl.configure(text=truncate(artist or '-', 42))
        self.track_album_lbl.configure(text=truncate(album or '-', 46))
        # guardamos para sobrevivir a un rebuild de UI (cambio de tema, idioma...)
        self._current_track_info = (name or '-', artist or '-', album or '-')
        self._current_art_bytes = art_bytes
        if art_bytes:
            self._load_album_art(art_bytes, track_id)
        else:
            self._draw_default_art()
        self._refresh_sync_label_text()
        # lanzar precompute del espectro reactivo en background
        if track_id and AUDIO_FFT_AVAILABLE:
            self._kick_spectrum_compute(track_id)
        # actualizar mini player si esta activo
        if self._mini_mode:
            try:
                n = (name or '-')
                a = (artist or '-')
                nl = 22 if self._mini_compact else 28
                al = 26 if self._mini_compact else 32
                self.mini_name_lbl.configure(
                    text=n[:nl] if len(n) <= nl else n[:nl - 1] + '…')
                self.mini_artist_lbl.configure(
                    text=a[:al] if len(a) <= al else a[:al - 1] + '…')
                if art_bytes:
                    self._load_mini_art(art_bytes)
                else:
                    self._draw_mini_default_art()
            except Exception:
                pass

    def _kick_spectrum_compute(self, track_id):
        with self._spectrum_lock:
            self._spectrum_frames = None
            self._spectrum_track_id = track_id
        def _bg():
            try:
                frames, fps = _compute_spectrum_frames(track_id, n_bands=self._n_bands, fps=30)
            except Exception as e:
                print('[fft]', e)
                return
            # solo aplica si la pista sigue siendo la actual
            with self._spectrum_lock:
                if self._spectrum_track_id == track_id and frames is not None:
                    self._spectrum_frames = frames
                    self._spectrum_fps = fps
        threading.Thread(target=_bg, daemon=True).start()

    def _refresh_sync_label_text(self):
        if self._sync_state == 'ok':
            self.sync_label.configure(text=_T('sync_ok'), fg=MAIN_GLW())
        elif self._sync_state == 'est':
            self.sync_label.configure(text=_T('sync_est'), fg=ACCENT())
        else:
            self.sync_label.configure(text=_T('sync_none'), fg=MUTED)

    # ------------------------------------------------------------------ Lyrics fetcher
    def _fetch_all_lyrics(self, artist, title, album, duration_s, track_id):
        # 1) Buscar .lrc al lado del archivo
        try:
            tr = self.audio.current_track()
            if tr:
                base, _ = os.path.splitext(tr['path'])
                lrc_path = base + '.lrc'
                if os.path.isfile(lrc_path):
                    with open(lrc_path, 'r', encoding='utf-8', errors='ignore') as f:
                        txt = f.read()
                    lines = parse_lrc(txt)
                    if lines:
                        self._ui_dispatch(self._on_synced, lines, track_id)
                        return
                txt_path = base + '.txt'
                if os.path.isfile(txt_path):
                    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                        txt = f.read()
                    self._ui_dispatch(self._on_plain, txt, 'local', track_id)
                    return
        except Exception:
            pass
        # 2) LRCLIB online
        self._ui_dispatch(self._set_searching, track_id)
        res = fetch_lrclib(artist, title, duration_s)
        if res and res.get('synced'):
            lines = parse_lrc(res['synced'])
            if lines:
                self._ui_dispatch(self._on_synced, lines, track_id)
                return
        if res and res.get('plain'):
            self._ui_dispatch(self._on_plain, res['plain'], 'lrclib', track_id)
            return
        # 3) search
        plain = fetch_plain_fallback(artist, title)
        if plain:
            self._ui_dispatch(self._on_plain, plain, 'search', track_id)
            return
        self._ui_dispatch(self._on_no_lyrics, track_id)

    def _set_searching(self, track_id):
        if track_id != self._current_track_id:
            return
        self.lyrics.clear()
        self._render_plain(_T('search_lyric'))
        self._sync_state = 'none'
        self._refresh_sync_label_text()

    def _on_synced(self, lines, track_id):
        if track_id != self._current_track_id:
            return
        self.lyrics.set_synced(lines)
        self._render_synced(lines)
        self._sync_state = 'ok'
        self._refresh_sync_label_text()

    def _on_plain(self, text, source, track_id):
        if track_id != self._current_track_id:
            return
        self.lyrics.set_plain(text)
        self._render_plain(text)
        self._sync_state = 'est'
        self._refresh_sync_label_text()

    def _on_no_lyrics(self, track_id):
        if track_id != self._current_track_id:
            return
        self.lyrics.clear()
        self._render_plain(_T('no_lyric'))
        self._sync_state = 'none'
        self._refresh_sync_label_text()

    # ------------------------------------------------------------------ Fullscreen
    def _toggle_fullscreen(self, event=None):
        self._fullscreen = not self._fullscreen
        try:
            self.attributes('-fullscreen', self._fullscreen)
        except Exception:
            self.state('zoomed' if self._fullscreen else 'normal')

    def _exit_fullscreen(self, event=None):
        if self._fullscreen:
            self._fullscreen = False
            try:
                self.attributes('-fullscreen', False)
            except Exception:
                self.state('normal')

    # ------------------------------------------------------------------ Mini Player
    def _toggle_mini_mode(self, event=None):
        if self._mini_mode:
            self._exit_mini_mode()
        else:
            self._enter_mini_mode()

    def _enter_mini_mode(self):
        if self._mini_mode:
            return
        self._mini_mode = True
        self.withdraw()
        self._build_mini_window()

    def _exit_mini_mode(self):
        if not self._mini_mode:
            return
        self._mini_mode = False
        try:
            if self._mini_win and self._mini_win.winfo_exists():
                self._mini_win.destroy()
        except Exception:
            pass
        self._mini_win = None
        self._mini_art_tk = None
        self.deiconify()
        self.focus_force()
        try:
            self.unbind_class('Canvas', '<space>')
        except Exception:
            pass

    def _build_mini_window(self):
        W, H = (220, 320) if self._mini_compact else (390, 110)
        win = tk.Toplevel(self)
        self._mini_win = win
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.configure(bg=MAIN_GLW())
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        if self._mini_last_pos:
            x, y = self._mini_last_pos
        else:
            x = sw - W - 20
            y = sh - H - 60
        win.geometry(f'{W}x{H}+{x}+{y}')
        win.resizable(False, False)

        inner = tk.Frame(win, bg=MANTLE())
        inner.pack(fill='both', expand=True, padx=1, pady=1)

        # ---- barra de titulo ----
        tbar = tk.Frame(inner, bg=CRUST(), height=26)
        tbar.pack(fill='x')
        tbar.pack_propagate(False)

        title_lbl = tk.Label(tbar, text='▬  UTMOST.FM PRO',
                             font=('Courier', 8, 'bold'),
                             fg=MAIN_GLW(), bg=CRUST())
        title_lbl.pack(side='left', padx=(10, 0))

        close_btn = tk.Label(tbar, text='✕', font=('Courier', 10, 'bold'),
                             fg=MAIN_DIM(), bg=CRUST(), cursor='hand2', padx=8)
        close_btn.pack(side='right')
        close_btn.bind('<Button-1>', lambda e: self._on_close())
        close_btn.bind('<Enter>', lambda e: close_btn.configure(fg=PINK_ERR))
        close_btn.bind('<Leave>', lambda e: close_btn.configure(fg=MAIN_DIM()))

        expand_btn = tk.Label(tbar, text='⤢', font=('Courier', 10, 'bold'),
                              fg=MAIN_DIM(), bg=CRUST(), cursor='hand2', padx=6)
        expand_btn.pack(side='right')
        expand_btn.bind('<Button-1>', lambda e: self._exit_mini_mode())
        expand_btn.bind('<Enter>', lambda e: expand_btn.configure(fg=MAIN_GLW()))
        expand_btn.bind('<Leave>', lambda e: expand_btn.configure(fg=MAIN_DIM()))

        # boton alternar modo compacto / extendido
        compact_sym = '⊞' if self._mini_compact else '⊟'
        cmp_btn = tk.Label(tbar, text=compact_sym, font=('Courier', 10, 'bold'),
                           fg=MAIN_DIM(), bg=CRUST(), cursor='hand2', padx=6)
        cmp_btn.pack(side='right')
        cmp_btn.bind('<Button-1>', lambda e: self._toggle_mini_compact())
        cmp_btn.bind('<Enter>', lambda e: cmp_btn.configure(fg=MAIN_GLW()))
        cmp_btn.bind('<Leave>', lambda e: cmp_btn.configure(fg=MAIN_DIM()))

        min_btn = tk.Label(tbar, text='─', font=('Courier', 10, 'bold'),
                           fg=MAIN_DIM(), bg=CRUST(), cursor='hand2', padx=6)
        min_btn.pack(side='right')
        min_btn.bind('<Button-1>', lambda e: win.iconify())
        min_btn.bind('<Enter>', lambda e: min_btn.configure(fg=MAIN_GLW()))
        min_btn.bind('<Leave>', lambda e: min_btn.configure(fg=MAIN_DIM()))

        for w in (tbar, title_lbl):
            w.bind('<Button-1>', self._mini_start_drag)
            w.bind('<B1-Motion>', self._mini_do_drag)

        tk.Frame(inner, bg=MAIN_GLW(), height=1).pack(fill='x')

        if self._mini_compact:
            self._build_mini_compact_body(inner)
        else:
            self._build_mini_wide_body(inner)

        win.bind('<space>', lambda e: self._play_pause())
        win.bind('<Right>', lambda e: self._next())
        win.bind('<Left>', lambda e: self._prev())
        win.bind('<Escape>', lambda e: self._exit_mini_mode())
        win.bind('<Control-m>', lambda e: self._exit_mini_mode())
        win.bind('<Control-M>', lambda e: self._exit_mini_mode())

    def _build_mini_wide_body(self, inner):
        """Cuerpo horizontal (modo extendido): portada + info + controles."""
        content = tk.Frame(inner, bg=BG())
        content.pack(fill='both', expand=True)

        self.mini_art_cv = tk.Canvas(
            content, bg=CRUST(),
            highlightthickness=1, highlightbackground=MAIN_DK(),
            width=72, height=72)
        self.mini_art_cv.pack(side='left', padx=(8, 8), pady=6)
        self._draw_mini_default_art()
        if self._current_art_bytes and PIL_AVAILABLE:
            self._load_mini_art(self._current_art_bytes)

        # controles primero para que expand no los aplaste
        ctrl = tk.Frame(content, bg=BG())
        ctrl.pack(side='right', padx=(4, 10))

        def _mb(par, sym, cmd, sz=12):
            b = tk.Label(par, text=sym, font=('Courier', sz, 'bold'),
                         fg=MAIN(), bg=BG(), cursor='hand2', padx=4)
            b.pack(side='left')
            b.bind('<Button-1>', lambda e: cmd())
            b.bind('<Enter>', lambda e, w=b: w.configure(fg=MAIN_GLW()))
            b.bind('<Leave>', lambda e, w=b: w.configure(fg=MAIN()))
            return b

        _mb(ctrl, '⏮', self._prev, sz=11)
        is_pl = self.audio.is_playing and not self.audio.is_paused
        self.mini_play_btn = _mb(ctrl, '⏸' if is_pl else '⏵', self._play_pause, sz=14)
        _mb(ctrl, '⏭', self._next, sz=11)

        info = tk.Frame(content, bg=BG())
        info.pack(side='left', fill='both', expand=True, pady=6)

        name, artist, _ = self._current_track_info
        self.mini_name_lbl = tk.Label(
            info,
            text=(name or '-')[:28] if len(name or '') <= 28 else (name or '')[:27] + '…',
            font=('Courier', 9, 'bold'),
            fg=MAIN_GLW(), bg=BG(), anchor='w')
        self.mini_name_lbl.pack(fill='x')

        self.mini_artist_lbl = tk.Label(
            info,
            text=(artist or '-')[:32] if len(artist or '') <= 32 else (artist or '')[:31] + '…',
            font=('Courier', 8),
            fg=SEC(), bg=BG(), anchor='w')
        self.mini_artist_lbl.pack(fill='x', pady=(2, 6))

        self.mini_pb_cv = tk.Canvas(
            info, bg=SURFACE0(), highlightthickness=0, height=4)
        self.mini_pb_cv.pack(fill='x')
        self.mini_pb_cv.bind('<Button-1>', self._on_mini_seek)
        self.mini_pb_cv.bind('<Configure>', lambda e: self._draw_mini_pb())

        for w in (content, info, ctrl):
            w.bind('<Button-1>', self._mini_start_drag)
            w.bind('<B1-Motion>', self._mini_do_drag)
        for w in (self.mini_name_lbl, self.mini_artist_lbl):
            w.bind('<Button-1>', self._mini_start_drag)
            w.bind('<B1-Motion>', self._mini_do_drag)

    def _build_mini_compact_body(self, inner):
        """Cuerpo vertical Spotify-style: portada grande + nombre + controles."""
        ART = 192
        content = tk.Frame(inner, bg=BG())
        content.pack(fill='both', expand=True)

        self.mini_art_cv = tk.Canvas(
            content, bg=CRUST(),
            highlightthickness=0,
            width=ART, height=ART)
        self.mini_art_cv.pack(pady=(8, 0), padx=((220 - ART) // 2))
        self._draw_mini_default_art()
        if self._current_art_bytes and PIL_AVAILABLE:
            self._load_mini_art(self._current_art_bytes)

        name, artist, _ = self._current_track_info

        self.mini_name_lbl = tk.Label(
            content,
            text=(name or '-')[:22] if len(name or '') <= 22 else (name or '')[:21] + '…',
            font=('Courier', 10, 'bold'),
            fg=MAIN_GLW(), bg=BG(), anchor='center', justify='center')
        self.mini_name_lbl.pack(fill='x', padx=10, pady=(10, 0))

        self.mini_artist_lbl = tk.Label(
            content,
            text=(artist or '-')[:26] if len(artist or '') <= 26 else (artist or '')[:25] + '…',
            font=('Courier', 8),
            fg=SEC(), bg=BG(), anchor='center', justify='center')
        self.mini_artist_lbl.pack(fill='x', padx=10, pady=(2, 6))

        self.mini_pb_cv = tk.Canvas(
            content, bg=SURFACE0(), highlightthickness=0, height=4)
        self.mini_pb_cv.pack(fill='x', padx=10, pady=(0, 6))
        self.mini_pb_cv.bind('<Button-1>', self._on_mini_seek)
        self.mini_pb_cv.bind('<Configure>', lambda e: self._draw_mini_pb())

        ctrl = tk.Frame(content, bg=BG())
        ctrl.pack(pady=(0, 10))

        def _mb(par, sym, cmd, sz=12):
            b = tk.Label(par, text=sym, font=('Courier', sz, 'bold'),
                         fg=MAIN(), bg=BG(), cursor='hand2', padx=8)
            b.pack(side='left')
            b.bind('<Button-1>', lambda e: cmd())
            b.bind('<Enter>', lambda e, w=b: w.configure(fg=MAIN_GLW()))
            b.bind('<Leave>', lambda e, w=b: w.configure(fg=MAIN()))
            return b

        _mb(ctrl, '⏮', self._prev, sz=12)
        is_pl = self.audio.is_playing and not self.audio.is_paused
        self.mini_play_btn = _mb(ctrl, '⏸' if is_pl else '⏵', self._play_pause, sz=16)
        _mb(ctrl, '⏭', self._next, sz=12)

        content.bind('<Button-1>', self._mini_start_drag)
        content.bind('<B1-Motion>', self._mini_do_drag)

    def _toggle_mini_compact(self):
        try:
            if self._mini_win and self._mini_win.winfo_exists():
                self._mini_last_pos = (self._mini_win.winfo_x(), self._mini_win.winfo_y())
                self._mini_win.destroy()
        except Exception:
            pass
        self._mini_win = None
        self._mini_compact = not self._mini_compact
        self._build_mini_window()

    def _update_mini_player(self):
        try:
            if not (self._mini_win and self._mini_win.winfo_exists()):
                return
            st = self.audio.get_state()
            item = st.get('item')
            if item:
                name = item.get('name', '-') or '-'
                artist = ((item.get('artists') or [{}])[0].get('name') or '-')
                n = name[:30] if len(name) <= 30 else name[:29] + '…'
                a = artist[:34] if len(artist) <= 34 else artist[:33] + '…'
                self.mini_name_lbl.configure(text=n)
                self.mini_artist_lbl.configure(text=a)
            is_pl = st.get('is_playing', False)
            self.mini_play_btn.configure(text='⏸' if is_pl else '⏵')
            self._draw_mini_pb(st)
        except Exception:
            pass

    def _draw_mini_pb(self, st=None):
        try:
            c = self.mini_pb_cv
            c.delete('all')
            w = c.winfo_width()
            if w < 4:
                return
            c.create_rectangle(0, 0, w, 4, fill=SURFACE0(), outline='')
            if st is None:
                st = self.audio.get_state()
            dur = ((st.get('item') or {}).get('duration_ms') or 1)
            prog = st.get('progress_ms', 0)
            frac = max(0.0, min(1.0, prog / max(1, dur)))
            if frac > 0.001:
                c.create_rectangle(0, 0, max(4, int(w * frac)), 4,
                                   fill=MAIN_GLW(), outline='')
        except Exception:
            pass

    def _draw_mini_default_art(self):
        try:
            c = self.mini_art_cv
            c.delete('all')
            c.configure(bg=CRUST())
            s = c.winfo_reqwidth()
            cx, cy = s // 2, s // 2
            for r in (int(s * f) for f in (0.08, 0.18, 0.28, 0.39)):
                c.create_oval(cx - r, cy - r, cx + r, cy + r,
                              outline=MAIN_DIM(), width=1)
            c.create_text(cx, cy, text='♪',
                          font=('Courier', max(10, s // 5)), fill=MAIN_GLW())
        except Exception:
            pass

    def _load_mini_art(self, art_bytes):
        if not PIL_AVAILABLE or not art_bytes:
            return
        crt = (self._art_style == 'crt')
        size = 192 if self._mini_compact else 72
        def _bg():
            try:
                img = Image.open(io.BytesIO(art_bytes)).convert('RGB')
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                if crt:
                    img = _apply_crt_filter(img)
                tk_img = ImageTk.PhotoImage(img)
                self._ui_dispatch(self._paint_mini_art, tk_img)
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    def _paint_mini_art(self, tk_img):
        try:
            if not (hasattr(self, 'mini_art_cv') and
                    self.mini_art_cv.winfo_exists()):
                return
            self._mini_art_tk = tk_img
            c = self.mini_art_cv
            s = c.winfo_reqwidth()
            c.delete('all')
            c.create_image(s // 2, s // 2, image=tk_img, anchor='center')
        except Exception:
            pass

    def _mini_start_drag(self, event):
        self._mini_drag_ox = event.x_root - self._mini_win.winfo_x()
        self._mini_drag_oy = event.y_root - self._mini_win.winfo_y()

    def _mini_do_drag(self, event):
        try:
            x = event.x_root - self._mini_drag_ox
            y = event.y_root - self._mini_drag_oy
            self._mini_win.geometry(f'+{x}+{y}')
        except Exception:
            pass

    def _on_mini_seek(self, event):
        try:
            w = max(1, self.mini_pb_cv.winfo_width())
            frac = max(0.0, min(1.0, event.x / w))
            st = self.audio.get_state()
            dur = ((st.get('item') or {}).get('duration_ms') or 0)
            if dur:
                target = int(dur * frac)
                pygame.mixer.music.play(start=target / 1000.0)
                self.audio._start_wall = time.time()
                self.audio._pause_offset_ms = target
        except Exception:
            pass

    def _on_close(self):
        """Cierre limpio: detener audio, destruir overlay y salir."""
        try:
            pygame.mixer.stop()
            pygame.mixer.quit()
        except Exception:
            pass
        try:
            ov = getattr(self, '_carol_overlay', None)
            if ov is not None:
                ov.destroy()
        except Exception:
            pass
        self.destroy()


# ==============================================================================
#   MAIN
# ==============================================================================
if __name__ == '__main__':
    app = SevenFMPlayer()
    app.mainloop()
