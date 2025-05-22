import customtkinter as ctk
from PIL import Image
import json
from views.sidebar_view import SidebarView
from views.home_view import HomeView
from views.settings_view import SettingsView
from views.showcase_view import ShowcaseView
from views.api_test_view import APITestView
from views.manual_test import ManualTestView  # Import the ManualTestView
from widgets.custom_tabview import CustomTabView
from config.app_config import AppConfig

class AppController:
    def __init__(self, root):
        self.root = root
        self.config = AppConfig()
        
        # Initialize theme
        self.config.set_theme(self.config.DEFAULT_THEME)
        
        self._init_components()
    
    def _init_components(self):
        self.main_container = self._create_main_container()
        self.sidebar = self._create_sidebar()
        self.tabview = self._create_tabview()
        self.views = self._create_views()
    
    def _create_main_container(self):
        container = ctk.CTkFrame(self.root)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        return container
    
    def _create_sidebar(self):
        sidebar = SidebarView(self.main_container, width=250)
        sidebar.pack(fill="y", side="left", padx=10, pady=10)
        return sidebar
        
    def _create_tabview(self):
        tabview = CustomTabView(self.main_container)
        tabview.pack(fill="both", expand=True, padx=(0, 10), pady=10)
        
        # Add tabs with icons using paths from config
        tabs_with_icons = {
            "Home": self.config.get_icon_path("tab_home"),
            "ManualTest": self.config.get_icon_path("tab_manual"),
            "APITest": self.config.get_icon_path("tab_api"),
            "Settings": self.config.get_icon_path("tab_settings"),
            "Showcase": self.config.get_icon_path("tab_showcase"),
        }
        
        for tab, icon in tabs_with_icons.items():
            try:
                pil_image = Image.open(icon)
                icon_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(20, 20))
                tabview.add(tab, image=icon_image, compound="left")
            except Exception as e:
                print(f"Failed to load icon {icon}: {e}")
                tabview.add(tab)  # Fallback without icon
                
        return tabview

    def _create_views(self):
        views = {
            "Home": HomeView(self.tabview.tab("Home"), self),  # Pass self as app_controller
            "ManualTest": ManualTestView(self.tabview.tab("ManualTest")),  # Add ManualTest view
            "APITest": APITestView(self.tabview.tab("APITest")),
            "Settings": SettingsView(self.tabview.tab("Settings"), self),
            "Showcase": ShowcaseView(self.tabview.tab("Showcase"))
        }
        
        # Pack all views to make them visible
        for view in views.values():
            view.pack(fill="both", expand=True)
        
        return views

    def handle_theme_change(self, new_theme):
        """Handle theme change"""
        self.config.set_theme(new_theme)
        
        # Update theme menus
        if hasattr(self.sidebar, 'appearance_menu'):
            self.sidebar.appearance_menu.set(new_theme)
        if 'Settings' in self.views and hasattr(self.views['Settings'], 'theme_menu'):
            self.views['Settings'].theme_menu.set(new_theme)
        
        # Update tabview theme
        self.tabview.update_theme(new_theme)
        
        # Update UI
        self.root.update_idletasks()
        self.root.update()