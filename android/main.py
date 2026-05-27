# -*- coding: utf-8 -*-
"""
UTMOST.FM MOBILE  -  Reproductor local retro-futurista para Android (Kivy).
Recrea la estetica y funciones de la version de escritorio: 10 temas, visualizador
de espectro, letras sincronizadas (LRCLIB + .lrc), efecto CRT, reloj de bloques.

Audio: MediaPlayer nativo de Android via pyjnius; en escritorio usa Kivy SoundLoader
(para previsualizar). Musica: escaneo del almacenamiento + selector de archivos.
"""
import os
import re
import math
import time
import json
import random
import threading
import urllib.parse
import urllib.request

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform, get_color_from_hex
from kivy.metrics import dp, sp
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image as KImage
from kivy.graphics import (Color, Rectangle, Line, Ellipse, RoundedRectangle,
                           PushMatrix, PopMatrix)
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty

# ------------------------------------------------------------------ deps opcionales
try:
    from mutagen import File as MutagenFile
    MUTAGEN = True
except Exception:
    MUTAGEN = False

IS_ANDROID = (platform == 'android')

# ==============================================================================
#   TEMAS (10) -- identicos a la version de escritorio
# ==============================================================================
THEMES = {
    'purple': {'name': 'MORADO', 'BG': '#0a0015', 'MANTLE': '#0f0020', 'CRUST': '#13002a',
               'SURFACE0': '#1e0040', 'SURFACE1': '#280055', 'MAIN': '#cba6f7',
               'MAIN_DIM': '#7c4fa0', 'MAIN_DK': '#3d1060', 'MAIN_GLW': '#a855f7',
               'SEC': '#b4befe', 'SEC_DIM': '#5a5a99', 'ACCENT': '#e879f9',
               'ACC_DIM': '#7a1a7a', 'GRID': '#110028', 'SCANLINE': '#0a0015'},
    'green': {'name': 'VERDE', 'BG': '#000e06', 'MANTLE': '#001a0a', 'CRUST': '#002810',
              'SURFACE0': '#003d18', 'SURFACE1': '#005220', 'MAIN': '#a3f7b5',
              'MAIN_DIM': '#3a9955', 'MAIN_DK': '#1a4d2a', 'MAIN_GLW': '#22dd66',
              'SEC': '#c8ffd4', 'SEC_DIM': '#4a8855', 'ACCENT': '#00ff99',
              'ACC_DIM': '#006633', 'GRID': '#001a08', 'SCANLINE': '#000e06'},
    'orange': {'name': 'NARANJA', 'BG': '#0f0800', 'MANTLE': '#1a0e00', 'CRUST': '#261500',
               'SURFACE0': '#3d2200', 'SURFACE1': '#522e00', 'MAIN': '#ffb347',
               'MAIN_DIM': '#a06020', 'MAIN_DK': '#5c3300', 'MAIN_GLW': '#ff8800',
               'SEC': '#ffd9a0', 'SEC_DIM': '#996633', 'ACCENT': '#ff5500',
               'ACC_DIM': '#7a2200', 'GRID': '#1a0e00', 'SCANLINE': '#0f0800'},
    'blue': {'name': 'AZUL', 'BG': '#00050f', 'MANTLE': '#000d1a', 'CRUST': '#001226',
             'SURFACE0': '#001f40', 'SURFACE1': '#002855', 'MAIN': '#89b4fa',
             'MAIN_DIM': '#3a6aaa', 'MAIN_DK': '#1a3d66', 'MAIN_GLW': '#4488ff',
             'SEC': '#b9d1fa', 'SEC_DIM': '#4466aa', 'ACCENT': '#00d4ff',
             'ACC_DIM': '#005566', 'GRID': '#000d1a', 'SCANLINE': '#00050f'},
    'rose': {'name': 'ROSA', 'BG': '#0f0008', 'MANTLE': '#1a0010', 'CRUST': '#260018',
             'SURFACE0': '#3d0028', 'SURFACE1': '#520035', 'MAIN': '#f7a8c4',
             'MAIN_DIM': '#aa4470', 'MAIN_DK': '#660040', 'MAIN_GLW': '#ff4488',
             'SEC': '#ffd6e8', 'SEC_DIM': '#995566', 'ACCENT': '#ff0066',
             'ACC_DIM': '#7a0033', 'GRID': '#1a0010', 'SCANLINE': '#0f0008'},
    'celeste': {'name': 'CELESTE', 'BG': '#000a14', 'MANTLE': '#001122', 'CRUST': '#001a33',
                'SURFACE0': '#00274d', 'SURFACE1': '#003566', 'MAIN': '#8be9fd',
                'MAIN_DIM': '#5ab0c2', 'MAIN_DK': '#2d6978', 'MAIN_GLW': '#66d9ff',
                'SEC': '#cceeff', 'SEC_DIM': '#80cce6', 'ACCENT': '#00bfff',
                'ACC_DIM': '#0080b3', 'GRID': '#001428', 'SCANLINE': '#000a14'},
    'aqua': {'name': 'AQUA', 'BG': '#000a08', 'MANTLE': '#001411', 'CRUST': '#00211c',
             'SURFACE0': '#00332b', 'SURFACE1': '#00473c', 'MAIN': '#a3f7eb',
             'MAIN_DIM': '#54b3a4', 'MAIN_DK': '#2a665d', 'MAIN_GLW': '#33ffdb',
             'SEC': '#b3fff0', 'SEC_DIM': '#4dccb6', 'ACCENT': '#00e6bc',
             'ACC_DIM': '#008068', 'GRID': '#001411', 'SCANLINE': '#000a08'},
    'red': {'name': 'ROJO', 'BG': '#0d0000', 'MANTLE': '#1a0000', 'CRUST': '#260000',
            'SURFACE0': '#400000', 'SURFACE1': '#590000', 'MAIN': '#ff8080',
            'MAIN_DIM': '#b33939', 'MAIN_DK': '#661414', 'MAIN_GLW': '#ff3333',
            'SEC': '#ffb3b3', 'SEC_DIM': '#cc6666', 'ACCENT': '#ff0000',
            'ACC_DIM': '#990000', 'GRID': '#1a0000', 'SCANLINE': '#0d0000'},
    'white': {'name': 'BLANCO', 'BG': '#050505', 'MANTLE': '#0d0d0d', 'CRUST': '#141414',
              'SURFACE0': '#242424', 'SURFACE1': '#333333', 'MAIN': '#e6e6e6',
              'MAIN_DIM': '#a6a6a6', 'MAIN_DK': '#595959', 'MAIN_GLW': '#ffffff',
              'SEC': '#f2f2f2', 'SEC_DIM': '#8c8c8c', 'ACCENT': '#cccccc',
              'ACC_DIM': '#666666', 'GRID': '#0d0d0d', 'SCANLINE': '#050505'},
    'dark': {'name': 'NEGRO', 'BG': '#000000', 'MANTLE': '#050505', 'CRUST': '#0a0a0a',
             'SURFACE0': '#141414', 'SURFACE1': '#1f1f1f', 'MAIN': '#999999',
             'MAIN_DIM': '#666666', 'MAIN_DK': '#333333', 'MAIN_GLW': '#b3b3b3',
             'SEC': '#777777', 'SEC_DIM': '#444444', 'ACCENT': '#888888',
             'ACC_DIM': '#444444', 'GRID': '#050505', 'SCANLINE': '#000000'},
}
SUBTEXT = '#a6adc8'; MUTED = '#585b70'; PINK_ERR = '#f38ba8'

