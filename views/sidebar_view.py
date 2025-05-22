import customtkinter as ctk
from PIL import Image
import webbrowser
import json
import os
from config.app_config import AppConfig

class SidebarView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.config = AppConfig()
        
        # Apply initial frame colors
        self.config.set_theme(self.config.get_theme())
        
        # Create main sections
        self.top_frame = ctk.CTkFrame(self)
        self.info_frame = ctk.CTkFrame(self)
        self.bottom_frame = ctk.CTkFrame(self)
        
        # Pack main sections
        self.top_frame.pack(fill="x", expand=False, padx=5, pady=5)
        self.info_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.bottom_frame.pack(fill="x", side="bottom", padx=5, pady=5)
        
        self._setup_header()
        self._setup_info()
        self._setup_controls()
    
    def _setup_header(self):
        # Logo
        try:
            logo = ctk.CTkImage(Image.open("assets/icons/apps.png"), size=(64, 64))
            ctk.CTkLabel(self.top_frame, text="", image=logo).pack(padx=5, pady=5)
        except: pass
        
        # Title and version
        ctk.CTkLabel(self.top_frame, 
                     text=self.config.APP_NAME, 
                     font=("", 16, "bold")).pack(padx=5, pady=5)
        
        ctk.CTkLabel(self.top_frame, 
                     text=f"Version {self.config.VERSION}", 
                     font=("bold", 12)).pack(pady=5)
    

    def _setup_info(self):
        self.info_text = ctk.CTkTextbox(
            self.info_frame,
            wrap="word",
            font=("", 12)
        )
        self.info_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        info_content = """Test Management System

        A Complete Testing & Job Application Tracking Solution

        • Job Application Tracking
        - Application status monitoring
        - Interview stage tracking
        - Document management
        - Application analytics
        - Career progress tracking

        • Manual Testing
        - Test case management
        - Test execution tracking
        - Defect reporting
        - Requirements coverage
        - Test documentation

        • API Testing
        - REST/SOAP API validation
        - Request/Response testing
        - Endpoint management
        - Security testing
        - Performance testing

        • Automation Testing (Coming Soon)
        - Selenium WebDriver integration
        - Test script management
        - CI/CD pipeline integration
        - Cross-browser testing
        - Automated reporting

        Designed for QA professionals and job seekers to streamline testing processes and career development."""

        self.info_text.insert("1.0", info_content)
        self.info_text.configure(state="disabled")
    
    def _setup_controls(self):
        # GitHub button
        ctk.CTkButton(
            self.bottom_frame,
            text="GitHub Repository",
            command=lambda: webbrowser.open("https://github.com/yourusername/testcasemanagement")).pack(fill="x", padx=40, pady=(10,10))
        
        # Theme selector with proper styling
        theme_label = ctk.CTkLabel(
            self.bottom_frame, 
            text="Theme Mode:",
            font=("", 12)
        )
        theme_label.pack(padx=5, pady=5)
        
        self.appearance_menu = ctk.CTkOptionMenu(
            self.bottom_frame,
            values=self.config.THEMES,
            command=self._handle_theme_change
        )
        self.appearance_menu.set(self.config.get_theme())
        self.appearance_menu.pack(padx=1, pady=10)

    def _handle_theme_change(self, new_theme):
        # Apply theme using AppConfig
        self.config.set_theme(new_theme)
        
        # Notify controller
        if hasattr(self.master, 'app_controller'):
            self.master.app_controller.handle_theme_change(new_theme)
