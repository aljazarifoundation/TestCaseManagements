from customtkinter import CTkButton, ThemeManager
from typing import Optional, Any
from config.app_config import AppConfig

class CustomButton(CTkButton):
    """A custom button widget that uses theme-aware colors with fallback values."""
    
    def __init__(self, master: Optional[Any] = None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._apply_theme_colors()
    
    def _apply_theme_colors(self) -> None:
        try:
            current_theme = ThemeManager.current_theme
            theme = AppConfig.THEME_SETTINGS.get(current_theme, {})
            button_theme = theme.get("CTkButton", {})
            self.configure(
                fg_color=button_theme.get("fg_color", "gray75"),
                hover_color=button_theme.get("hover_color", "gray70"),
                text_color=button_theme.get("text_color", "black")
            )
        except Exception as e:
            print(f"Warning: Failed to apply theme colors: {e}")
            self.configure(fg_color="gray75", hover_color="gray70", text_color="black")