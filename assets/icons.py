"""
icons.py - Iconos SVG para la aplicación Island
"""

def get_chat_icon():
    """Icono de chat con burbujas de mensaje"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 4C9.4 4 4 8.6 4 14.5C4 17.4 5.4 20 7.6 21.9L6.5 26.5C6.4 26.9 6.8 27.3 7.2 27.2L12.4 25.5C13.5 25.8 14.7 26 16 26C22.6 26 28 21.4 28 15.5C28 9.6 22.6 4 16 4Z" 
              fill="white" opacity="0.9"/>
        <circle cx="11" cy="15" r="1.5" fill="#1a1a1a"/>
        <circle cx="16" cy="15" r="1.5" fill="#1a1a1a"/>
        <circle cx="21" cy="15" r="1.5" fill="#1a1a1a"/>
    </svg>
    """

def get_clock_icon():
    """Icono de reloj"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="16" r="11" fill="none" stroke="white" stroke-width="2" opacity="0.8"/>
        <path d="M16 8 L16 16 L21 19" fill="none" stroke="white" stroke-width="2" 
              stroke-linecap="round" stroke-linejoin="round" opacity="0.8"/>
    </svg>
    """

def get_sparkles_icon():
    """Icono de sparkles/estrellas (IA)"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 4 L17.5 11 L24 12.5 L17.5 14 L16 21 L14.5 14 L8 12.5 L14.5 11 Z" 
              fill="white" opacity="0.9"/>
        <path d="M24 6 L24.8 9 L28 9.8 L24.8 10.6 L24 14 L23.2 10.6 L20 9.8 L23.2 9 Z" 
              fill="white" opacity="0.7"/>
        <path d="M9 20 L9.5 22 L12 22.5 L9.5 23 L9 25 L8.5 23 L6 22.5 L8.5 22 Z" 
              fill="white" opacity="0.7"/>
    </svg>
    """

def get_settings_icon():
    """Icono de configuración (opcional)"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 11 C13.2 11 11 13.2 11 16 C11 18.8 13.2 21 16 21 C18.8 21 21 18.8 21 16 C21 13.2 18.8 11 16 11 Z" 
              fill="white" opacity="0.8"/>
        <path d="M26 14 L24 14 C23.7 12.9 23.2 11.9 22.5 11 L23.8 9.7 L22.3 8.2 L21 9.5 C20.1 8.8 19.1 8.3 18 8 L18 6 L14 6 L14 8 C12.9 8.3 11.9 8.8 11 9.5 L9.7 8.2 L8.2 9.7 L9.5 11 C8.8 11.9 8.3 12.9 8 14 L6 14 L6 18 L8 18 C8.3 19.1 8.8 20.1 9.5 21 L8.2 22.3 L9.7 23.8 L11 22.5 C11.9 23.2 12.9 23.7 14 24 L14 26 L18 26 L18 24 C19.1 23.7 20.1 23.2 21 22.5 L22.3 23.8 L23.8 22.3 L22.5 21 C23.2 20.1 23.7 19.1 24 18 L26 18 Z" 
              fill="none" stroke="white" stroke-width="1.5" opacity="0.8"/>
    </svg>
    """

def get_heart_icon():
    """Icono de corazón (opcional)"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 27 C16 27 4 19 4 11 C4 7.7 6.7 5 10 5 C12.4 5 14.5 6.3 16 8.3 C17.5 6.3 19.6 5 22 5 C25.3 5 28 7.7 28 11 C28 19 16 27 16 27 Z" 
              fill="white" opacity="0.85"/>
    </svg>
    """

def get_notification_icon():
    """Icono de notificación (opcional)"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 6 C13.2 6 11 8.2 11 11 L11 16 L8 20 L24 20 L21 16 L21 11 C21 8.2 18.8 6 16 6 Z" 
              fill="white" opacity="0.85"/>
        <path d="M14 22 C14 23.1 14.9 24 16 24 C17.1 24 18 23.1 18 22" 
              fill="none" stroke="white" stroke-width="2" stroke-linecap="round" opacity="0.85"/>
        <circle cx="22" cy="9" r="3" fill="#FF5555"/>
    </svg>
    """

def get_close_icon():
    """Icono de cerrar/X"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path d="M9 9 L23 23 M23 9 L9 23" 
              stroke="white" stroke-width="2.5" 
              stroke-linecap="round" opacity="0.8"/>
    </svg>
    """

def get_send_icon():
    """Icono de enviar (estilo flecha de papel/telegram)"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path d="M26.5 5.5L4 14.5L13.5 18.5L17.5 28L26.5 5.5Z" 
              fill="none" stroke="white" stroke-width="2" stroke-linejoin="round"/>
        <path d="M13.5 18.5L26.5 5.5" 
              stroke="white" stroke-width="2" stroke-linecap="round"/>
    </svg>
    """

def get_stop_icon():
    """Icono de detener generación (cuadrado)"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <rect x="9" y="9" width="14" height="14" rx="2"
              fill="white" opacity="0.9"/>
    </svg>
    """

def get_camera_icon():
    """Icono de cámara (estilo Instagram/Cámara moderna)"""
    return """
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <rect x="6" y="9" width="20" height="15" rx="3" 
              stroke="white" stroke-width="2" fill="none"/>
        <circle cx="16" cy="16.5" r="3.5" 
                stroke="white" stroke-width="2" fill="none"/>
        <path d="M11 9L13 6H19L21 9" 
              stroke="white" stroke-width="2" stroke-linejoin="round" fill="none"/>
        <circle cx="22" cy="12" r="1" fill="white"/>
    </svg>
    """