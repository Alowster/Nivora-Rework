import ctypes
import ctypes.wintypes


class _ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ('AccentState',   ctypes.c_uint),
        ('AccentFlags',   ctypes.c_uint),
        ('GradientColor', ctypes.c_uint),
        ('AnimationId',   ctypes.c_uint),
    ]


class _WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ('Attribute',  ctypes.c_uint),
        ('Data',       ctypes.c_void_p),
        ('SizeOfData', ctypes.c_size_t),
    ]


ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


def apply_acrylic(hwnd: int, tint_color: int = 0x00FFFFFF):
    """Aplica efecto Acrylic (blur de escritorio) a la ventana con el HWND dado.
    tint_color: AABBGGRR — 0x00FFFFFF sin tinte, 0x44000000 negro suave.
    """
    accent = _ACCENTPOLICY()
    accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags = 2
    accent.GradientColor = tint_color

    data = _WINCOMPATTRDATA()
    data.Attribute = WCA_ACCENT_POLICY
    data.Data = ctypes.cast(ctypes.byref(accent), ctypes.c_void_p)
    data.SizeOfData = ctypes.sizeof(accent)

    ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