T = dict(THEMES['purple'])


def C(key):
    """Color del tema actual como rgba (floats) para Kivy."""
    return get_color_from_hex(T.get(key, '#ffffff'))


def apply_theme(name):
    global T
    if name in THEMES:
        T = dict(THEMES[name])


# ==============================================================================
#   TRADUCCIONES
# ==============================================================================
LANGS = {
    'es': {
        'track': 'PISTA', 'artist': 'ARTISTA', 'spectrum': 'ESPECTRO',
        'lyrics': 'LETRAS', 'queue': 'SIGUIENTE', 'settings': 'AJUSTES',
        'theme': 'TEMA', 'lang': 'IDIOMA', 'scan': 'ESCANEAR ALMACENAMIENTO',
        'pick': 'ELEGIR ARCHIVOS', 'no_lyrics': 'letra no disponible',
        'searching': 'buscando letra...', 'empty': 'biblioteca vacia',
        'playing': 'reproduciendo', 'paused': 'pausado', 'stopped': 'detenido',
        'art_crt': 'PORTADA CRT', 'on': 'ON', 'off': 'OFF', 'close': 'CERRAR',
        'scanning': 'escaneando...', 'found': 'pistas: ',
    },
    'en': {
        'track': 'TRACK', 'artist': 'ARTIST', 'spectrum': 'SPECTRUM',
        'lyrics': 'LYRICS', 'queue': 'UP NEXT', 'settings': 'SETTINGS',
        'theme': 'THEME', 'lang': 'LANGUAGE', 'scan': 'SCAN STORAGE',
        'pick': 'PICK FILES', 'no_lyrics': 'lyrics not available',
        'searching': 'searching lyrics...', 'empty': 'empty library',
        'playing': 'playing', 'paused': 'paused', 'stopped': 'stopped',
        'art_crt': 'CRT ART', 'on': 'ON', 'off': 'OFF', 'close': 'CLOSE',
        'scanning': 'scanning...', 'found': 'tracks: ',
    },
}
CURRENT_LANG = 'es'


def _T(k):
    return LANGS.get(CURRENT_LANG, LANGS['es']).get(k, k)


# ==============================================================================
#   ALMACENAMIENTO DE CONFIG
# ==============================================================================
def _data_dir():
    if IS_ANDROID:
        try:
            from android.storage import app_storage_path
            d = app_storage_path()
        except Exception:
            d = os.path.expanduser('~')
    else:
        d = os.path.join(os.path.expanduser('~'), '.utmostfm_mobile')
    os.makedirs(d, exist_ok=True)
    return d


CFG_FILE = os.path.join(_data_dir(), 'config.json')


def save_cfg(data):
    try:
        with open(CFG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass


def load_cfg():
    try:
        with open(CFG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


# ==============================================================================
#   LETRAS (.lrc + LRCLIB via urllib)
# ==============================================================================
_LRC_RE = re.compile(r'\[(\d+):(\d+)(?:\.(\d+))?\](.*)')


def parse_lrc(text):
    out = []
    for raw in (text or '').splitlines():
        m = _LRC_RE.match(raw.strip())
        if not m:
            continue
        mm, ss, fr, txt = m.groups()
        ms = int(mm) * 60000 + int(ss) * 1000 + (int(fr[:3].ljust(3, '0')) if fr else 0)
        txt = txt.strip()
        if txt:
            out.append({'time': ms, 'text': txt})
    out.sort(key=lambda x: x['time'])
    return out


def fetch_lrclib(artist, title, dur=None):
    base = 'https://lrclib.net/api/get'
    params = {'artist_name': artist or '', 'track_name': title or ''}
    if dur:
        params['duration'] = int(dur)
    url = base + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'UtmostFM-Mobile'})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode('utf-8'))
            return {'synced': data.get('syncedLyrics') or '',
                    'plain': data.get('plainLyrics') or ''}
    except Exception:
        # fallback: search
        try:
            surl = 'https://lrclib.net/api/search?' + urllib.parse.urlencode(
                {'track_name': title or '', 'artist_name': artist or ''})
            req2 = urllib.request.Request(surl, headers={'User-Agent': 'UtmostFM-Mobile'})
            with urllib.request.urlopen(req2, timeout=12) as r:
                arr = json.loads(r.read().decode('utf-8'))
                if isinstance(arr, list) and arr:
                    best = next((e for e in arr if e.get('syncedLyrics')), arr[0])
                    return {'synced': best.get('syncedLyrics') or '',
                            'plain': best.get('plainLyrics') or ''}
        except Exception:
            pass
    return None


