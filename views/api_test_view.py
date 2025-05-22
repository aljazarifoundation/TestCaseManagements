import customtkinter as ctk
import requests
import json
from datetime import datetime
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sqlite3
from config.app_config import AppConfig

class APITestView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.config = AppConfig()
        self.request_logs = []
        self.stats = {
            "success": 0, 
            "failed": 0,
            "features": {
                "InquirySaldo": {"total": 0, "passed": 0},
                "Transfer": {"total": 0, "passed": 0},
                "Payment": {"total": 0, "passed": 0}
            }
        }
        self.test_cases = []
        self.setup_ui()
        self.load_default_values()
        self.setup_request_config()
        self.setup_database()

    def setup_database(self):
        self.conn = sqlite3.connect('db_apitestcase.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY,
                name TEXT,
                method TEXT,
                url TEXT,
                headers TEXT,
                body TEXT,
                auth_type TEXT,
                auth_value TEXT,
                config TEXT,
                status TEXT,
                response_time TEXT,
                response_headers TEXT,
                response_body TEXT,
                api_name TEXT
            )
        ''')
        self.conn.commit()
        self.load_test_cases()

    def load_test_cases(self):
        self.cursor.execute('SELECT * FROM test_cases')
        rows = self.cursor.fetchall()
        for row in rows:
            test_case = {
                "id": row[0],
                "name": row[1],
                "method": row[2],
                "url": row[3],
                "headers": row[4],
                "body": row[5],
                "auth_type": row[6],
                "auth_value": row[7],
                "config": json.loads(row[8]),
                "status": row[9],
                "response_time": row[10],
                "response_headers": row[11],
                "response_body": row[12],
                "api_name": row[13]
            }
            self.test_cases.append(test_case)
            self.add_to_manage_list(test_case)

    def save_test_case_to_db(self, test_case):
        self.cursor.execute('''
            INSERT INTO test_cases (name, method, url, headers, body, auth_type, auth_value, config, status, response_time, response_headers, response_body, api_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_case["name"],
            test_case["method"],
            test_case["url"],
            test_case["headers"],
            test_case["body"],
            test_case["auth_type"],
            test_case["auth_value"],
            json.dumps(test_case["config"]),
            test_case["status"],
            test_case["response_time"],
            test_case["response_headers"],
            test_case["response_body"],
            test_case["api_name"]
        ))
        self.conn.commit()

    def load_default_values(self):
        # Set default URL
        self.url_entry.insert(0, "http://aljazari:7200/balance-inquiry")
        
        # Set default request body
        default_body = {
            "transactionType": "InquirySaldo",
            "accountNumber": "1234567890",
            "requestDate": "2025-01-15T09:33:17Z",
            "channel": "ATM",
            "terminalId": "ATM12345"
        }
        self.body_text.insert("1.0", json.dumps(default_body, indent=2))

    def setup_ui(self):
        # Main parameters frame with themed colors
        self.params_frame = ctk.CTkFrame(
            self,
            fg_color=self.config.COLORS[self.config.get_theme()]["bg_secondary"]
        )
        self.params_frame.pack(fill="x", pady=5)

        # API name frame
        self.api_name_frame = ctk.CTkFrame(self.params_frame)
        self.api_name_frame.pack(fill="x", pady=2)
        
        self.api_name_var = ctk.StringVar(value="InquirySaldo")
        self.api_name_menu = ctk.CTkOptionMenu(
            self.api_name_frame,
            values=["InquiryBalance", "Transaction History", "Account Details", 
                   "Fund Transfer (External/RTGS/NEFT/SKN)", "Card Activation", 
                   "Card Block/Unblock", "Card Transaction Inquiry", "Payment", 
                   "Purchase", "CheckStatus"],
            variable=self.api_name_var,
            width=120,
            font=self.config.FONT_STYLES["normal"]
        )
        self.api_name_menu.pack(side="left", padx=5, pady=2)

        # Set up other UI elements
        self._setup_auth_frame()
        self._setup_url_frame()
        self._setup_tab_view()

    def _setup_auth_frame(self):
        # Authorization frame
        self.auth_frame = ctk.CTkFrame(
            self.params_frame,
            fg_color=self.config.COLORS[self.config.get_theme()]["bg_secondary"]
        )
        self.auth_frame.pack(fill="x", pady=2)
        
        self.auth_type = ctk.CTkOptionMenu(
            self.auth_frame,
            values=["None", "Basic Auth", "Bearer Token"],
            command=self.on_auth_change,
            width=120,
            font=self.config.FONT_STYLES["normal"]
        )
        self.auth_type.pack(side="left", padx=5)
        
        self.auth_input = ctk.CTkEntry(
            self.auth_frame,
            placeholder_text="Auth Value",
            width=200,
            font=self.config.FONT_STYLES["normal"]
        )
        self.auth_input.pack(side="left", padx=5, fill="x", expand=True)

    def _setup_url_frame(self):
        # URL and Method frame
        self.url_frame = ctk.CTkFrame(
            self.params_frame,
            fg_color=self.config.COLORS[self.config.get_theme()]["bg_secondary"]
        )
        self.url_frame.pack(fill="x", pady=4)
        
        self.method_menu = ctk.CTkOptionMenu(
            self.url_frame,
            values=["GET", "POST", "PUT", "DELETE"],
            command=self.on_method_change,
            width=120,
            font=self.config.FONT_STYLES["normal"]
        )
        self.method_menu.pack(side="left", padx=5)

        self.url_entry = ctk.CTkEntry(
            self.url_frame,
            placeholder_text="Enter URL",
            width=400,
            font=self.config.FONT_STYLES["normal"]
        )
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)

        self.status_frame = ctk.CTkFrame(
            self.url_frame, 
            fg_color="transparent"
        )
        self.status_frame.pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Status: -",
            font=self.config.FONT_STYLES["normal"]
        )
        self.status_label.pack(side="left", padx=5)
        
        self.response_time_label = ctk.CTkLabel(
            self.status_frame,
            text="Response Time: -",
            font=self.config.FONT_STYLES["normal"]
        )
        self.response_time_label.pack(side="left", padx=5)

        self.send_button = ctk.CTkButton(
            self.url_frame,
            text="Send",
            command=self.send_request,
            width=100,
            font=self.config.FONT_STYLES["normal"]
        )
        self.send_button.pack(side="right", padx=5)

    def _setup_tab_view(self):
        # Main tab view
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, pady=5)

        # Create tabs
        tabs = ["Request", "Response", "Test Results Management", "Statistics", "Logs"]
        for tab in tabs:
            self.tab_view.add(tab)

        # Setup individual tabs
        self.setup_request_tab(self.tab_view.tab("Request"))
        self.setup_response_tab(self.tab_view.tab("Response"))
        self.setup_data_tab(self.tab_view.tab("Test Results Management"))
        self.setup_statistics_tab(self.tab_view.tab("Statistics"))
        self.setup_log_tab(self.tab_view.tab("Logs"))

    def setup_request_tab(self, tab):
        # Headers with themed appearance
        self.headers_label = ctk.CTkLabel(
            tab, 
            text="Headers:",
            font=self.config.FONT_STYLES["normal"]
        )
        self.headers_label.pack(anchor="w", padx=5, pady=(5,0))
        
        self.headers_text = ctk.CTkTextbox(
            tab, 
            height=100,
            font=self.config.FONT_STYLES["normal"]
        )
        self.headers_text.pack(fill="x", padx=5, pady=5)
        self.headers_text.insert("1.0", '{\n    "Content-Type": "application/json",\n    "Connection": "keep-alive",\n    "User-Agent": "APITestClient/1.0"\n}')

        # Body
        self.body_label = ctk.CTkLabel(
            tab, 
            text="Body:",
            font=self.config.FONT_STYLES["normal"]
        )
        self.body_label.pack(anchor="w", padx=5, pady=(5,0))
        
        self.body_text = ctk.CTkTextbox(
            tab, 
            height=200,
            font=self.config.FONT_STYLES["normal"]
        )
        self.body_text.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_response_tab(self, tab):
        # Headers with themed appearance
        self.resp_headers_label = ctk.CTkLabel(
            tab,  # Changed from self.resp_tab to tab
            text="Headers:",
            font=self.config.FONT_STYLES["normal"]
        )
        self.resp_headers_label.pack(anchor="w", padx=5, pady=(5,0))
        
        self.resp_headers_text = ctk.CTkTextbox(
            tab,  # Changed from self.resp_tab to tab
            height=150,
            font=self.config.FONT_STYLES["normal"]
        )
        self.resp_headers_text.pack(fill="x", padx=5, pady=5)

        # Body
        self.resp_body_label = ctk.CTkLabel(
            tab,  # Changed from self.resp_tab to tab
            text="Body:",
            font=self.config.FONT_STYLES["normal"]
        )
        self.resp_body_label.pack(anchor="w", padx=5, pady=(5,0))
        
        self.resp_body_text = ctk.CTkTextbox(
            tab,  # Changed from self.resp_tab to tab
            font=self.config.FONT_STYLES["normal"]
        )
        self.resp_body_text.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_data_tab(self, tab):
        """Enhanced test results management"""
        self.data_notebook = ctk.CTkTabview(tab)
        self.data_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Test Results tab
        self.test_results_tab = self.data_notebook.add("Test Results")
        self.setup_test_results_tab()
        
        # Manage Results tab
        self.manage_results_tab = self.data_notebook.add("Manage Results")
        self.setup_manage_results_tab()

    def setup_test_results_tab(self):
        # Title
        title_frame = ctk.CTkFrame(self.test_results_tab)
        title_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            title_frame,
            text="Test Results",
            font=("Arial Bold", 14)
        ).pack(pady=5)

        # Control buttons
        self.data_controls = ctk.CTkFrame(self.test_results_tab)
        self.data_controls.pack(fill="x", padx=5, pady=5)
        
        self.add_btn = ctk.CTkButton(
            self.data_controls, 
            text="Add Test Result",
            command=self.add_test_case
        )
        self.add_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(
            self.data_controls,
            text="Clear All",
            command=self.clear_test_results
        )
        self.clear_btn.pack(side="left", padx=5)

        # Test results list
        test_results_frame = ctk.CTkFrame(self.test_results_tab)
        test_results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Headers for test results
        test_results_headers_frame = ctk.CTkFrame(test_results_frame)
        test_results_headers_frame.pack(fill="x", padx=5, pady=2)
        
        test_results_headers = ["Name", "API Name", "Method", "URL", "Headers", "Body", "Status", "Response Time"]
        test_results_weights = [2, 2, 1, 2, 2, 2, 1, 1]
        
        for header, weight in zip(test_results_headers, test_results_weights):
            ctk.CTkLabel(
                test_results_headers_frame,
                text=header,
                font=("Arial Bold", 12)
            ).pack(side="left", padx=5, expand=True, fill="x")

        # Scrollable list for test results
        self.test_results_list = ctk.CTkScrollableFrame(test_results_frame)
        self.test_results_list.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_manage_results_tab(self):
        # Title
        title_frame = ctk.CTkFrame(self.manage_results_tab)
        title_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            title_frame,
            text="Manage Results",
            font=("Arial Bold", 14)
        ).pack(pady=5)

        # Manage results list
        manage_results_frame = ctk.CTkFrame(self.manage_results_tab)
        manage_results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Headers for manage results
        manage_results_headers_frame = ctk.CTkFrame(manage_results_frame)
        manage_results_headers_frame.pack(fill="x", padx=5, pady=2)
        
        manage_results_headers = ["ID", "Name", "API Name", "Method", "URL", "Headers", "Body", "Status", "Response Time"]
        manage_results_weights = [1, 2, 2, 1, 2, 2, 2, 1, 1]
        
        for header, weight in zip(manage_results_headers, manage_results_weights):
            ctk.CTkLabel(
                manage_results_headers_frame,
                text=header,
                font=("Arial Bold", 12)
            ).pack(side="left", padx=5, expand=True, fill="x")

        # Scrollable list for manage results
        self.manage_results_list = ctk.CTkScrollableFrame(manage_results_frame)
        self.manage_results_list.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_statistics_tab(self, tab):
        self.stats_notebook = ctk.CTkTabview(tab)
        self.stats_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Feature Coverage tab
        self.feature_tab = self.stats_notebook.add("Feature Coverage")
        self.feature_fig, self.feature_ax = plt.subplots(figsize=(6, 4))
        self.feature_canvas = FigureCanvasTkAgg(self.feature_fig, master=self.feature_tab)
        self.feature_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Update statistics when the tab is selected
        self.stats_notebook.set("Feature Coverage")
        self.update_statistics()

    def setup_log_tab(self, tab):
        self.log_text = ctk.CTkTextbox(tab)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_request_config(self):
        """Add request configuration frame"""
        self.config_frame = ctk.CTkFrame(self.params_frame)
        self.config_frame.pack(fill="x", pady=2)
        
        # Keep-Alive
        self.keep_alive_var = ctk.BooleanVar(value=True)
        self.keep_alive_cb = ctk.CTkCheckBox(
            self.config_frame,
            text="Keep-Alive",
            variable=self.keep_alive_var
        )
        self.keep_alive_cb.pack(side="left", padx=5)
        
        # Verify SSL
        self.verify_ssl_var = ctk.BooleanVar(value=True)
        self.verify_ssl_cb = ctk.CTkCheckBox(
            self.config_frame,
            text="Verify SSL",
            variable=self.verify_ssl_var
        )
        self.verify_ssl_cb.pack(side="left", padx=5)

        # Timeout
        ctk.CTkLabel(self.config_frame, text="Timeout (s):").pack(side="left", padx=5)
        self.timeout_entry = ctk.CTkEntry(self.config_frame, width=60)
        self.timeout_entry.insert(0, "30")
        self.timeout_entry.pack(side="left", padx=5)

    def on_auth_change(self, auth_type):
        if auth_type == "None":
            self.auth_input.configure(state="disabled")
        else:
            self.auth_input.configure(state="normal")
            if auth_type == "Basic Auth":
                self.auth_input.configure(placeholder_text="username:password")
            else:  # Bearer Token
                self.auth_input.configure(placeholder_text="Enter token")

    def get_auth_headers(self):
        auth_type = self.auth_type.get()
        auth_value = self.auth_input.get()
        
        if auth_type == "Basic Auth" and auth_value:
            import base64
            auth_bytes = base64.b64encode(auth_value.encode()).decode()
            return {'Authorization': f'Basic {auth_bytes}'}
        elif auth_type == "Bearer Token" and auth_value:
            return {'Authorization': f'Bearer {auth_value}'}
        return {}

    def log_request(self, method, url, headers, body, response):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"""
=== Request [{timestamp}] ===
{method} {url}
Headers: {json.dumps(headers, indent=2)}
Body: {json.dumps(body, indent=2) if body else 'None'}

=== Response ===
Status: {response.status_code}
Headers: {json.dumps(dict(response.headers), indent=2)}
Body: {json.dumps(response.json(), indent=2) if response.headers.get('content-type', '').startswith('application/json') else response.text}
"""
        self.log_text.insert("1.0", log_entry + "\n" + "="*50 + "\n\n")

    def on_method_change(self, method):
        if method in ["POST", "PUT"]:
            self.body_text.configure(state="normal")
        else:
            self.body_text.configure(state="disabled")
            self.body_text.delete("1.0", "end")

    def send_request(self):
        try:
            start_time = time.time()
            url = self.url_entry.get()
            method = self.method_menu.get()
            
            # Combine custom headers with auth headers
            headers = {**self.get_auth_headers(), 'Content-Type': 'application/json'}
            try:
                custom_headers = json.loads(self.headers_text.get("1.0", "end-1c"))
                headers.update(custom_headers)
            except:
                pass
            
            # Get body for POST/PUT
            body = None
            if method in ["POST", "PUT"]:
                body_text = self.body_text.get("1.0", "end-1c")
                if body_text:
                    try:
                        body = json.loads(body_text)
                    except:
                        body = body_text

            # Send request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if isinstance(body, dict) else None,
                data=body if isinstance(body, str) else None,
                verify=self.verify_ssl_var.get()
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Update status and response time
            self.status_label.configure(
                text=f"Status: {response.status_code}",
                text_color="green" if 200 <= response.status_code < 300 else "red"
            )
            self.response_time_label.configure(
                text=f"Response Time: {response_time:.2f}ms"
            )

            # Display response headers
            self.resp_headers_text.delete("1.0", "end")
            self.resp_headers_text.insert("1.0", json.dumps(dict(response.headers), indent=2))

            # Display response body
            self.resp_body_text.delete("1.0", "end")
            try:
                formatted_response = json.dumps(response.json(), indent=2)
            except:
                formatted_response = response.text
            
            self.resp_body_text.insert("1.0", formatted_response)
            
            # Log request and response
            self.log_request(method, url, headers, body, response)
            
            # Update history and stats
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.add_to_history(method, url, response.status_code, timestamp)
            
            # Update feature statistics if transaction type is present
            if body and isinstance(body, dict) and "transactionType" in body:
                feat = body["transactionType"]
                if feat in self.stats["features"]:
                    self.stats["features"][feat]["total"] += 1
                    if 200 <= response.status_code < 300:
                        self.stats["features"][feat]["passed"] += 1
            
            self.update_statistics()
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.resp_body_text.delete("1.0", "end")
            self.resp_body_text.insert("1.0", error_msg)
            self.log_text.insert("1.0", f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {error_msg}\n")
            self.add_to_history(method, url, 0, datetime.now().strftime('%H:%M:%S'), error=True)
            self.status_label.configure(text="Status: Error", text_color="red")
            self.response_time_label.configure(text="Response Time: -")

    def add_to_history(self, method, url, status_code, timestamp, error=False):
        """Update statistics and logs without using request_list"""
        # Update statistics
        if 200 <= status_code < 300:
            self.stats["success"] += 1
        else:
            self.stats["failed"] += 1

        # Add to test data list
        test_case = {
            "name": f"Test {timestamp}",
            "method": method,
            "url": url,
            "status": status_code,
            "timestamp": timestamp,
            "api_name": self.api_name_var.get(),  # Ensure api_name is included
            "headers": self.headers_text.get("1.0", "end-1c"),
            "body": self.body_text.get("1.0", "end-1c")
        }
        self.add_to_data_list(test_case)
        
        # Update statistics display
        self.update_statistics()

    def update_statistics(self):
        # Reset statistics
        self.stats = {
            "success": 0,
            "failed": 0,
            "features": {}
        }

        # Collect data from test management
        for test_case in self.test_cases:
            api_name = test_case["api_name"]
            if api_name not in self.stats["features"]:
                self.stats["features"][api_name] = {"total": 0, "passed": 0}
            self.stats["features"][api_name]["total"] += 1
            if test_case["status"] == "Successful":
                self.stats["features"][api_name]["passed"] += 1

        # Update feature coverage chart
        self.feature_ax.clear()
        features = list(self.stats["features"].keys())
        total = [self.stats["features"][f]["total"] for f in features]
        passed = [self.stats["features"][f]["passed"] for f in features]
        
        x = range(len(features))
        width = 0.35
        
        self.feature_ax.bar([i - width/2 for i in x], total, width, label='Total', color='lightblue')
        self.feature_ax.bar([i + width/2 for i in x], passed, width, label='Passed', color='lightgreen')
        
        self.feature_ax.set_ylabel('Test Cases')
        self.feature_ax.set_title('Feature Coverage')
        self.feature_ax.set_xticks(x)
        self.feature_ax.set_xticklabels(features)
        self.feature_ax.legend()
        
        self.feature_canvas.draw()

    def add_to_data_list(self, test_case):
        frame = ctk.CTkFrame(self.test_results_list)
        frame.pack(fill="x", padx=5, pady=2)
        
        try:
            status_code = int(test_case.get("status", 0))
        except ValueError:
            status_code = 0
        
        status_color = "green" if 200 <= status_code < 300 else "red"
        
        # Add detailed information
        ctk.CTkLabel(frame, text=test_case["name"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["api_name"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["method"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["url"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["headers"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["body"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, 
                    text=f"Status: {test_case.get('status', 'Error')}", 
                    text_color=status_color).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case.get("response_time", "N/A")).pack(side="left", padx=5)

    def add_to_manage_list(self, test_case):
        frame = ctk.CTkFrame(self.manage_results_list)
        frame.pack(fill="x", padx=5, pady=2)
        
        # Add detailed information
        ctk.CTkLabel(frame, text=test_case["id"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["name"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["api_name"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["method"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["url"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["headers"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["body"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["status"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["response_time"]).pack(side="left", padx=5)
        
        def delete_test_case():
            self.test_cases.remove(test_case)
            frame.destroy()
            self.cursor.execute('DELETE FROM test_cases WHERE id = ?', (test_case["id"],))
            self.conn.commit()
            self.update_statistics()
        
        ctk.CTkButton(
            frame,
            text="Delete",
            command=delete_test_case,
            width=60
        ).pack(side="right", padx=5)

    def add_to_detailed_data_list(self, test_case):
        frame = ctk.CTkFrame(self.detailed_data_list)
        frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(frame, text=test_case["name"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["headers"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["body"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["status"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["response_time"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["response_headers"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["response_body"]).pack(side="left", padx=5)

    def add_test_case(self):
        """Save current test configuration"""
        api_name = self.api_name_var.get()
        test_case = {
            "id": len(self.test_cases) + 1,
            "name": f"Test Case {len(self.test_cases) + 1}",
            "method": self.method_menu.get(),
            "url": self.url_entry.get(),
            "headers": self.headers_text.get("1.0", "end-1c"),
            "body": self.body_text.get("1.0", "end-1c"),
            "auth_type": self.auth_type.get(),
            "auth_value": self.auth_input.get(),
            "config": {
                "keep_alive": self.keep_alive_var.get(),
                "timeout": float(self.timeout_entry.get()),
                "verify_ssl": self.verify_ssl_var.get()
            },
            "status": "Successful",
            "response_time": self.response_time_label.cget("text"),
            "response_headers": self.resp_headers_text.get("1.0", "end-1c"),
            "response_body": self.resp_body_text.get("1.0", "end-1c"),
            "api_name": api_name
        }
        
        self.test_cases.append(test_case)
        self.add_to_manage_list(test_case)
        self.save_test_case_to_db(test_case)
        self.update_statistics()

    def add_to_mgmt_list(self, test_case):
        frame = ctk.CTkFrame(self.mgmt_list)
        frame.pack(fill="x", padx=5, pady=2)
        
        # Add detailed information
        ctk.CTkLabel(frame, text=test_case["name"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["api_name"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["method"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["url"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["headers"]).pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=test_case["body"]).pack(side="left", padx=5)
        
        def load_test_case():
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, test_case["url"])
            self.method_menu.set(test_case["method"])
            self.headers_text.delete("1.0", "end")
            self.headers_text.insert("1.0", json.dumps(test_case["headers"], indent=2))
            self.body_text.delete("1.0", "end")
            self.body_text.insert("1.0", test_case["body"])
            self.auth_type.set(test_case["auth_type"])
            self.auth_input.delete(0, "end")
            self.auth_input.insert(0, test_case["auth_value"])
            self.status_label.configure(text=test_case["status"])
            self.response_time_label.configure(text=test_case["response_time"])
            self.resp_headers_text.delete("1.0", "end")
            self.resp_headers_text.insert("1.0", test_case["response_headers"])
            self.resp_body_text.delete("1.0", "end")
            self.resp_body_text.insert("1.0", test_case["response_body"])
        
        ctk.CTkButton(
            frame,
            text="Load",
            command=load_test_case,
            width=60
        ).pack(side="right", padx=5)

    def clear_test_results(self):
        for widget in self.test_results_list.winfo_children():
            widget.destroy()

    def clear_test_cases(self):
        self.test_cases.clear()
        for widget in self.test_results_list.winfo_children():
            widget.destroy()
        for widget in self.manage_results_list.winfo_children():
            widget.destroy()

    def run_all_tests(self):
        for test_case in self.test_cases:
            self.load_and_run_test(test_case)

    def load_and_run_test(self, test_case):
        """Load test case configuration and run it"""
        # Load configuration
        self.method_menu.set(test_case["method"])
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, test_case["url"])
        self.headers_text.delete("1.0", "end")
        self.headers_text.insert("1.0", test_case["headers"])
        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", test_case["body"])
        self.auth_type.set(test_case["auth_type"])
        self.auth_input.delete(0, "end")
        self.auth_input.insert(0, test_case["auth_value"])
        
        # Set request config
        self.keep_alive_var.set(test_case["config"]["keep_alive"])
        self.timeout_entry.delete(0, "end")
        self.timeout_entry.insert(0, str(test_case["config"]["timeout"]))
        self.verify_ssl_var.set(test_case["config"]["verify_ssl"])
        
        # Run the test
        self.send_request()



