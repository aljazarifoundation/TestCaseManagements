import customtkinter as ctk
from controllers.app_controller import AppController
from config.app_config import AppConfig

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self._setup_window()
        self.app_controller = AppController(self)
        
    def _setup_window(self):
        self.title(self.config.APP_NAME)
        self.geometry(self.config.WINDOW_SIZE)
        self.minsize(*self.config.MIN_WINDOW_SIZE)

def main():
    #print("Hello from the executable!")
    #input("Press Enter to exit...")
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()