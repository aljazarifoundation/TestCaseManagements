import customtkinter as ctk
from typing import Optional, Any
from config.app_config import AppConfig

class CustomTabView(ctk.CTkTabview):
    def __init__(self, master: Optional[Any] = None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.config = AppConfig()
        
        # Apply initial theme colors
        self._apply_theme_colors(self.config.get_theme())

    def _apply_theme_colors(self, theme: str) -> None:
        if theme == "System":
            theme = ctk.get_appearance_mode()
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme(self.config.DEFAULT_COLOR_THEME)

    def add(self, name: str, **kwargs) -> None:
        """Override add method to support additional parameters like image"""
        tab = super().add(name)
        
        # If image is provided, update the tab button with the image
        if "image" in kwargs and "compound" in kwargs:
            for button in self._segmented_button._buttons_dict.values():
                if button.cget("text") == name:
                    button.configure(image=kwargs["image"], compound=kwargs["compound"])
                    break
        
        return tab

    def update_theme(self, theme: str) -> None:
        self._apply_theme_colors(theme)

    def refresh_theme(self) -> None:
        """Refresh the theme colors based on the current configuration."""
        self._apply_theme_colors(self.config.get_theme())