# ==============================================================================
#   MOTOR DE AUDIO  (Android MediaPlayer / desktop SoundLoader)
# ==============================================================================
AUDIO_EXTS = {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus', '.wma'}


def extract_meta(path):
    info = {'path': path, 'title': os.path.splitext(os.path.basename(path))[0],
            'artist': 'Desconocido', 'album': '', 'duration_ms': 0, 'art': None}
    if not MUTAGEN:
        return info
    try:
        mf = MutagenFile(path)
        if mf is None:
            return info
        try:
            info['duration_ms'] = int(mf.info.length * 1000)
        except Exception:
            pass

        def g(*keys):
            for k in keys:
                v = mf.tags.get(k) if mf.tags else None
                if v:
                    return str(v[0] if isinstance(v, list) else v).strip()
            return None
        info['title'] = g('TIT2', 'title', '\xa9nam') or info['title']
        info['artist'] = g('TPE1', 'artist', '\xa9ART') or info['artist']
        info['album'] = g('TALB', 'album', '\xa9alb') or ''
        art = None
        if getattr(mf, 'tags', None):
            for k in list(mf.tags.keys()):
                if k.startswith('APIC'):
                    art = mf.tags[k].data
                    break
            if art is None and hasattr(mf, 'pictures') and mf.pictures:
                art = mf.pictures[0].data
            if art is None:
                covr = mf.tags.get('covr') if hasattr(mf.tags, 'get') else None
                if covr:
                    art = bytes(covr[0])
        info['art'] = art
    except Exception:
        pass
    return info


class AudioEngine:
    def __init__(self):
        self.tracks = []
        self.idx = -1
        self.volume = 0.8
        self._mp = None         # Android MediaPlayer
        self._snd = None        # desktop Sound
        self.is_playing = False
        self._dur_ms = 0

    # --- biblioteca ---
    def set_tracks(self, tracks):
        self.tracks = tracks
        if tracks and self.idx < 0:
            self.idx = 0

    def current(self):
        if 0 <= self.idx < len(self.tracks):
            return self.tracks[self.idx]
        return None

    # --- reproduccion ---
    def _stop_backends(self):
        try:
            if self._mp:
                self._mp.stop(); self._mp.release(); self._mp = None
        except Exception:
            self._mp = None
        try:
            if self._snd:
                self._snd.stop(); self._snd = None
        except Exception:
            self._snd = None

    def play(self, idx=None):
        if idx is not None:
            self.idx = idx
        tr = self.current()
        if not tr:
            return
        self._stop_backends()
        self._dur_ms = tr.get('duration_ms', 0)
        if IS_ANDROID:
            try:
                from jnius import autoclass
                MediaPlayer = autoclass('android.media.MediaPlayer')
                self._mp = MediaPlayer()
                self._mp.setDataSource(tr['path'])
                self._mp.prepare()
                self._mp.setVolume(self.volume, self.volume)
                self._mp.start()
                if not self._dur_ms:
                    self._dur_ms = self._mp.getDuration()
                self.is_playing = True
                return
            except Exception as e:
                print('[audio-android]', e)
        # desktop / fallback
        try:
            from kivy.core.audio import SoundLoader
            self._snd = SoundLoader.load(tr['path'])
            if self._snd:
                self._snd.volume = self.volume
                self._snd.play()
                if not self._dur_ms and self._snd.length:
                    self._dur_ms = int(self._snd.length * 1000)
                self.is_playing = True
        except Exception as e:
            print('[audio-desktop]', e)

    def toggle(self):
        tr = self.current()
        if not tr:
            return
        if self._mp:
            try:
                if self._mp.isPlaying():
                    self._mp.pause(); self.is_playing = False
                else:
                    self._mp.start(); self.is_playing = True
                return
            except Exception:
                pass
        if self._snd:
            try:
                if self.is_playing:
                    self._snd.stop(); self.is_playing = False
                else:
                    self._snd.play(); self.is_playing = True
                return
            except Exception:
                pass
        self.play()

    def next(self):
        if self.tracks:
            self.play((self.idx + 1) % len(self.tracks))

    def prev(self):
        if self.tracks:
            self.play((self.idx - 1) % len(self.tracks))

    def seek_ms(self, ms):
        ms = max(0, int(ms))
        if self._mp:
            try:
                self._mp.seekTo(ms); self.is_playing = True; return
            except Exception:
                pass
        if self._snd:
            try:
                self._snd.seek(ms / 1000.0); self.is_playing = True
            except Exception:
                pass

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        if self._mp:
            try: self._mp.setVolume(self.volume, self.volume)
            except Exception: pass
        if self._snd:
            try: self._snd.volume = self.volume
            except Exception: pass

    def pos_ms(self):
        if self._mp:
            try: return int(self._mp.getCurrentPosition())
            except Exception: return 0
        if self._snd:
            try: return int((self._snd.get_pos() or 0) * 1000)
            except Exception: return 0
        return 0

    def dur_ms(self):
        return self._dur_ms or 1

    def poll_end(self):
        """Avanza al terminar la pista."""
        if not self.is_playing:
            return
        if self._mp:
            try:
                if not self._mp.isPlaying() and self._mp.getCurrentPosition() >= self._dur_ms - 400:
                    self.next()
            except Exception:
                pass


# ==============================================================================
#   ESCANEO DE MUSICA
# ==============================================================================
def scan_storage_dirs():
    cands = []
    if IS_ANDROID:
        cands = ['/sdcard/Music', '/sdcard/Download', '/storage/emulated/0/Music',
                 '/storage/emulated/0/Download', '/storage/emulated/0']
    else:
        home = os.path.expanduser('~')
        cands = [os.path.join(home, 'Music'), os.path.join(home, 'Downloads')]
    seen = set()
    found = []
    for d in cands:
        if not d or not os.path.isdir(d) or d in seen:
            continue
        seen.add(d)
        for root, _dirs, files in os.walk(d):
            for fn in files:
                if os.path.splitext(fn)[1].lower() in AUDIO_EXTS:
                    found.append(os.path.join(root, fn))
            if len(found) > 2000:
                break
    return found


def request_android_perms():
    if not IS_ANDROID:
        return
    try:
        from android.permissions import request_permissions, Permission
        perms = [Permission.READ_EXTERNAL_STORAGE]
        for extra in ('READ_MEDIA_AUDIO',):
            if hasattr(Permission, extra):
                perms.append(getattr(Permission, extra))
        request_permissions(perms)
    except Exception as e:
        print('[perms]', e)


# ==============================================================================
#   WIDGETS DE UI
# ==============================================================================
def _hex_lerp(c1, c2, t):
    a = get_color_from_hex(c1); b = get_color_from_hex(c2)
    return [a[i] + (b[i] - a[i]) * t for i in range(4)]


class RetroBackground(Widget):
    """Fondo: color base + grid sutil + scanline animada."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.phase = 0.0
        self.bind(pos=self._redraw, size=self._redraw)

    def tick(self, dt):
        self.phase += dt * 18
        self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(*C('BG'))
            Rectangle(pos=self.pos, size=self.size)
            # grid
            Color(*C('GRID'))
            step = dp(36)
            x = self.x
            while x < self.right:
                Line(points=[x, self.y, x, self.top], width=1)
                x += step
            y = self.y
            while y < self.top:
                Line(points=[self.x, y, self.right, y], width=1)
                y += step
            # scanline
            Color(*C('SCANLINE'))
            sy = self.y + (self.phase % max(1, self.height))
            Line(points=[self.x, sy, self.right, sy], width=1.4)


class AlbumArt(Widget):
    """Caratula: textura o arte por defecto, con overlay CRT (scanlines + barra rodante)."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.texture = None
        self.crt = False
        self.bar_y = 0.0
        self.bind(pos=self._redraw, size=self._redraw)

    def set_art_bytes(self, data):
        self.texture = None
        if data:
            try:
                import io
                from kivy.core.image import Image as CoreImage
                ext = 'png' if data[:4] == b'\x89PNG' else 'jpg'
                self.texture = CoreImage(io.BytesIO(data), ext=ext).texture
            except Exception as e:
                print('[art]', e)
        self._redraw()

    def tick(self, dt):
        if self.crt:
            self.bar_y = (self.bar_y + dt * 26) % max(1, self.height)
            self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            # marco
            Color(*C('CRUST'))
            Rectangle(pos=self.pos, size=self.size)
            if self.texture:
                Color(1, 1, 1, 1)
                Rectangle(texture=self.texture, pos=(self.x + dp(3), self.y + dp(3)),
                          size=(self.width - dp(6), self.height - dp(6)))
            else:
                # arte por defecto: circulos concentricos + texto
                Color(*C('MAIN_DK'))
                cx, cy = self.center
                r = min(self.width, self.height) * 0.42
                k = 6
                while k > 0:
                    rr = r * k / 6.0
                    Line(circle=(cx, cy, rr), width=1)
                    k -= 1
                Color(*C('MAIN_GLW'))
                Line(rectangle=(self.x + 2, self.y + 2, self.width - 4, self.height - 4), width=1.5)
            # borde
            Color(*C('MAIN_DK'))
            Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1.5))
            if self.crt:
                # scanlines
                Color(0, 0, 0, 0.22)
                yy = self.y
                while yy < self.top:
                    Rectangle(pos=(self.x, yy), size=(self.width, dp(1)))
                    yy += dp(3)
                # tren de barras rodantes
                base = self.top - self.bar_y
                for off, h, alpha in [(0, dp(7), 0.85), (-dp(22), dp(2), 0.5),
                                      (dp(22), dp(2), 0.5), (-dp(44), dp(1.5), 0.35),
                                      (dp(44), dp(1.5), 0.35)]:
                    Color(0, 0, 0, alpha)
                    Rectangle(pos=(self.x, base + off), size=(self.width, h))


