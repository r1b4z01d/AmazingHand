"""Platform helpers for window customization and keyboard state."""

from __future__ import annotations

import ctypes
import platform
from typing import Optional


def set_windows_window_frame_color(window_name, rgb_color):
    """Attempt to tint the native Windows title bar / border."""
    if platform.system() != "Windows":
        return False
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, window_name)
        if hwnd == 0:
            return False
        dwmapi = ctypes.windll.dwmapi
        # COLORREF uses 0x00BBGGRR ordering.
        r, g, b = rgb_color
        colorref = ctypes.c_int((b << 16) | (g << 8) | r)
        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        for attr in (DWMWA_BORDER_COLOR, DWMWA_CAPTION_COLOR):
            dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(colorref), ctypes.sizeof(colorref)
            )
        return True
    except (AttributeError, OSError):
        return False


_SYSTEM = platform.system()

# Windows global key state primitives
try:
    _USER32 = ctypes.windll.user32 if _SYSTEM == "Windows" else None
except (AttributeError, OSError):  # pragma: no cover - windll missing on non-Windows
    _USER32 = None

# Linux/X11 global key state primitives
_X11 = None
_X11_DISPLAY = None
_X11_KEYCODE_CACHE: dict[str, Optional[int]] = {}
if _SYSTEM == "Linux":
    try:  # pragma: no cover - requires X11 runtime
        _X11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        _X11.XInitThreads()
        _X11.XOpenDisplay.restype = ctypes.c_void_p
        _X11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        _X11_DISPLAY = _X11.XOpenDisplay(None)
        if _X11_DISPLAY:
            _X11.XStringToKeysym.restype = ctypes.c_ulong
            _X11.XStringToKeysym.argtypes = [ctypes.c_char_p]
            _X11.XKeysymToKeycode.restype = ctypes.c_int
            _X11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            _X11.XQueryKeymap.restype = ctypes.c_int
            _X11.XQueryKeymap.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_char),
            ]
    except (AttributeError, OSError):
        _X11 = None
        _X11_DISPLAY = None


def _normalize_key_char(key: str) -> str:
    if not isinstance(key, str) or len(key) != 1:
        raise ValueError("key must be a single character string")
    return key


def _linux_keycode_for_char(key: str) -> Optional[int]:
    """Lookup and cache the X11 keycode for a printable key."""
    if _X11 is None or not _X11_DISPLAY:
        return None
    cached = _X11_KEYCODE_CACHE.get(key)
    if cached is not None:
        return cached
    for candidate in (key, key.upper(), key.lower()):
        c_bytes = candidate.encode("ascii", errors="ignore")
        if not c_bytes:
            continue
        keysym = _X11.XStringToKeysym(c_bytes)
        if keysym != 0:
            keycode = _X11.XKeysymToKeycode(_X11_DISPLAY, keysym)
            if keycode != 0:
                _X11_KEYCODE_CACHE[key] = keycode
                return keycode
    _X11_KEYCODE_CACHE[key] = None
    return None


def supports_global_hotkeys() -> bool:
    """Return True when we can query global keyboard state."""
    if _USER32 is not None:
        return True
    return bool(_X11 and _X11_DISPLAY)


def is_global_key_pressed(key: str) -> bool:
    """Check if the given printable key is currently pressed globally."""
    key = _normalize_key_char(key)
    if _USER32 is not None:
        virtual_key = ord(key.upper())
        return bool(_USER32.GetAsyncKeyState(virtual_key) & 0x8000)

    if _X11 is not None and _X11_DISPLAY:
        keycode = _linux_keycode_for_char(key)
        if keycode is None:
            return False
        keymap = (ctypes.c_ubyte * 32)()
        _X11.XQueryKeymap(_X11_DISPLAY, ctypes.cast(keymap, ctypes.POINTER(ctypes.c_char)))
        byte_index = keycode // 8
        bit_index = keycode % 8
        key_byte = keymap[byte_index]
        return bool(key_byte & (1 << bit_index))

    return False


__all__ = ["set_windows_window_frame_color", "supports_global_hotkeys", "is_global_key_pressed"]
