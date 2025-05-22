from typing import Dict, List
import customtkinter as ctk
import os

class AppConfig:
    # App Information
    APP_NAME = "Test Case Management"
    VERSION = "1.0.0"
    WINDOW_SIZE = "1024x768"
    MIN_WINDOW_SIZE = (1200, 800)
    
    # Theme Settings
    DEFAULT_THEME = "Dark"
    DEFAULT_COLOR_THEME = "blue"
    THEMES = ["Light", "Dark", "System"]
    
    # Font Settings
    FONT_FAMILY = "Arial"
    FONT_SIZES = {
        "large": 16,
        "medium": 12,
        "small": 11
    }
    FONT_STYLES = {
        "header": ("Arial Bold", 20),
        "subheader": ("Arial Bold", 16),
        "normal": ("Arial", 12),  # Changed from "medium" to actual size
        "small": ("Arial", 11)    # Changed from "small" to actual size
    }
    
    # Color Settings
    COLORS = {
        "Light": {
            "bg_primary": "gray95",
            "bg_secondary": "gray90",
            "text": "black",
            "separator": "gray70"
        },
        "Dark": {
            "bg_primary": "gray20",
            "bg_secondary": "gray25",
            "text": "white",
            "separator": "gray30"
        }
    }
    
    # Status Colors
    STATUS_COLORS = {
        "Sent": ("lightblue", "darkblue"),
        "Scheduled": ("orange", "darkorange"),
        "Completed": ("lightgreen", "darkgreen"),
        "Rejected": ("pink", "darkred"),
        "In Progress": ("lightblue", "blue"),
        "No Response": ("gray80", "gray40"),
        "No Show": ("coral", "brown"),
        "Passed": ("lightgreen", "green"),
        "Failed": ("pink", "red"),
        "Pending": ("yellow", "orange"),
        "Accepted": ("lightgreen", "green"),
        "Withdrawn": ("gray70", "gray30")
    }
    
    # Application Stages
    STAGES = {
        "CV": {"Sent": "blue", "Rejected": "red", "No Response": "gray"},
        "HR Interview": {"Scheduled": "yellow", "Completed": "green", "Rejected": "red", 
                        "No Show": "brown", "Rescheduled": "orange"},
        "Technical Test": {"Scheduled": "yellow", "In Progress": "blue", "Completed": "green", 
                          "Failed": "red", "Passed": "cyan"},
        "Technical Interview": {"Scheduled": "yellow", "Completed": "green", "Rejected": "red", 
                              "No Show": "brown", "Rescheduled": "orange"},
        "User Interview": {"Scheduled": "yellow", "Completed": "green", "Rejected": "red", 
                          "No Show": "brown", "Rescheduled": "orange"},
        "Offer": {"Pending": "yellow", "Accepted": "green", "Rejected": "red"},
        "Contract Signed": {"Signed": "green", "Pending": "yellow", "Withdrawn": "brown"}
    }
    
    # UI Settings
    UI_SETTINGS = {
        "row_height": 30,
        "button_height": 28,
        "padding": {
            "small": 5,
            "medium": 10,
            "large": 20
        },
        "note_max_length": 50
    }
    
    # Field Options
    FIELD_OPTIONS = {
        "positions": ["Quality Engineer", "Software Engineer", "Data Scientist", 
                     "Product Manager", "Designer", "Other"],
        "locations": ["Indonesia", "Malaysia", "Singapore", "Australia", 
                     "Europe", "Asia", "Remote", "Other"],
        "salary_ranges": ["$50k-$70k", "$70k-$90k", "$90k-$110k", "$110k+", "Unknown"]
    }

    # API Test View Settings
    API_TEST_CONFIG = {
        "default_url": "http://aljazari:7200/balance-inquiry",
        "default_headers": {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "User-Agent": "APITestClient/1.0"
        },
        "default_body": {
            "transactionType": "InquirySaldo",
            "accountNumber": "1234567890",
            "requestDate": "2025-01-15T09:33:17Z",
            "channel": "ATM",
            "terminalId": "ATM12345"
        },
        "api_features": [
            "InquiryBalance", 
            "Transaction History", 
            "Account Details",
            "Fund Transfer (External/RTGS/NEFT/SKN)", 
            "Card Activation",
            "Card Block/Unblock", 
            "Card Transaction Inquiry", 
            "Payment",
            "Purchase", 
            "CheckStatus"
        ],
        "auth_types": ["None", "Basic Auth", "Bearer Token"],
        "http_methods": ["GET", "POST", "PUT", "DELETE"],
        "table_columns": [
            "Actions", "No.", "TestCaseID", "Feature", "Description",
            "TestSteps", "Expected", "Actual", "Status", "Environment",
            "Browser", "Evidence", "Date"
        ],
        "column_widths": {
            "Actions": 80,
            "No.": 50,
            "TestCaseID": 120,
            "Feature": 100,
            "Description": 150,
            "TestSteps": 200,
            "Expected": 150,
            "Actual": 150,
            "Status": 80,
            "Environment": 100,
            "Browser": 80,
            "Evidence": 80,
            "Date": 100
        }
    }

    # Manual Test View Settings
    MANUAL_TEST_CONFIG = {
        "test_case_prefix": "TC",
        "features": [
            "Login", "User Management", "Dashboard", "Reports",
            "Settings", "Profile", "Notifications", "Search", "FlowTransaction"
        ],
        "environments": ["Development", "Staging", "Production"],
        "browsers": ["Chrome", "Firefox", "Edge", "Safari"],
        "statuses": ["Pass", "Fail", "Not Executed"],
        "status_colors": {
            "Pass": "#2ECC71",
            "Fail": "#E74C3C",
            "Not Executed": "#95A5A6"
        },
        "supported_images": [
            ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("GIF files", "*.gif"),
            ("BMP files", "*.bmp"),
            ("All files", "*.*")
        ],
        "default_templates": {
            "desc": "Enter test description here...",
            "steps": """Given the user is on the login page
When the user enters valid credentials
And clicks the login button
Then the user should be redirected to the dashboard""",
            "expected": "User should be successfully logged in",
            "actual": "Enter actual test results here...",
            "notes": "Enter any notes or issues here..."
        },
        "table_columns": [
            "Actions", "No.", "TestCaseID", "Feature", "Description", 
            "TestSteps", "Expected", "Actual", "Status", "Environment",
            "Browser", "Evidence", "Date"
        ],
        "column_widths": {
            "Actions": 80,
            "No.": 50,
            "TestCaseID": 120,
            "Feature": 100,
            "Description": 150,
            "TestSteps": 200,
            "Expected": 150,
            "Actual": 150,
            "Status": 80,
            "Environment": 100,
            "Browser": 80,
            "Evidence": 80,
            "Date": 100
        }
    }

    # Common Database Settings
    DB_PATHS = {
        "job_applications": "db_jobapplications.db",
        "manual_test": "db_manualtestcases.db",
        "api_test": "db_apitestcase.db"
    }

    # Report Settings
    REPORT_CONFIG = {
        "output_dir": r"D:\ResultsTestCaseManagement",
        "chart_colors": {
            "pass": "#2ECC71",
            "fail": "#E74C3C",
            "not_executed": "#95A5A6",
            "feature_colors": [
                "#FF9999", "#66B2FF", "#99FF99", "#FFCC99",
                "#FF99CC", "#99FFCC", "#FFB366", "#99FF99"
            ]
        },
        "excel_formats": {
            "header": {
                "bold": True,
                "bg_color": "#4F81BD",
                "color": "white",
                "border": 1
            }
        }
    }

    def __init__(self):
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @classmethod
    def get_theme(cls) -> str:
        """Get current theme setting"""
        return ctk.get_appearance_mode()
    
    @classmethod
    def set_theme(cls, theme: str) -> None:
        """Set theme and apply settings"""
        if theme == "System":
            theme = ctk.get_appearance_mode()
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme(cls.DEFAULT_COLOR_THEME)
    
    # Icon paths for the entire application
    ICON_PATHS: Dict[str, str] = {
        # Tab icons
        "tab_home": "home.png",
        "tab_manual": "manual.png",
        "tab_api": "api.png",
        "tab_settings": "settings.png",
        "tab_showcase": "task.png",
        
        # Other icons
        "settings": "settings.png",
        "add": "add.png",
        # Add other icon paths here
    }
    
    def get_icon_path(self, icon_name: str) -> str:
        """Get the path for a specific icon https://heroicons.dev/  https://fonts.google.com/icons"""
        return os.path.join(self.base_path, "assets", "icons", self.ICON_PATHS[icon_name])

    FONTS: List[str] = ["Times New Roman", "Arial", "Helvetica"]