class Spectrum(Widget):
    """Visualizador de barras (animado; reacciona al estado de reproduccion)."""
    def __init__(self, n=28, **kw):
        super().__init__(**kw)
        self.n = n
        self.vals = [0.05] * n
        self.phase = 0.0
        self.playing = False
        self.bind(pos=self._redraw, size=self._redraw)

    def tick(self, dt):
        self.phase += dt * 4
        for i in range(self.n):
            if self.playing:
                target = (0.35 + 0.3 * math.sin(self.phase * 1.7 + i * 0.5)
                          + 0.2 * math.sin(self.phase * 0.9 + i * 0.27)
                          + 0.15 * random.random())
            else:
                target = 0.05 + 0.03 * math.sin(self.phase + i * 0.3)
            self.vals[i] += (max(0.02, min(1.0, target)) - self.vals[i]) * 0.3
        self._redraw()

    def _bar_color(self, t):
        if t < 0.45:
            return _hex_lerp(T['MAIN_DK'], T['MAIN_DIM'], t / 0.45)
        if t < 0.75:
            return _hex_lerp(T['MAIN_DIM'], T['MAIN_GLW'], (t - 0.45) / 0.3)
        return _hex_lerp(T['MAIN_GLW'], T['ACCENT'], (t - 0.75) / 0.25)

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(*C('CRUST'))
            Rectangle(pos=self.pos, size=self.size)
            Color(*C('MAIN_DK'))
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
            gap = dp(2)
            bw = max(dp(2), (self.width - dp(8)) / self.n - gap)
            for i in range(self.n):
                v = self.vals[i]
                bh = v * (self.height - dp(8))
                bx = self.x + dp(4) + i * (bw + gap)
                # segmentos con gradiente
                seg = dp(5)
                yy = self.y + dp(4)
                top = yy + bh
                while yy < top:
                    nh = min(seg, top - yy)
                    Color(*self._bar_color((yy - self.y) / max(1, self.height)))
                    Rectangle(pos=(bx, yy), size=(bw, nh - dp(1)))
                    yy += seg
                Color(*C('ACCENT'))
                Rectangle(pos=(bx, top - dp(2)), size=(bw, dp(2)))


