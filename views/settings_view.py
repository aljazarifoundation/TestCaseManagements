import customtkinter as ctk
from config.app_config import AppConfig

class SettingsView(ctk.CTkFrame):
    def __init__(self, master, app_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.config = AppConfig()
        self._init_ui()
    
    def _init_ui(self):
        # Title
        ctk.CTkLabel(self, text="Appearance Settings",
                    font=("", 16, "bold")).pack(pady=(20,10), padx=20, anchor="w")
        
        # Theme selector frame
        theme_frame = ctk.CTkFrame(self)
        theme_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(theme_frame, text="Theme Mode:",
                    font=("", 12)).pack(side="left", padx=(20,10), pady=10)
        
        # Use themes from config
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Light", "Dark", "System"],  # Basic themes only
            command=self._handle_theme_change,
            width=150
        )
        self.theme_menu.set(ctk.get_appearance_mode())
        self.theme_menu.pack(side="left", padx=10, pady=10)
    
    def _handle_theme_change(self, new_theme):
        if self.app_controller:
            self.app_controller.handle_theme_change(new_theme)