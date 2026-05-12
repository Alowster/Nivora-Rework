# Dimensiones de la ventana
WINDOW_WIDTH = 300
WINDOW_HEIGHT = 75
WINDOW_TOP_MARGIN = 20

# Tamaños de botones
BUTTON_SIZE = 52
ICON_SIZE = 32
MENU_BUTTON_WIDTH = 45

# Espaciado y márgenes
LAYOUT_MARGIN_HORIZONTAL = 15
LAYOUT_MARGIN_VERTICAL = 12
BUTTON_SPACING = 12

# Colores del fondo
BACKGROUND_COLOR = (35, 35, 40, 230)  # RGBA
BORDER_COLOR = (255, 255, 255, 30)     # RGBA
INNER_BORDER_COLOR = (255, 255, 255, 15)  # RGBA

# Sombra
SHADOW_BLUR_RADIUS = 30
SHADOW_OFFSET_X = 0
SHADOW_OFFSET_Y = 8
SHADOW_COLOR = (0, 0, 0, 120)  # RGBA

# Gradientes del primer botón (pueden personalizarse)
GRADIENT_COLORS = {
    'start': '#4A90E2',
    'middle': '#7B68EE',
    'end': '#9B59B6'
}

GRADIENT_COLORS_HOVER = {
    'start': '#5AA0F2',
    'middle': '#8B78FE',
    'end': '#AB69C6'
}

GRADIENT_COLORS_PRESSED = {
    'start': '#3A80D2',
    'middle': '#6B58DE',
    'end': '#8B49A6'
}

# IA
GEMINI_MODEL = "models/gemini-3.1-flash-lite"

# Archivos de recursos
STYLES_FILE = "assets/styles.qss"
DB_PATH = "data/nivora.db"