class SeekBar(Widget):
    """Barra de progreso tactil (tap para seek)."""
    def __init__(self, on_seek=None, **kw):
        super().__init__(**kw)
        self.frac = 0.0
        self.on_seek = on_seek
        self.bind(pos=self._redraw, size=self._redraw)

    def set_frac(self, f):
        self.frac = max(0.0, min(1.0, f))
        self._redraw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            f = (touch.x - self.x) / max(1, self.width)
            if self.on_seek:
                self.on_seek(max(0.0, min(1.0, f)))
            return True
        return super().on_touch_down(touch)

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(*C('SURFACE0'))
            Rectangle(pos=(self.x, self.center_y - dp(2)), size=(self.width, dp(4)))
            Color(*C('MAIN_GLW'))
            Rectangle(pos=(self.x, self.center_y - dp(2)),
                      size=(self.width * self.frac, dp(4)))
            Color(*C('ACCENT'))
            Ellipse(pos=(self.x + self.width * self.frac - dp(6), self.center_y - dp(6)),
                    size=(dp(12), dp(12)))


class TransportButton(Widget):
    """Boton con icono dibujado (prev/play/pause/next/gear/close)."""
    def __init__(self, kind='play', primary=False, on_press=None, **kw):
        super().__init__(**kw)
        self.kind = kind
        self.primary = primary
        self.cb = on_press
        self.bind(pos=self._redraw, size=self._redraw)

    def set_kind(self, k):
        self.kind = k
        self._redraw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.cb:
                self.cb()
            return True
        return super().on_touch_down(touch)

    def _redraw(self, *a):
        self.canvas.clear()
        cx, cy = self.center
        r = min(self.width, self.height) * 0.5 - dp(2)
        with self.canvas:
            if self.primary:
                Color(*C('MAIN'))
                Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
                ic = C('BG')
            else:
                Color(*C('SURFACE0'))
                Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
                ic = C('MAIN')
            Color(*ic)
            k = self.kind
            if k == 'play':
                w = r * 0.5; h = r * 0.7
                from kivy.graphics import Triangle
                Triangle(points=[cx - w / 2 + r * 0.08, cy - h / 2,
                                 cx - w / 2 + r * 0.08, cy + h / 2,
                                 cx + w / 2 + r * 0.08, cy])
            elif k == 'pause':
                bw = r * 0.2; bh = r * 0.7; gap = r * 0.16
                Rectangle(pos=(cx - gap - bw, cy - bh / 2), size=(bw, bh))
                Rectangle(pos=(cx + gap, cy - bh / 2), size=(bw, bh))
            elif k in ('prev', 'next'):
                from kivy.graphics import Triangle
                w = r * 0.45; h = r * 0.6; bw = r * 0.14
                if k == 'prev':
                    Rectangle(pos=(cx - r * 0.45, cy - h / 2), size=(bw, h))
                    Triangle(points=[cx + w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                                     cx - w / 2 + bw, cy])
                else:
                    Triangle(points=[cx - w / 2, cy - h / 2, cx - w / 2, cy + h / 2,
                                     cx + w / 2 - bw * 0.5, cy])
                    Rectangle(pos=(cx + r * 0.45 - bw, cy - h / 2), size=(bw, h))
            elif k == 'gear':
                n = 8
                pts = []
                for i in range(n * 2):
                    ang = i * math.pi / n
                    rr = r * 0.9 if i % 2 == 0 else r * 0.62
                    pts += [cx + rr * math.cos(ang), cy + rr * math.sin(ang)]
                from kivy.graphics import Mesh
                Line(points=pts + pts[:2], width=dp(2))
                Line(circle=(cx, cy, r * 0.28), width=dp(2))
            elif k == 'close':
                Line(points=[cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], width=dp(2.5))
                Line(points=[cx - r * 0.5, cy + r * 0.5, cx + r * 0.5, cy - r * 0.5], width=dp(2.5))


