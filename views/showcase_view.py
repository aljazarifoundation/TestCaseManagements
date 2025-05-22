from customtkinter import CTkFrame, CTkLabel, ThemeManager
from widgets.custom_button import CustomButton
from widgets.custom_tabview import CustomTabView

class ShowcaseView(CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.configure(fg_color=ThemeManager.theme["CTk"]["fg_color"])
        
        self.label = CTkLabel(self, text="Showcase View")
        self.label.pack(pady=20)
        
        self.button = CustomButton(self, text="Custom Button")
        self.button.pack(pady=10)
        
        self.tabview = CustomTabView(self)
        self.tabview.pack(pady=10)
        self.tabview.add("Tab 1")
        self.tabview.add("Tab 2")
        self.tabview.add("Tab 3")
        
        self.showcase_label = CTkLabel(self, text="Showcase Content", font=("Helvetica", 16))
        self.showcase_label.pack(pady=20)
        
        self.description_label = CTkLabel(self, text="This is a showcase of the application's features.", wraplength=400)
        self.description_label.pack(pady=10)
        
        self.feature_label = CTkLabel(self, text="Feature 1: Custom Button", font=("Helvetica", 14))
        self.feature_label.pack(pady=5)
        
        self.feature_description = CTkLabel(self, text="This button demonstrates the custom button widget.", wraplength=400)
        self.feature_description.pack(pady=5)
        
        self.feature_label2 = CTkLabel(self, text="Feature 2: Custom Dropdown", font=("Helvetica", 14))
        self.feature_label2.pack(pady=5)
        
        self.feature_description2 = CTkLabel(self, text="This dropdown demonstrates the custom dropdown widget.", wraplength=400)
        self.feature_description2.pack(pady=5)