class LyricsView(ScrollView):
    """Letras con resaltado de linea activa y tap-para-saltar."""
    def __init__(self, on_seek_ms=None, **kw):
        super().__init__(**kw)
        self.on_seek_ms = on_seek_ms
        self.do_scroll_x = False
        self.grid = GridLayout(cols=1, size_hint_y=None, padding=dp(8), spacing=dp(4))
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.add_widget(self.grid)
        self.lines = []          # [{'time','text'}]
        self.labels = []
        self.synced = False
        self.active = -1

    def set_text(self, text, synced):
        self.grid.clear_widgets()
        self.labels = []
        self.synced = synced
        if synced:
            self.lines = text  # ya es lista
            items = [ln['text'] for ln in text]
        else:
            self.lines = []
            items = [l for l in (text or '').splitlines()]
        for i, s in enumerate(items):
            lb = Label(text=s, font_size=sp(15), color=C('SEC_DIM'),
                       size_hint_y=None, halign='center', valign='middle')
            lb.bind(size=lambda inst, val: setattr(inst, 'text_size', (inst.width, None)))
            lb.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1] + dp(8)))
            if synced:
                lb._t = self.lines[i]['time']
                lb.bind(on_touch_down=self._tap)
            self.grid.add_widget(lb)
            self.labels.append(lb)
        self.active = -1

    def _tap(self, inst, touch):
        if inst.collide_point(*touch.pos) and self.synced and self.on_seek_ms:
            self.on_seek_ms(max(0, inst._t - 150))
            return True
        return False

    def update_active(self, pos_ms, dur_ms):
        if not self.labels:
            return
        if self.synced and self.lines:
            act = 0
            for i, ln in enumerate(self.lines):
                if ln['time'] <= pos_ms:
                    act = i
                else:
                    break
        else:
            frac = pos_ms / max(1, dur_ms)
            act = min(len(self.labels) - 1, int(frac * len(self.labels)))
        if act == self.active:
            return
        self.active = act
        for i, lb in enumerate(self.labels):
            d = abs(i - act)
            if d == 0:
                lb.color = C('MAIN_GLW'); lb.bold = True; lb.font_size = sp(18)
            elif d == 1:
                lb.color = C('MAIN'); lb.bold = False; lb.font_size = sp(16)
            else:
                lb.color = C('SEC_DIM'); lb.bold = False; lb.font_size = sp(14)
        # autoscroll
        if len(self.labels) > 1:
            try:
                self.scroll_to(self.labels[act], padding=dp(40), animate=True)
            except Exception:
                pass


def themed_button(text, on_press, bg='SURFACE0', fg='MAIN', font=14, bold=True):
    b = Button(text=text, font_size=sp(font), bold=bold,
               background_normal='', background_down='',
               background_color=C(bg), color=C(fg))
    if on_press:
        b.bind(on_release=lambda *a: on_press())
    b._roles = (bg, fg)
    return b


# ==============================================================================
#   PANEL DE AJUSTES
# ==============================================================================
class SettingsPanel(FloatLayout):
    def __init__(self, root_app, **kw):
        super().__init__(**kw)
        self.app = root_app
        with self.canvas.before:
            Color(*C('MANTLE'))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        col = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        self.add_widget(col)

        head = BoxLayout(size_hint_y=None, height=dp(44))
        h = Label(text=_T('settings'), font_size=sp(18), bold=True,
                  color=C('MAIN_GLW'), halign='left', valign='middle')
        h.bind(size=lambda i, v: setattr(i, 'text_size', (i.width, None)))
        head.add_widget(h)
        close = themed_button('X', self.app.hide_settings, bg='SURFACE0', fg='MAIN', font=14)
        close.size_hint_x = None
        close.width = dp(54)
        head.add_widget(close)
        col.add_widget(head)

        col.add_widget(self._section(_T('lang')))
        lang_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        for code, lab in [('es', 'ESPANOL'), ('en', 'ENGLISH')]:
            lang_row.add_widget(themed_button(
                lab, lambda c=code: self.app.set_lang(c),
                bg=('MAIN_GLW' if CURRENT_LANG == code else 'SURFACE0'),
                fg=('BG' if CURRENT_LANG == code else 'MAIN'), font=12))
        col.add_widget(lang_row)

        col.add_widget(self._section(_T('theme')))
        grid = GridLayout(cols=5, size_hint_y=None, height=dp(96), spacing=dp(5))
        for name, th in THEMES.items():
            b = Button(text=th['name'], font_size=sp(9), bold=True,
                       background_normal='', background_down='',
                       background_color=get_color_from_hex(th['BG']),
                       color=get_color_from_hex(th['MAIN']))
            b.bind(on_release=lambda inst, n=name: self.app.set_theme(n))
            grid.add_widget(b)
        col.add_widget(grid)

        crt_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        cl = Label(text=_T('art_crt'), font_size=sp(12), color=C('SEC_DIM'),
                   halign='left', valign='middle')
        cl.bind(size=lambda i, v: setattr(i, 'text_size', (i.width, None)))
        crt_row.add_widget(cl)
        for val, lab in [(True, _T('on')), (False, _T('off'))]:
            crt_row.add_widget(themed_button(
                lab, lambda v=val: self.app.set_crt(v),
                bg=('MAIN_GLW' if self.app.crt == val else 'SURFACE0'),
                fg=('BG' if self.app.crt == val else 'MAIN'), font=12))
        col.add_widget(crt_row)

        col.add_widget(self._section('MUSICA'))
        col.add_widget(themed_button(_T('scan'), self.app.scan_storage,
                                     bg='SURFACE0', fg='MAIN_GLW', font=13))
        col.add_widget(themed_button(_T('pick'), self.app.open_picker,
                                     bg='SURFACE0', fg='MAIN_GLW', font=13))
        self.status_lbl = Label(text='', font_size=sp(11), color=C('ACCENT'),
                                size_hint_y=None, height=dp(24))
        col.add_widget(self.status_lbl)
        col.add_widget(Widget())

    def _section(self, txt):
        lb = Label(text=txt, font_size=sp(12), color=C('SEC_DIM'),
                   size_hint_y=None, height=dp(22), halign='left', valign='middle')
        lb.bind(size=lambda i, v: setattr(i, 'text_size', (i.width, None)))
        return lb

    def _sync_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


# ==============================================================================
#   PANTALLA PRINCIPAL
# ==============================================================================
class UtmostRoot(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.bg = RetroBackground()
        self.add_widget(self.bg)

        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))
        self.add_widget(root)

        top = BoxLayout(size_hint_y=None, height=dp(40))
        self.title_lbl = Label(text='UTMOST.FM', font_size=sp(20), bold=True,
                               color=C('MAIN_GLW'), halign='left', valign='middle')
        self.title_lbl.bind(size=lambda i, v: setattr(i, 'text_size', (i.width, None)))
        top.add_widget(self.title_lbl)
        self.clock_lbl = Label(text='--:--', font_size=sp(14), color=C('SEC'),
                               size_hint_x=None, width=dp(80))
        top.add_widget(self.clock_lbl)
        gear = TransportButton(kind='gear', on_press=app.show_settings,
                               size_hint=(None, None), size=(dp(36), dp(36)))
        top.add_widget(gear)
        root.add_widget(top)

        self.art = AlbumArt(size_hint_y=None, height=dp(210))
        root.add_widget(self.art)

        self.track_lbl = Label(text='-', font_size=sp(17), bold=True, color=C('MAIN_GLW'),
                               size_hint_y=None, height=dp(28), halign='center',
                               valign='middle', shorten=True)
        self.track_lbl.bind(size=lambda i, v: setattr(i, 'text_size', (i.width, None)))
        root.add_widget(self.track_lbl)
        self.artist_lbl = Label(text='-', font_size=sp(13), color=C('SEC'),
                                size_hint_y=None, height=dp(22), halign='center',
                                valign='middle', shorten=True)
        self.artist_lbl.bind(size=lambda i, v: setattr(i, 'text_size', (i.width, None)))
        root.add_widget(self.artist_lbl)

        self.spectrum = Spectrum(size_hint_y=None, height=dp(54))
        root.add_widget(self.spectrum)

        prow = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(6))
        self.t_now = Label(text='0:00', font_size=sp(11), color=C('SEC'),
                           size_hint_x=None, width=dp(44))
        self.t_tot = Label(text='0:00', font_size=sp(11), color=C('SEC'),
                           size_hint_x=None, width=dp(44))
        self.progress = SeekBar(on_seek=app.on_seek_frac)
        prow.add_widget(self.t_now)
        prow.add_widget(self.progress)
        prow.add_widget(self.t_tot)
        root.add_widget(prow)

        ctl = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(20),
                        padding=[dp(40), 0])
        self.prev_btn = TransportButton(kind='prev', on_press=app.prev)
        self.play_btn = TransportButton(kind='play', primary=True, on_press=app.toggle)
        self.next_btn = TransportButton(kind='next', on_press=app.next)
        for b in (self.prev_btn, self.play_btn, self.next_btn):
            ctl.add_widget(b)
        root.add_widget(ctl)

        vrow = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        vrow.add_widget(Label(text='VOL', font_size=sp(11), color=C('SEC'),
                             size_hint_x=None, width=dp(40)))
        self.vol = Slider(min=0, max=1, value=0.8, cursor_size=(dp(18), dp(18)))
        self.vol.bind(value=lambda i, v: app.set_volume(v))
        vrow.add_widget(self.vol)
        root.add_widget(vrow)

        self.lyr_title = Label(text=_T('lyrics'), font_size=sp(12), bold=True,
                               color=C('MAIN'), size_hint_y=None, height=dp(22),
                               halign='left', valign='middle')
        self.lyr_title.bind(size=lambda i, v: setattr(i, 'text_size', (i.width, None)))
        root.add_widget(self.lyr_title)
        self.lyrics = LyricsView(on_seek_ms=app.seek_ms)
        root.add_widget(self.lyrics)


# ==============================================================================
#   APP
# ==============================================================================
class UtmostApp(App):
    def build(self):
        cfg = load_cfg()
        global CURRENT_LANG
        CURRENT_LANG = cfg.get('lang', 'es')
        apply_theme(cfg.get('theme', 'purple'))
        self.theme_name = cfg.get('theme', 'purple')
        self.crt = bool(cfg.get('crt', False))

        self.audio = AudioEngine()
        self.audio.volume = cfg.get('volume', 0.8)
        self._cur_track_path = None
        self._lyrics_state = 'none'

        self.root_layout = FloatLayout()
        self.ui = UtmostRoot(self)
        self.root_layout.add_widget(self.ui)
        self.settings_panel = None
        self.ui.art.crt = self.crt

        # permisos + carga inicial
        if IS_ANDROID:
            request_android_perms()
        saved = cfg.get('tracks', [])
        if saved:
            self.audio.set_tracks(saved)
            self.ui.lyrics.set_text(_T('empty'), False)
        Clock.schedule_once(lambda dt: self._auto_initial_scan(), 0.5)

        # loops
        Clock.schedule_interval(self._tick, 1 / 30.0)
        Clock.schedule_interval(self._poll_track, 0.5)
        Clock.schedule_interval(self._tick_clock, 1.0)
        return self.root_layout

    def _auto_initial_scan(self):
        if not self.audio.tracks:
            self.scan_storage()

    # ----- loops -----
    def _tick(self, dt):
        self.ui.bg.tick(dt)
        self.ui.art.tick(dt)
        self.ui.spectrum.playing = self.audio.is_playing
        self.ui.spectrum.tick(dt)
        self.audio.poll_end()
        pos = self.audio.pos_ms()
        dur = self.audio.dur_ms()
        self.ui.progress.set_frac(pos / dur)
        self.ui.t_now.text = self._fmt(pos)
        self.ui.t_tot.text = self._fmt(dur)
        self.ui.lyrics.update_active(pos, dur)
        self.ui.play_btn.set_kind('pause' if self.audio.is_playing else 'play')

    def _tick_clock(self, dt):
        self.ui.clock_lbl.text = time.strftime('%H:%M:%S')

    def _poll_track(self, dt):
        tr = self.audio.current()
        path = tr['path'] if tr else None
        if path != self._cur_track_path:
            self._cur_track_path = path
            if tr:
                self.ui.track_lbl.text = tr.get('title', '-')
                self.ui.artist_lbl.text = tr.get('artist', '-')
                self.ui.art.set_art_bytes(tr.get('art'))
                threading.Thread(target=self._load_lyrics, args=(tr,), daemon=True).start()

    def _fmt(self, ms):
        s = int(ms // 1000)
        return f'{s // 60}:{s % 60:02d}'

    # ----- controles -----
    def toggle(self):
        self.audio.toggle()

    def next(self):
        self.audio.next()

    def prev(self):
        self.audio.prev()

    def set_volume(self, v):
        self.audio.set_volume(v)
        self._save()

    def seek_ms(self, ms):
        self.audio.seek_ms(ms)

    def on_seek_frac(self, f):
        self.audio.seek_ms(int(f * self.audio.dur_ms()))

    # ----- letras -----
    def _load_lyrics(self, tr):
        # 1) .lrc al lado
        try:
            base, _ = os.path.splitext(tr['path'])
            for ext in ('.lrc',):
                p = base + ext
                if os.path.isfile(p):
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = parse_lrc(f.read())
                    if lines:
                        Clock.schedule_once(lambda dt: self.ui.lyrics.set_text(lines, True))
                        return
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self.ui.lyrics.set_text(_T('searching'), False))
        res = fetch_lrclib(tr.get('artist'), tr.get('title'),
                           (tr.get('duration_ms') or 0) // 1000)
        if res and res.get('synced'):
            lines = parse_lrc(res['synced'])
            if lines:
                Clock.schedule_once(lambda dt: self.ui.lyrics.set_text(lines, True))
                return
        if res and res.get('plain'):
            txt = res['plain']
            Clock.schedule_once(lambda dt: self.ui.lyrics.set_text(txt, False))
            return
        Clock.schedule_once(lambda dt: self.ui.lyrics.set_text(_T('no_lyrics'), False))

    # ----- ajustes -----
    def show_settings(self):
        if self.settings_panel is None:
            self.settings_panel = SettingsPanel(self)
            self.root_layout.add_widget(self.settings_panel)

    def hide_settings(self):
        if self.settings_panel is not None:
            self.root_layout.remove_widget(self.settings_panel)
            self.settings_panel = None

    def set_lang(self, code):
        global CURRENT_LANG
        CURRENT_LANG = code
        self._save()
        self.hide_settings()
        self.ui.lyr_title.text = _T('lyrics')

    def set_theme(self, name):
        apply_theme(name)
        self.theme_name = name
        self._save()
        self.ui.title_lbl.color = C('MAIN_GLW')
        self.ui.track_lbl.color = C('MAIN_GLW')
        self.ui.artist_lbl.color = C('SEC')
        self.ui.clock_lbl.color = C('SEC')
        self.ui.lyr_title.color = C('MAIN')
        self.ui.t_now.color = C('SEC')
        self.ui.t_tot.color = C('SEC')
        for w in (self.ui.bg, self.ui.art, self.ui.spectrum, self.ui.progress,
                  self.ui.prev_btn, self.ui.play_btn, self.ui.next_btn):
            if hasattr(w, '_redraw'):
                w._redraw()
        self.hide_settings()

    def set_crt(self, val):
        self.crt = bool(val)
        self.ui.art.crt = self.crt
        self.ui.art._redraw()
        self._save()
        self.hide_settings()

    # ----- musica -----
    def scan_storage(self):
        if self.settings_panel:
            self.settings_panel.status_lbl.text = _T('scanning')

        def _bg():
            paths = scan_storage_dirs()
            tracks = [extract_meta(p) for p in paths]
            Clock.schedule_once(lambda dt: self._apply_tracks(tracks))
        threading.Thread(target=_bg, daemon=True).start()

    def _apply_tracks(self, tracks):
        self.audio.set_tracks(tracks)
        if self.settings_panel:
            self.settings_panel.status_lbl.text = _T('found') + str(len(tracks))
        self._save()

    def open_picker(self):
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        start = '/sdcard' if IS_ANDROID else os.path.expanduser('~')
        chooser = FileChooserListView(path=start if os.path.isdir(start) else '/',
                                      filters=['*' + e for e in AUDIO_EXTS],
                                      multiselect=True)
        box = BoxLayout(orientation='vertical')
        box.add_widget(chooser)
        btns = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        pop = Popup(title=_T('pick'), content=box, size_hint=(0.95, 0.9))

        def _ok(*a):
            sel = list(chooser.selection)
            if sel:
                tracks = [extract_meta(p) for p in sel if os.path.isfile(p)]
                self.audio.set_tracks(tracks)
                self._save()
            pop.dismiss()
            self.hide_settings()
        btns.add_widget(themed_button('OK', _ok, bg='MAIN_GLW', fg='BG'))
        btns.add_widget(themed_button(_T('close'), pop.dismiss, bg='SURFACE0', fg='MAIN'))
        box.add_widget(btns)
        pop.open()

    def _save(self):
        save_cfg({
            'lang': CURRENT_LANG, 'theme': self.theme_name, 'crt': self.crt,
            'volume': self.audio.volume,
            'tracks': self.audio.tracks[:500],
        })


if __name__ == '__main__':
    UtmostApp().run()
