import customtkinter as ctk
import sqlite3
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import json
from tkinter import messagebox, filedialog
import os
import traceback
import matplotlib.pyplot as plt
import pandas as pd  # Add at the top with other imports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4, landscape
from io import BytesIO
import matplotlib
import numpy as np  # Add this with other imports at the top
matplotlib.use('Agg')  # Required for saving plots to memory
from config.app_config import AppConfig

class ManualTestView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config = AppConfig()
        
        # Use config values for constants
        self.STATUS_COLORS = self.config.MANUAL_TEST_CONFIG["status_colors"]
        self.STATUS_VALUES = self.config.MANUAL_TEST_CONFIG["statuses"]
        self.TEST_CASE_PREFIX = self.config.MANUAL_TEST_CONFIG["test_case_prefix"]
        self.DEFAULT_TEMPLATES = self.config.MANUAL_TEST_CONFIG["default_templates"]
        self.supported_images = self.config.MANUAL_TEST_CONFIG["supported_images"]
        
        # Initialize database path from config
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.config.DB_PATHS["manual_test"]
        )
        
        # Initialize evidence list
        self.evidence_list = []
        self.evidence_label = None
        
        # Core variables initialization
        self.initialize_variables()
        self.setup_database()
        self.create_widgets()
        self.after(100, self.refresh_table_view)

    def initialize_variables(self):
        """Initialize core variables with config values"""
        self.default_hostname = os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or "Unknown"
        
        # Add required fields definition
        self.fields = {
            'required': [
                'test_case_id',
                'feature',
                'description',
                'test_steps',
                'expected_result',
                'status'
            ]
        }
        
        self.vars = {
            'hostname': ctk.StringVar(value=self.default_hostname),
            'env': ctk.StringVar(value=self.config.MANUAL_TEST_CONFIG["environments"][0]),
            'browser': ctk.StringVar(value=self.config.MANUAL_TEST_CONFIG["browsers"][0]),
            'feature': ctk.StringVar(),
            'status': ctk.StringVar(value=self.config.MANUAL_TEST_CONFIG["statuses"][0])
        }
        
        # Use config values for column definitions
        self.columns = self.config.MANUAL_TEST_CONFIG["table_columns"]
        self.col_widths = self.config.MANUAL_TEST_CONFIG["column_widths"]
        
        # Features from config
        self.features = self.config.MANUAL_TEST_CONFIG["features"]
        
        # UI settings from config
        self.ui_config = {
            'row_height': self.config.UI_SETTINGS["row_height"],
            'padding': self.config.UI_SETTINGS["padding"],
            'font_size': self.config.FONT_SIZES["medium"]
        }
        
        # Add pagination settings
        self.current_page = 1
        self.rows_per_page = 10  # Add this line to set default rows per page

    def normalize_status(self, status):
        """Simplified status normalization"""
        status = str(status).lower().strip()
        if 'pass' in status:
            return 'Pass'
        if 'fail' in status:
            return 'Fail'
        return 'Not Executed'

    def get_status_color(self, status):
        """Get color for status"""
        return self.STATUS_COLORS.get(self.normalize_status(status), 'gray')

    def setup_database(self):
        """Setup database with proper error handling and table creation"""
        try:
            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if (db_dir and not os.path.exists(db_dir)):
                os.makedirs(db_dir)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create the test_cases table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS test_cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hostname TEXT,
                        environment TEXT,
                        browser TEXT,
                        feature TEXT,
                        test_case_id TEXT UNIQUE,
                        description TEXT,
                        test_steps TEXT,
                        expected_result TEXT,
                        actual_result TEXT,
                        status TEXT,
                        notes TEXT,
                        evidence_paths TEXT,
                        created_date TEXT
                    )
                ''')
                conn.commit()
                
                # Verify table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_cases'")
                if not cursor.fetchone():
                    raise Exception("Failed to create test_cases table")
                    
        except Exception as e:
            print(f"Database setup error: {e}")
            messagebox.showerror("Database Error", 
                               "Failed to setup database. Please check permissions and disk space.")
            raise

    def create_widgets(self):
        # Title with consistent theme and centered
        header_frame = ctk.CTkFrame(self, fg_color=self.cget("fg_color"))
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header_frame, 
            text="Manual Test Case Management", 
            font=("Arial", 24, "bold"),
            text_color=("gray10", "gray90")
        )
        title.pack(expand=True)  # Center the title

        # Create TabView with updated styling
        self.tab_view = ctk.CTkTabview(
            self,
            fg_color=("gray95", "gray13"),
            segmented_button_fg_color=("gray90", "gray17"),
            segmented_button_selected_color=("gray75", "gray28"),
            segmented_button_selected_hover_color=("gray70", "gray32")
        )
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=10)

        # Create tabs with consistent padding
        self.detail_tab = self.tab_view.add("Test Case Detail")
        self.list_tab = self.tab_view.add("Test Cases List")
        
        # Create content for each tab
        self.create_detail_panel(self.detail_tab)
        self.create_test_cases_list(self.list_tab)

    def create_detail_panel(self, parent):
        """Create detail panel using config values"""
        container = ctk.CTkFrame(parent)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        # Environment selection with config values
        env_frame = ctk.CTkFrame(container)
        env_frame.pack(fill="x", pady=5)
        
        for i, (label, var, values) in enumerate([
            ("Hostname", self.vars['hostname'], [self.default_hostname]),
            ("Environment", self.vars['env'], self.config.MANUAL_TEST_CONFIG["environments"]),
            ("Browser", self.vars['browser'], self.config.MANUAL_TEST_CONFIG["browsers"])
        ]):
            ctk.CTkLabel(env_frame, text=label).grid(row=0, column=i*2, padx=5, pady=5)
            ctk.CTkOptionMenu(
                env_frame,
                variable=var,
                values=values,
                width=150
            ).grid(row=0, column=i*2+1, padx=5, pady=5)

        # Feature and Test Case ID section
        id_frame = ctk.CTkFrame(container)
        id_frame.pack(fill="x", pady=5)
        
        # Feature dropdown
        ctk.CTkLabel(id_frame, text="Feature:").grid(row=0, column=0, padx=5, pady=5)
        self.feature_dropdown = ctk.CTkOptionMenu(
            id_frame,
            variable=self.vars['feature'],
            values=self.features,
            width=200
        )
        self.feature_dropdown.grid(row=0, column=1, padx=5, pady=5)

        # Test Case ID with generate button
        ctk.CTkLabel(id_frame, text="Test Case ID:").grid(row=0, column=2, padx=5, pady=5)
        self.tc_id_entry = ctk.CTkEntry(id_frame, width=150)
        self.tc_id_entry.grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkButton(
            id_frame,
            text="Generate ID",
            command=self.generate_test_case_id,
            width=100
        ).grid(row=0, column=4, padx=5, pady=5)

        # Create scrollable frame for test details
        details_scroll = ctk.CTkScrollableFrame(container)
        details_scroll.pack(fill="both", expand=True, pady=5)

        # Add all text sections
        sections = [
            ("Test Description", "desc_text", 100),
            ("Test Steps", "steps_text", 150),
            ("Expected Results", "expected_text", 100),
            ("Actual Results", "actual_text", 100),
            ("Notes", "notes_text", 100)
        ]

        for title, attr_name, height in sections:
            frame = ctk.CTkFrame(details_scroll)
            frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(frame, text=title, font=("Arial", 12, "bold")).pack(anchor="w", padx=5)
            textbox = ctk.CTkTextbox(frame, height=height)
            textbox.pack(fill="x", padx=5, pady=5)
            setattr(self, attr_name, textbox)

        # Status and Evidence frame
        control_frame = ctk.CTkFrame(details_scroll)
        control_frame.pack(fill="x", pady=5)

        # Status dropdown with standardized values
        status_frame = ctk.CTkFrame(control_frame)
        status_frame.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(status_frame, text="Status:").pack(side="left", padx=5)
        self.status_dropdown = ctk.CTkOptionMenu(
            status_frame,
            variable=self.vars['status'],
            values=self.STATUS_VALUES  # Use standard status values only
        )
        self.status_dropdown.pack(side="left", padx=5)

        # Evidence section with proper initialization
        evidence_frame = ctk.CTkFrame(control_frame)
        evidence_frame.pack(side="right", fill="x", expand=True, padx=5)
        
        self.evidence_button = ctk.CTkButton(
            evidence_frame,
            text="Add Evidence",
            command=self.add_evidence
        )
        self.evidence_button.pack(side="left", padx=5)
        
        self.evidence_label = ctk.CTkLabel(evidence_frame, text="0 files")
        self.evidence_label.pack(side="left", padx=5)

        # Save button frame at bottom
        save_frame = ctk.CTkFrame(container)
        save_frame.pack(fill="x", pady=5)
        ctk.CTkButton(
            save_frame,
            text="Save Test Case",
            command=self.save_test_case,
            width=120
        ).pack(side="right", padx=10)

        # Set default texts
        self.desc_text.insert("1.0", self.DEFAULT_TEMPLATES['desc'])
        self.steps_text.insert("1.0", self.DEFAULT_TEMPLATES['steps'])
        self.expected_text.insert("1.0", self.DEFAULT_TEMPLATES['expected'])
        self.actual_text.insert("1.0", self.DEFAULT_TEMPLATES['actual'])
        self.notes_text.insert("1.0", self.DEFAULT_TEMPLATES['notes'])

    def create_test_cases_list(self, parent):
        """Create simplified list view with just the table"""
        # Main container with no extra padding
        main_frame = ctk.CTkFrame(parent, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=5, pady=2)  # Reduced outer padding

        # Buttons frame with minimal padding
        buttons_frame = ctk.CTkFrame(
            main_frame,
            fg_color=("gray95", "gray13"),
            corner_radius=6
        )
        buttons_frame.pack(fill="x", pady=(2, 2), padx=2)  # Reduced padding

        # Add buttons (unchanged)
        ctk.CTkButton(
            buttons_frame,
            text="📊 Statistics Dashboard",
            command=self.show_statistics_dashboard,
            width=150,
            height=32,
            hover_color="#404040"
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            buttons_frame,
            text="📄 Generate PDF",
            command=self.generate_report,
            width=120,
            height=32,
            hover_color="#404040"
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            buttons_frame,
            text="📊 Export to Excel",
            command=self.generate_excel_report,
            width=120,
            height=32,
            hover_color="#404040"
        ).pack(side="left", padx=5, pady=5)

        # Table frame with minimal padding
        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=2, pady=2)  # Reduced padding

        # Fixed header with minimal height
        header_frame = ctk.CTkFrame(table_frame, height=32)  # Reduced height
        header_frame.pack(fill="x", padx=2, pady=0)  # Removed vertical padding
        header_frame.pack_propagate(False)

        # Create header columns
        for col in self.columns:
            col_frame = ctk.CTkFrame(
                header_frame,
                width=self.col_widths[col],
                height=32,  # Reduced height
                fg_color=("gray85", "gray25")
            )
            col_frame.pack(side="left", padx=1, pady=0)  # Removed vertical padding
            col_frame.pack_propagate(False)
            
            ctk.CTkLabel(
                col_frame,
                text=col,
                font=("Arial", 11, "bold"),
                fg_color="transparent",
                text_color=("gray20", "gray90")
            ).place(relx=0.5, rely=0.5, anchor="center")

        # Content area with minimal padding
        content_frame = ctk.CTkFrame(table_frame)
        content_frame.pack(fill="both", expand=True, padx=0, pady=0)  # Removed padding

        # Canvas setup with minimal padding
        canvas = ctk.CTkCanvas(
            content_frame,
            bg=self._apply_appearance_mode(self.cget("fg_color")),
            highlightthickness=0
        )
        v_scrollbar = ctk.CTkScrollbar(content_frame, orientation="vertical", command=canvas.yview)
        h_scrollbar = ctk.CTkScrollbar(content_frame, orientation="horizontal", command=canvas.xview)

        # Configure canvas
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        # Table container with minimal padding
        self.table_container = ctk.CTkFrame(canvas, fg_color="transparent")
        canvas_window = canvas.create_window((0, 0), window=self.table_container, anchor="nw")

        # Pack scrollbars and canvas tightly
        v_scrollbar.pack(side="right", fill="y", padx=0, pady=0)
        h_scrollbar.pack(side="bottom", fill="x", padx=0, pady=0)
        canvas.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # Pagination frame with minimal padding
        pagination_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        pagination_frame.pack(fill="x", pady=(2, 2))  # Reduced padding
        
        self.prev_button = ctk.CTkButton(
            pagination_frame, 
            text="Previous",
            command=self.prev_page,
            width=100
        )
        self.prev_button.pack(side="left", padx=5)
        
        self.page_label = ctk.CTkLabel(
            pagination_frame,
            text="Page 1",
            font=("Arial", 12)
        )
        self.page_label.pack(side="left", padx=5)
        
        self.next_button = ctk.CTkButton(
            pagination_frame,
            text="Next",
            command=self.next_page,
            width=100
        )
        self.next_button.pack(side="left", padx=5)

        # Update scroll region function
        def update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Set fixed width for content
            content_width = sum(self.col_widths.values()) + 20  # Reduced padding
            canvas.itemconfig(canvas_window, width=max(content_width, canvas.winfo_width()))

        # Bind scroll region updates
        self.table_container.bind("<Configure>", update_scroll_region)

        # Mouse wheel scrolling
        def on_mousewheel(event):
            if event.state & 1:  # Shift key is held down
                canvas.xview_scroll(int(-1 * (event.delta/120)), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta/120)), "units")

        # Bind mouse wheel events
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        canvas.bind_all("<Shift-MouseWheel>", on_mousewheel)

    def create_table_row(self, parent, data, row_num):
        """Create a table row with minimal spacing"""
        row_frame = ctk.CTkFrame(
            parent,
            fg_color=("gray90", "gray17") if row_num % 2 == 0 else ("gray95", "gray13"),
            height=32  # Reduced height
        )
        row_frame.pack(fill="x", padx=2, pady=0)  # Minimal padding
        row_frame.pack_propagate(False)

        # Actions column first
        actions_frame = ctk.CTkFrame(
            row_frame,
            width=self.col_widths["Actions"],
            fg_color="transparent"
        )
        actions_frame.pack(side="left", padx=1)
        actions_frame.pack_propagate(False)

        # Action buttons
        buttons_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        buttons_frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkButton(
            buttons_frame,
            text="✎",
            width=25,
            height=25,
            command=lambda: self.edit_test_case(data["TestCaseID"])
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            buttons_frame,
            text="×",
            width=25,
            height=25,
            fg_color="red",
            command=lambda: self.confirm_row_delete(data["TestCaseID"])
        ).pack(side="left", padx=1)

        # Other columns
        for col in self.columns[1:]:  # Skip Actions column
            cell_frame = ctk.CTkFrame(
                row_frame,
                width=self.col_widths[col],
                fg_color="transparent"
            )
            cell_frame.pack(side="left", padx=1)
            cell_frame.pack_propagate(False)

            value = str(data.get(col, ""))
            text = value[:30] + "..." if len(value) > 30 else value

            if col == "Status":
                normalized_status = self.normalize_status(value)
                fg_color = self.get_status_color(normalized_status)
            else:
                fg_color = "transparent"

            ctk.CTkLabel(
                cell_frame,
                text=text,
                fg_color=fg_color,
                width=self.col_widths[col]-5
            ).place(relx=0.5, rely=0.5, anchor="center")

        return row_frame

    def confirm_row_delete(self, test_case_id):
        """Confirm deletion of a specific row"""
        if messagebox.askyesno("Confirm Delete", f"Delete test case {test_case_id}?"):
            self.delete_test_case_by_id(test_case_id)

    def refresh_table_view(self):
        """Refresh table view with pagination"""
        try:
            if not hasattr(self, 'table_container'):
                return
                
            for widget in self.table_container.winfo_children():
                widget.destroy()
            
            # Open single database connection for all operations
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Get total count first
                cursor.execute('SELECT COUNT(*) FROM test_cases')
                total_rows = cursor.fetchone()[0]
                total_pages = (total_rows + self.rows_per_page - 1) // self.rows_per_page
                
                # Update page label
                self.page_label.configure(text=f"Page {self.current_page} of {total_pages}")
                
                # Enable/disable pagination buttons
                self.prev_button.configure(state="normal" if self.current_page > 1 else "disabled")
                self.next_button.configure(state="normal" if self.current_page < total_pages else "disabled")
                
                # Calculate offset for pagination
                offset = (self.current_page - 1) * self.rows_per_page
                
                # Get paginated data
                cursor.execute(
                    'SELECT * FROM test_cases ORDER BY id DESC LIMIT ? OFFSET ?',
                    (self.rows_per_page, offset)
                )
                rows = cursor.fetchall()
                
                for i, row in enumerate(rows, 1):
                    data = self.prepare_row_data(row)
                    data["No."] = str(offset + i)  # Update row numbers for current page
                    self.create_table_row(self.table_container, data, i)

                # Get final count and update total count label
                cursor.execute('SELECT COUNT(*) FROM test_cases')
                total_count = cursor.fetchone()[0]
                if hasattr(self, 'total_count_label'):
                    self.total_count_label.configure(text=str(total_count))
                    
            finally:
                # Ensure connection is closed in finally block
                conn.close()
                    
        except Exception as e:
            print(f"Error refreshing table view: {e}")
            traceback.print_exc()

    def next_page(self):
        """Go to next page"""
        self.current_page += 1
        self.refresh_table_view()

    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_table_view()

    def prepare_row_data(self, row):
        """Prepare row data for display with matching column keys"""
        evidence_count = len(json.loads(row[12])) if row[12] else 0
        return {
            "Actions": "",
            "No.": "",  # Will be set by refresh_table_view
            "TestCaseID": row[5],
            "Feature": row[4],
            "Description": row[6],
            "TestSteps": row[7],
            "Expected": row[8],
            "Actual": row[9],
            "Status": row[10],
            "Environment": row[2],
            "Browser": row[3],
            "Evidence": f"{evidence_count} files",
            "Date": row[13]
        }

    def save_test_case(self):
        """Simplified save operation"""
        try:
            # Get form data
            data = self.get_form_data()
            
            # Validate required fields
            if missing := [f for f in self.fields['required'] if not data.get(f)]:
                messagebox.showerror("Error", f"Please fill required fields: {', '.join(missing)}")
                return
                
            # Normalize status
            data['status'] = self.normalize_status(data['status'])
            
            # Save to database
            self.save_to_database(data)
            
            # Refresh view
            self.refresh_table_view()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            traceback.print_exc()

    def get_form_data(self):
        """Get data from all form fields"""
        try:
            data = {
                'hostname': self.vars['hostname'].get(),
                'environment': self.vars['env'].get(),
                'browser': self.vars['browser'].get(),
                'feature': self.vars['feature'].get(),
                'test_case_id': self.tc_id_entry.get(),
                'description': self.desc_text.get("1.0", "end-1c"),
                'test_steps': self.steps_text.get("1.0", "end-1c"),
                'expected_result': self.expected_text.get("1.0", "end-1c"),
                'actual_result': self.actual_text.get("1.0", "end-1c"),
                'status': self.vars['status'].get(),
                'notes': self.notes_text.get("1.0", "end-1c"),
                'evidence_paths': json.dumps(self.evidence_list),
                'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            return data
        except Exception as e:
            print(f"Error getting form data: {e}")
            raise

    def save_to_database(self, data):
        """Save test case data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if test case ID already exists
            cursor.execute('SELECT id FROM test_cases WHERE test_case_id = ?', (data['test_case_id'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                fields = list(data.keys())
                update_fields = [f"{field} = ?" for field in fields]
                values = list(data.values())
                values.append(data['test_case_id'])
                
                cursor.execute(f'''
                    UPDATE test_cases 
                    SET {', '.join(update_fields)}
                    WHERE test_case_id = ?
                ''', values)
            else:
                # Insert new record
                fields = list(data.keys())
                placeholders = ['?' for _ in fields]
                values = list(data.values())
                
                cursor.execute(f'''
                    INSERT INTO test_cases 
                    ({', '.join(fields)})
                    VALUES ({', '.join(placeholders)})
                ''', values)
                
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Test case saved successfully")
            self.clear_form()
            
        except Exception as e:
            print(f"Error saving to database: {e}")
            traceback.print_exc()
            raise

    def clear_form(self):
        """Clear all form fields and restore defaults"""
        # Use hostname_var instead of hostname_entry
        self.vars['hostname'].set(self.default_hostname)
        self.vars['env'].set("Production")
        self.vars['browser'].set("Chrome")
        self.vars['feature'].set(self.features[0])
        self.tc_id_entry.delete(0, 'end')
        
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", self.DEFAULT_TEMPLATES['desc'])
        
        self.steps_text.delete("1.0", "end")
        self.steps_text.insert("1.0", self.DEFAULT_TEMPLATES['steps'])
        
        self.expected_text.delete("1.0", "end")
        self.expected_text.insert("1.0", self.DEFAULT_TEMPLATES['expected'])
        
        self.actual_text.delete("1.0", "end")
        self.actual_text.insert("1.0", self.DEFAULT_TEMPLATES['actual'])
        
        self.vars['status'].set("Not Executed")
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", self.DEFAULT_TEMPLATES['notes'])
        self.evidence_list = []

    def delete_test_case_by_id(self, test_case_id):
        """Delete test case by its ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM test_cases WHERE test_case_id=?', (test_case_id,))
            conn.commit()
            conn.close()
            self.refresh_table_view()
            messagebox.showinfo("Success", "Test case deleted successfully")
        except Exception as e:
            print(f"Error deleting test case: {e}")
            messagebox.showerror("Error", "Failed to delete test case")

    def generate_test_case_id(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            feature_prefix = self.vars['feature'].get()[:3].upper()
            cursor.execute('SELECT COUNT(*) FROM test_cases WHERE feature = ?', (self.vars['feature'].get(),))
            count = cursor.fetchone()[0] + 1
            new_id = f"{self.TEST_CASE_PREFIX}_{feature_prefix}_{count:03d}"  # Use the constant here
            self.tc_id_entry.delete(0, 'end')
            self.tc_id_entry.insert(0, new_id)
            conn.close()
        except Exception as e:
            print(f"Error generating test case ID: {e}")

    def generate_report(self):
        """Generate enhanced PDF report using config settings"""
        try:
            report_dir = self.config.REPORT_CONFIG["output_dir"]
            os.makedirs(report_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(report_dir, f"test_cases_report_{timestamp}.pdf")
            
            # Create PDF document
            doc = SimpleDocTemplate(filename, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                spaceAfter=30
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=20
            )
            
            # Add title and date
            elements.append(Paragraph("Test Cases Execution Report", title_style))
            elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Fetch statistics
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Overall statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'Pass' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN status = 'Fail' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'Not Executed' THEN 1 ELSE 0 END) as not_executed
                FROM test_cases
            ''')
            total, passed, failed, not_executed = cursor.fetchone()
            
            # Create executive summary
            elements.append(Paragraph("Executive Summary", heading_style))
            
            summary_data = [
                ["Metric", "Count", "Percentage"],
                ["Total Test Cases", str(total), "100%"],
                ["Passed", str(passed), f"{(passed/total*100 if total else 0):.1f}%"],
                ["Failed", str(failed), f"{(failed/total*100 if total else 0):.1f}%"],
                ["Not Executed", str(not_executed), f"{(not_executed/total*100 if total else 0):.1f}%"]
            ]
            
            summary_table = Table(summary_data, colWidths=[200, 100, 100])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))
            
            # Add detailed test cases section
            elements.append(Paragraph("Detailed Test Cases", heading_style))
            
            # Fetch detailed test cases data
            cursor.execute('''
                SELECT 
                    test_case_id, feature, description, test_steps,
                    expected_result, actual_result, status, environment,
                    browser, created_date, notes, evidence_paths
                FROM test_cases
                ORDER BY feature, test_case_id
            ''')
            data = cursor.fetchall()
            
            if data:
                # Create vertical layout for each test case
                for test_case in data:
                    # Add all elements from create_test_case_detail
                    elements.extend(self.create_test_case_detail(test_case))
                    elements.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(elements)
            messagebox.showinfo("Success", f"Report generated successfully: {filename}")
            
        except Exception as e:
            print(f"Error generating report: {e}")
            traceback.print_exc()

    def create_test_case_detail(self, test_case):
        """Create a vertical layout table for a single test case with evidence"""
        test_case_id = test_case[0]
        evidence_files = json.loads(test_case[11]) if test_case[11] else []
        
        elements = []
        
        # Main test case data
        fields = [
            ("Test Case ID:", test_case[0]),
            ("Feature:", test_case[1]),
            ("Description:", test_case[2]),
            ("Test Steps:", test_case[3]),
            ("Expected Result:", test_case[4]),
            ("Actual Result:", test_case[5]),
            ("Status:", test_case[6]),
            ("Environment:", test_case[7]),
            ("Browser:", test_case[8]),
            ("Date:", test_case[9]),
            ("Notes:", test_case[10])
        ]
        
        # Create table data
        table_data = [[label, str(value)] for label, value in fields]
        
        # Add evidence images to the table if they exist
        if evidence_files:
            table_data.append(["Evidence:", ""])  # Header row for evidence
            for file_path in evidence_files:
                try:
                    if os.path.exists(file_path):
                        # Create Image object with adjusted size
                        img = Image(file_path)
                        # Calculate aspect ratio to maintain proportions
                        aspect = img.imageWidth / float(img.imageHeight)
                        # Set maximum width and calculate height
                        target_width = 200  # Smaller width for table cell
                        target_height = target_width / aspect
                        img.drawWidth = target_width
                        img.drawHeight = target_height
                        # Add image and filename to table
                        table_data.append(["", img])
                        table_data.append(["", f"File: {os.path.basename(file_path)}"])
                except Exception as e:
                    print(f"Error processing image {file_path}: {e}")
                    table_data.append(["", f"Error loading image: {os.path.basename(file_path)}"])
        
        # Create table with adjusted widths
        table = Table(table_data, colWidths=[120, 380])
        
        # Apply styles
        table_style = [
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8E8E8')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2B2B2B')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, -1), 10),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (1, 0), (1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # Special status row styling
            ('BACKGROUND', (1, 6), (1, 6), {
                'Pass': colors.HexColor('#E6FFE6'),
                'Fail': colors.HexColor('#FFE6E6'),
                'Not Executed': colors.HexColor('#F0F0F0')
            }.get(test_case[6], colors.white))
        ]
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        return elements

    def show_piechart(self):
        """Show statistics in pie chart using matplotlib"""
        try:
            # Get status counts from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM test_cases 
                GROUP BY status
            ''')
            stats = cursor.fetchall()
            conn.close()

            if not stats:
                messagebox.showinfo("Info", "No data available for statistics")
                return

            # Prepare data for pie chart
            labels = [stat[0] for stat in stats]
            sizes = [stat[1] for stat in stats]
            colors = {
                "Pass": "#00B000",      # Green
                "Fail": "#CC0000",      # Red
                "Not Executed": "#808080" # Gray
            }
            pie_colors = [colors.get(label, "#0000FF") for label in labels]

            # Create new figure with a decent size
            plt.figure(figsize=(8, 6))
            plt.pie(sizes, labels=labels, colors=pie_colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Test Case Status Distribution')
            
            # Show the plotQ
            plt.show()
            
        except Exception as e:
            print(f"Error showing statistics: {e}")
            traceback.print_exc()
    
    def add_evidence(self):
        """Add evidence files to the test case"""
        try:
            files = filedialog.askopenfilenames(
                title="Select Evidence Images",
                filetypes=self.supported_images
            )
            
            if files:
                # Add selected files to evidence list
                for file in files:
                    if file not in self.evidence_list:
                        self.evidence_list.append(file)
                
                # Update evidence label
                if hasattr(self, 'evidence_label'):
                    self.evidence_label.configure(text=f"{len(self.evidence_list)} files")
                    
                messagebox.showinfo(
                    "Evidence Added", 
                    f"Added {len(files)} evidence file(s)"
                )
                
        except Exception as e:
            print(f"Error adding evidence: {e}")
            messagebox.showerror(
                "Error", 
                f"Failed to add evidence files: {str(e)}"
            )

    def edit_test_case(self, test_case_id=None):
        """Load test case into detail view and switch tabs"""
        if test_case_id is None:
            messagebox.showwarning("Warning", "No test case selected")
            return
            
        self.load_test_case_by_tc_id(test_case_id)
        self.tab_view.set("Test Case Detail")

    def load_test_case_by_tc_id(self, test_case_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM test_cases WHERE test_case_id = ?', (test_case_id,))
            row = cursor.fetchone()
            
            if row:
                # Update all fields in detail view
                self.vars['hostname'].set(row[1])
                self.vars['env'].set(row[2])
                self.vars['browser'].set(row[3])
                self.vars['feature'].set(row[4])
                self.tc_id_entry.delete(0, 'end')
                self.tc_id_entry.insert('0', row[5])
                
                # Clear and set text boxes
                self.desc_text.delete('1.0', 'end')
                self.desc_text.insert('1.0', row[6])
                self.steps_text.delete('1.0', 'end')
                self.steps_text.insert('1.0', row[7])
                self.expected_text.delete('1.0', 'end')
                self.expected_text.insert('1.0', row[8])
                self.actual_text.delete('1.0', 'end')
                self.actual_text.insert('1.0', row[9])
                self.vars['status'].set(row[10])
                self.notes_text.delete('1.0', 'end')
                self.notes_text.insert('1.0', row[11])
                
                # Handle evidence paths
                self.evidence_list = json.loads(row[12]) if row[12] else []
            
            conn.close()
        except Exception as e:
            print(f"Error loading test case: {e}")
            traceback.print_exc()

    def show_statistics_dashboard(self):
        """Show comprehensive statistics dashboard with improved visualization"""
        try:
            # Create window
            stats_window = ctk.CTkToplevel(self)
            stats_window.title("Test Cases Statistics")
            stats_window.geometry("1000x800")
            
            # Get the current theme colors
            current_theme = self.cget("fg_color")
            bg_color = current_theme[1] if isinstance(current_theme, tuple) else current_theme
            
            # Configure window with theme color
            stats_window.configure(fg_color=bg_color)
            
            # Create TabView with theme-aware colors
            tab_view = ctk.CTkTabview(stats_window)
            tab_view.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Add tabs
            self.table_tab = tab_view.add("Table View")
            self.chart_tab = tab_view.add("Chart View")

            # Get data from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # First normalize all statuses in the database
                cursor.execute('''
                    UPDATE test_cases 
                    SET status = 
                        CASE 
                            WHEN LOWER(status) IN ('pass', 'passed', 'p') THEN 'Pass'
                            WHEN LOWER(status) IN ('fail', 'failed', 'f') THEN 'Fail'
                            ELSE 'Not Executed'
                        END
                ''')
                conn.commit()

                # Then get the counts with the normalized statuses
                cursor.execute('''
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM test_cases
                    GROUP BY status
                    ORDER BY 
                        CASE status
                            WHEN 'Pass' THEN 1
                            WHEN 'Fail' THEN 2
                            ELSE 3
                        END
                ''')
                status_counts = cursor.fetchall()

                # Initialize all possible status counts to 0
                status_dict = {'Pass': 0, 'Fail': 0, 'Not Executed': 0}
                
                # Update with actual counts
                for status, count in status_counts:
                    normalized_status = self.normalize_status(status)
                    status_dict[normalized_status] = count

                # Get values in fixed order
                passed = status_dict['Pass']
                failed = status_dict['Fail']
                not_executed = status_dict['Not Executed']
                total = sum(status_dict.values())

                # Debug print to verify counts
                print("Raw status counts from DB:", status_counts)
                print("Normalized status dict:", status_dict)
                print(f"Final counts - Pass: {passed}, Fail: {failed}, Not Executed: {not_executed}, Total: {total}")

                # Update feature query to use normalized status
                cursor.execute('''
                    SELECT 
                        feature,
                        SUM(CASE WHEN status = 'Pass' THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN status = 'Fail' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'Not Executed' THEN 1 ELSE 0 END) as not_executed
                    FROM test_cases 
                    GROUP BY feature
                ''')
                feature_stats = cursor.fetchall()

                # Debug print
                print(f"Total: {total}, Passed: {passed}, Failed: {failed}, Not Executed: {not_executed}")
                print(f"Feature stats: {feature_stats}")

                # TABLE VIEW
                table_frame = ctk.CTkFrame(self.table_tab)
                table_frame.pack(fill="both", expand=True, padx=10, pady=10)

                # Title
                title = ctk.CTkLabel(
                    table_frame,
                    text="Test Cases Statistics Summary",
                    font=("Arial", 20, "bold")
                )
                title.pack(pady=(0, 20))

                # Overall Statistics Section
                overall_frame = ctk.CTkFrame(table_frame)
                overall_frame.pack(fill="x", padx=10, pady=10)

                overall_title = ctk.CTkLabel(
                    overall_frame,
                    text="Overall Statistics",
                    font=("Arial", 16, "bold")
                )
                overall_title.pack(pady=10)

                # Create overall statistics table
                stats_data = [
                    ["Total Test Cases", total],
                    ["Passed", passed],
                    ["Failed", failed],
                    ["Not Executed", not_executed]
                ]

                # Overall Statistics Section - Table View
                for label, value in stats_data:
                    row_frame = ctk.CTkFrame(overall_frame)
                    row_frame.pack(fill="x", padx=5, pady=2)
                    
                    percentage = (value/total*100) if total > 0 else 0
                    
                    ctk.CTkLabel(row_frame, text=label, width=150).pack(side="left", padx=5)
                    ctk.CTkLabel(
                        row_frame, 
                        text=str(value), 
                        width=100,
                        fg_color=("green" if label == "Passed" else 
                                 "red" if label == "Failed" else 
                                 "gray" if label == "Not Executed" else "transparent"),
                        corner_radius=5
                    ).pack(side="left", padx=5)
                    ctk.CTkLabel(
                        row_frame,
                        text=f"{percentage:.1f}%",
                        width=100
                    ).pack(side="left", padx=5)

                # Feature Statistics Section
                feature_frame = ctk.CTkFrame(table_frame)
                feature_frame.pack(fill="x", padx=10, pady=(20, 10))

                feature_title = ctk.CTkLabel(
                    feature_frame,
                    text="Feature-wise Statistics",
                    font=("Arial", 16, "bold")
                )
                feature_title.pack(pady=10)

                # Headers for feature table
                header_frame = ctk.CTkFrame(feature_frame)
                header_frame.pack(fill="x", padx=5, pady=2)
                
                headers = ["Feature", "Passed", "Failed", "Not Executed", "Total"]
                for header in headers:
                    ctk.CTkLabel(
                        header_frame,
                        text=header,
                        font=("Arial", 12, "bold"),
                        width=120
                    ).pack(side="left", padx=5)

                # Feature data
                for feature, passed, failed, not_exec in feature_stats:
                    row_frame = ctk.CTkFrame(feature_frame)
                    row_frame.pack(fill="x", padx=5, pady=2)
                    
                    feature_total = (passed or 0) + (failed or 0) + (not_exec or 0)
                    
                    ctk.CTkLabel(row_frame, text=feature, width=120).pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(passed or 0), width=120, fg_color="green3").pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(failed or 0), width=120, fg_color="red3").pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(not_exec or 0), width=120, fg_color="gray").pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(feature_total), width=120).pack(side="left", padx=5)

                # CHART VIEW
                chart_frame = ctk.CTkFrame(self.chart_tab)
                chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

                # Title frame
                title_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
                title_frame.pack(fill="x", pady=(0, 20))
                
                ctk.CTkLabel(
                    title_frame,
                    text="Test Cases Distribution Dashboard",
                    font=("Arial", 20, "bold")
                ).pack(pady=10)

                # Main chart container with nested frames for visual depth
                outer_chart_frame = ctk.CTkFrame(chart_frame)
                outer_chart_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
                middle_chart_frame = ctk.CTkFrame(
                    outer_chart_frame,
                    fg_color=("gray90", "gray17")
                )
                middle_chart_frame.pack(fill="both", expand=True, padx=2, pady=2)
                
                inner_chart_frame = ctk.CTkFrame(
                    middle_chart_frame,
                    fg_color=("gray95", "gray13")
                )
                inner_chart_frame.pack(fill="both", expand=True, padx=2, pady=2)

                # Prepare data
                status_values = [passed, failed, not_executed]
                status_labels = [f'Pass ({passed})', f'Fail ({failed})', f'Not Executed ({not_executed})']
                status_colors = ['#2ECC71', '#E74C3C', '#95A5A6']
                
                # Create figure with two subplots side by side
                fig = plt.Figure(figsize=(15, 7))
                # Get theme colors
                is_dark_theme = self.cget("fg_color")[1] == "gray13"
                bg_color = '#2B2B2B' if is_dark_theme else '#F0F0F0'
                text_color = 'white' if is_dark_theme else 'black'

                # Set figure background color
                fig.patch.set_facecolor(bg_color)

                # Status Distribution Chart (Left) - Pie Chart
                ax1 = fig.add_subplot(121)
                ax1.set_facecolor(bg_color)
                
                if total > 0:
                    # Ensure data order matches labels
                    status_values = [passed, failed, not_executed]
                    status_labels = [f'Pass ({passed})', f'Fail ({failed})', f'Not Executed ({not_executed})']
                    
                    # Create pie chart with ordered data
                    wedges1, texts1, autotexts1 = ax1.pie(
                        x=status_values,  # Use ordered values instead of status_counts
                        labels=status_labels,
                        colors=['#2ECC71', '#E74C3C', '#95A5A6'],
                        startangle=90,
                        autopct='%1.1f%%'
                    )
                    
                    # Set text colors
                    plt.setp(texts1, color=text_color)
                    plt.setp(autotexts1, color=text_color)

                ax1.set_title(
                    f"Test Status Distribution\nTotal: {total} test cases",
                    color=text_color,
                    pad=20,
                    fontsize=14
                )

                # Feature Distribution Chart (Right)
                ax2 = fig.add_subplot(122)
                ax2.set_facecolor(bg_color)

                if feature_stats:
                    feature_totals = [(stat[0], sum(stat[1:4])) for stat in feature_stats]
                    features = []
                    values = []
                    
                    # Calculate exact percentages for features
                    for feature, feature_total in feature_totals:
                        feature_pct = self.calculate_percentage(feature_total, total)
                        features.append(f'{feature}: {feature_total} ({feature_pct:.1f}%)')
                        values.append(float(feature_total))  # Convert to float explicitly
                    
                    # Convert to numpy array
                    values = np.array(values, dtype=np.float32)
                    
                    feature_colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', 
                                    '#FF99CC', '#99FFCC', '#FFB366', '#99FF99'][:len(features)]

                    wedges2, texts2, autotexts2 = ax2.pie(
                        x=values,  # Use the converted numpy array
                        labels=features,
                        colors=feature_colors,
                        startangle=90,
                        textprops={'fontsize': 10},
                        autopct=lambda pct: f'{pct:.1f}%' if pct > 0 else ''
                    )

                ax2.set_title(
                    f"Feature Distribution\nTotal: {total} test cases",
                    color=text_color,
                    pad=20,
                    fontsize=14
                )

                # Adjust layout with more padding for better visibility
                fig.tight_layout(pad=3.0)

                # Create canvas with the correct background color
                canvas = FigureCanvasTkAgg(fig, master=inner_chart_frame)
                canvas.draw()
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.configure(bg=bg_color)  # Set canvas background
                canvas_widget.pack(fill="both", expand=True, padx=10, pady=10)

                # Add legend below charts
                legend_frame = ctk.CTkFrame(chart_frame, fg_color=("gray95", "gray13"))
                legend_frame.pack(fill="x", pady=(10, 0), padx=20)

                # Status legend (left side)
                status_legend = ctk.CTkFrame(legend_frame, fg_color="transparent")
                status_legend.pack(side="left", expand=True, pady=5)
                
                for label, color in zip(status_labels, status_colors):
                    item_frame = ctk.CTkFrame(status_legend, fg_color="transparent")
                    item_frame.pack(side="left", expand=True, pady=5)
                    
                    ctk.CTkLabel(
                        item_frame,
                        text="●",
                        text_color=color,
                        font=("Arial", 20)
                    ).pack(side="left")
                    
                    ctk.CTkLabel(
                        item_frame,
                        text=label,
                        font=("Arial", 12)
                    ).pack(side="left")

            finally:
                conn.close()

        except Exception as e:
            print(f"Error showing statistics: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", "Failed to show statistics dashboard")

    def generate_excel_report(self):
        """Generate Excel report with all test case details"""
        try:
            # Create directory if it doesn't exist
            report_dir = r"D:\ResultsTestCaseManagement"
            os.makedirs(report_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(report_dir, f"test_cases_report_{timestamp}.xlsx")
            
            # Get data from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    test_case_id, feature, description, test_steps,
                    expected_result, actual_result, status, environment,
                    browser, created_date, notes
                FROM test_cases
                ORDER BY feature, test_case_id
            ''')
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                messagebox.showinfo("Info", "No data available for report")
                return
                
            # Create DataFrame
            df = pd.DataFrame(data, columns=[
                'Test Case ID', 'Feature', 'Description', 'Test Steps',
                'Expected Result', 'Actual Result', 'Status', 'Environment',
                'Browser', 'Created Date', 'Notes'
            ])
            
            # Create Excel writer
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Test Cases', index=False)
                
                # Get the workbook and the worksheet
                workbook = writer.book
                worksheet = writer.sheets['Test Cases']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4F81BD',
                    'color': 'white',
                    'border': 1
                })
                
                # Format the header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # Adjust column widths
                for idx, col in enumerate(df.columns):
                    series = df[col]
                    max_len = max(
                        series.astype(str).map(len).max(),
                        len(str(series.name))
                    ) + 1
                    worksheet.set_column(idx, idx, min(max_len, 50))
                    
            messagebox.showinfo("Success", f"Excel report generated successfully: {filename}")
                
        except Exception as e:
            print(f"Error generating Excel report: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", "Failed to generate Excel report")

    def create_vertical_test_case_table(self, test_case_data):
        """Create a vertical test case detail table"""
        data = [
            ["Test Case ID:", test_case_data[0]],
            ["Feature:", test_case_data[1]],
            ["Description:", test_case_data[2]],
            ["Test Steps:", test_case_data[3]],
            ["Expected Result:", test_case_data[4]],
            ["Actual Result:", test_case_data[5]],
            ["Status:", test_case_data[6]],
            ["Environment:", test_case_data[7]],
            ["Browser:", test_case_data[8]],
            ["Date:", test_case_data[9]],
            ["Notes:", test_case_data[10]]
        ]
        
        table = Table(data, colWidths=[100, 400])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        return table

    def calculate_percentage(self, value, total):
        """Calculate percentage with safety check for zero division"""
        return (value/total * 100) if total > 0 else 0

    def show_statistics_dashboard(self):
        """Show comprehensive statistics dashboard with improved visualization"""
        try:
            # Create window
            stats_window = ctk.CTkToplevel(self)
            stats_window.title("Test Cases Statistics")
            stats_window.geometry("1000x800")
            
            # Get the current theme colors
            current_theme = self.cget("fg_color")
            bg_color = current_theme[1] if isinstance(current_theme, tuple) else current_theme
            
            # Configure window with theme color
            stats_window.configure(fg_color=bg_color)
            
            # Create TabView with theme-aware colors
            tab_view = ctk.CTkTabview(stats_window)
            tab_view.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Add tabs
            self.table_tab = tab_view.add("Table View")
            self.chart_tab = tab_view.add("Chart View")

            # Get data from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # First normalize all statuses in the database
                cursor.execute('''
                    UPDATE test_cases 
                    SET status = 
                        CASE 
                            WHEN LOWER(status) IN ('pass', 'passed', 'p') THEN 'Pass'
                            WHEN LOWER(status) IN ('fail', 'failed', 'f') THEN 'Fail'
                            ELSE 'Not Executed'
                        END
                ''')
                conn.commit()

                # Then get the counts with the normalized statuses
                cursor.execute('''
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM test_cases
                    GROUP BY status
                    ORDER BY 
                        CASE status
                            WHEN 'Pass' THEN 1
                            WHEN 'Fail' THEN 2
                            ELSE 3
                        END
                ''')
                status_counts = cursor.fetchall()

                # Initialize all possible status counts to 0
                status_dict = {'Pass': 0, 'Fail': 0, 'Not Executed': 0}
                
                # Update with actual counts
                for status, count in status_counts:
                    normalized_status = self.normalize_status(status)
                    status_dict[normalized_status] = count

                # Get values in fixed order
                passed = status_dict['Pass']
                failed = status_dict['Fail']
                not_executed = status_dict['Not Executed']
                total = sum(status_dict.values())

                # Debug print to verify counts
                print("Raw status counts from DB:", status_counts)
                print("Normalized status dict:", status_dict)
                print(f"Final counts - Pass: {passed}, Fail: {failed}, Not Executed: {not_executed}, Total: {total}")

                # Update feature query to use normalized status
                cursor.execute('''
                    SELECT 
                        feature,
                        SUM(CASE WHEN status = 'Pass' THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN status = 'Fail' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'Not Executed' THEN 1 ELSE 0 END) as not_executed
                    FROM test_cases 
                    GROUP BY feature
                ''')
                feature_stats = cursor.fetchall()

                # Debug print
                print(f"Total: {total}, Passed: {passed}, Failed: {failed}, Not Executed: {not_executed}")
                print(f"Feature stats: {feature_stats}")

                # TABLE VIEW
                table_frame = ctk.CTkFrame(self.table_tab)
                table_frame.pack(fill="both", expand=True, padx=10, pady=10)

                # Title
                title = ctk.CTkLabel(
                    table_frame,
                    text="Test Cases Statistics Summary",
                    font=("Arial", 20, "bold")
                )
                title.pack(pady=(0, 20))

                # Overall Statistics Section
                overall_frame = ctk.CTkFrame(table_frame)
                overall_frame.pack(fill="x", padx=10, pady=10)

                overall_title = ctk.CTkLabel(
                    overall_frame,
                    text="Overall Statistics",
                    font=("Arial", 16, "bold")
                )
                overall_title.pack(pady=10)

                # Create overall statistics table
                stats_data = [
                    ["Total Test Cases", total],
                    ["Passed", passed],
                    ["Failed", failed],
                    ["Not Executed", not_executed]
                ]

                # Overall Statistics Section - Table View
                for label, value in stats_data:
                    row_frame = ctk.CTkFrame(overall_frame)
                    row_frame.pack(fill="x", padx=5, pady=2)
                    
                    percentage = (value/total*100) if total > 0 else 0
                    
                    ctk.CTkLabel(row_frame, text=label, width=150).pack(side="left", padx=5)
                    ctk.CTkLabel(
                        row_frame, 
                        text=str(value), 
                        width=100,
                        fg_color=("green" if label == "Passed" else 
                                 "red" if label == "Failed" else 
                                 "gray" if label == "Not Executed" else "transparent"),
                        corner_radius=5
                    ).pack(side="left", padx=5)
                    ctk.CTkLabel(
                        row_frame,
                        text=f"{percentage:.1f}%",
                        width=100
                    ).pack(side="left", padx=5)

                # Feature Statistics Section
                feature_frame = ctk.CTkFrame(table_frame)
                feature_frame.pack(fill="x", padx=10, pady=(20, 10))

                feature_title = ctk.CTkLabel(
                    feature_frame,
                    text="Feature-wise Statistics",
                    font=("Arial", 16, "bold")
                )
                feature_title.pack(pady=10)

                # Headers for feature table
                header_frame = ctk.CTkFrame(feature_frame)
                header_frame.pack(fill="x", padx=5, pady=2)
                
                headers = ["Feature", "Passed", "Failed", "Not Executed", "Total"]
                for header in headers:
                    ctk.CTkLabel(
                        header_frame,
                        text=header,
                        font=("Arial", 12, "bold"),
                        width=120
                    ).pack(side="left", padx=5)

                # Feature data
                for feature, passed, failed, not_exec in feature_stats:
                    row_frame = ctk.CTkFrame(feature_frame)
                    row_frame.pack(fill="x", padx=5, pady=2)
                    
                    feature_total = (passed or 0) + (failed or 0) + (not_exec or 0)
                    
                    ctk.CTkLabel(row_frame, text=feature, width=120).pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(passed or 0), width=120, fg_color="green3").pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(failed or 0), width=120, fg_color="red3").pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(not_exec or 0), width=120, fg_color="gray").pack(side="left", padx=5)
                    ctk.CTkLabel(row_frame, text=str(feature_total), width=120).pack(side="left", padx=5)

                # CHART VIEW
                chart_frame = ctk.CTkFrame(self.chart_tab)
                chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

                # Title frame
                title_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
                title_frame.pack(fill="x", pady=(0, 20))
                
                ctk.CTkLabel(
                    title_frame,
                    text="Test Cases Distribution Dashboard",
                    font=("Arial", 20, "bold")
                ).pack(pady=10)

                # Main chart container with nested frames for visual depth
                outer_chart_frame = ctk.CTkFrame(chart_frame)
                outer_chart_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
                middle_chart_frame = ctk.CTkFrame(
                    outer_chart_frame,
                    fg_color=("gray90", "gray17")
                )
                middle_chart_frame.pack(fill="both", expand=True, padx=2, pady=2)
                
                inner_chart_frame = ctk.CTkFrame(
                    middle_chart_frame,
                    fg_color=("gray95", "gray13")
                )
                inner_chart_frame.pack(fill="both", expand=True, padx=2, pady=2)

                # Prepare data
                status_values = [passed, failed, not_executed]
                status_labels = [f'Pass ({passed})', f'Fail ({failed})', f'Not Executed ({not_executed})']
                status_colors = ['#2ECC71', '#E74C3C', '#95A5A6']
                
                # Create figure with two subplots side by side
                fig = plt.Figure(figsize=(15, 7))
                # Get theme colors
                is_dark_theme = self.cget("fg_color")[1] == "gray13"
                bg_color = '#2B2B2B' if is_dark_theme else '#F0F0F0'
                text_color = 'white' if is_dark_theme else 'black'

                # Set figure background color
                fig.patch.set_facecolor(bg_color)

                # Status Distribution Chart (Left) - Pie Chart
                ax1 = fig.add_subplot(121)
                ax1.set_facecolor(bg_color)
                
                if total > 0:
                    # Ensure data order matches labels
                    status_values = [passed, failed, not_executed]
                    status_labels = [f'Pass ({passed})', f'Fail ({failed})', f'Not Executed ({not_executed})']
                    
                    # Create pie chart with ordered data
                    wedges1, texts1, autotexts1 = ax1.pie(
                        x=status_values,  # Use ordered values instead of status_counts
                        labels=status_labels,
                        colors=['#2ECC71', '#E74C3C', '#95A5A6'],
                        startangle=90,
                        autopct='%1.1f%%'
                    )
                    
                    # Set text colors
                    plt.setp(texts1, color=text_color)
                    plt.setp(autotexts1, color=text_color)

                ax1.set_title(
                    f"Test Status Distribution\nTotal: {total} test cases",
                    color=text_color,
                    pad=20,
                    fontsize=14
                )

                # Feature Distribution Chart (Right)
                ax2 = fig.add_subplot(122)
                ax2.set_facecolor(bg_color)

                if feature_stats:
                    feature_totals = [(stat[0], sum(stat[1:4])) for stat in feature_stats]
                    features = []
                    values = []
                    
                    # Calculate exact percentages for features
                    for feature, feature_total in feature_totals:
                        feature_pct = self.calculate_percentage(feature_total, total)
                        features.append(f'{feature}: {feature_total} ({feature_pct:.1f}%)')
                        values.append(float(feature_total))  # Convert to float explicitly
                    
                    # Convert to numpy array
                    values = np.array(values, dtype=np.float32)
                    
                    feature_colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', 
                                    '#FF99CC', '#99FFCC', '#FFB366', '#99FF99'][:len(features)]

                    wedges2, texts2, autotexts2 = ax2.pie(
                        x=values,  # Use the converted numpy array
                        labels=features,
                        colors=feature_colors,
                        startangle=90,
                        textprops={'fontsize': 10},
                        autopct=lambda pct: f'{pct:.1f}%' if pct > 0 else ''
                    )

                ax2.set_title(
                    f"Feature Distribution\nTotal: {total} test cases",
                    color=text_color,
                    pad=20,
                    fontsize=14
                )

                # Adjust layout with more padding for better visibility
                fig.tight_layout(pad=3.0)

                # Create canvas with the correct background color
                canvas = FigureCanvasTkAgg(fig, master=inner_chart_frame)
                canvas.draw()
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.configure(bg=bg_color)  # Set canvas background
                canvas_widget.pack(fill="both", expand=True, padx=10, pady=10)

                # Add legend below charts
                legend_frame = ctk.CTkFrame(chart_frame, fg_color=("gray95", "gray13"))
                legend_frame.pack(fill="x", pady=(10, 0), padx=20)

                # Status legend (left side)
                status_legend = ctk.CTkFrame(legend_frame, fg_color="transparent")
                status_legend.pack(side="left", expand=True, pady=5)
                
                for label, color in zip(status_labels, status_colors):
                    item_frame = ctk.CTkFrame(status_legend, fg_color="transparent")
                    item_frame.pack(side="left", expand=True, pady=5)
                    
                    ctk.CTkLabel(
                        item_frame,
                        text="●",
                        text_color=color,
                        font=("Arial", 20)
                    ).pack(side="left")
                    
                    ctk.CTkLabel(
                        item_frame,
                        text=label,
                        font=("Arial", 12)
                    ).pack(side="left")

            finally:
                conn.close()

        except Exception as e:
            print(f"Error showing statistics: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", "Failed to show statistics dashboard")

    def generate_excel_report(self):
        """Generate Excel report with all test case details"""
        try:
            # Create directory if it doesn't exist
            report_dir = r"D:\ResultsTestCaseManagement"
            os.makedirs(report_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(report_dir, f"test_cases_report_{timestamp}.xlsx")
            
            # Get data from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    test_case_id, feature, description, test_steps,
                    expected_result, actual_result, status, environment,
                    browser, created_date, notes
                FROM test_cases
                ORDER BY feature, test_case_id
            ''')
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                messagebox.showinfo("Info", "No data available for report")
                return
                
            # Create DataFrame
            df = pd.DataFrame(data, columns=[
                'Test Case ID', 'Feature', 'Description', 'Test Steps',
                'Expected Result', 'Actual Result', 'Status', 'Environment',
                'Browser', 'Created Date', 'Notes'
            ])
            
            # Create Excel writer
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Test Cases', index=False)
                
                # Get the workbook and the worksheet
                workbook = writer.book
                worksheet = writer.sheets['Test Cases']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4F81BD',
                    'color': 'white',
                    'border': 1
                })
                
                # Format the header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # Adjust column widths
                for idx, col in enumerate(df.columns):
                    series = df[col]
                    max_len = max(
                        series.astype(str).map(len).max(),
                        len(str(series.name))
                    ) + 1
                    worksheet.set_column(idx, idx, min(max_len, 50))
                    
            messagebox.showinfo("Success", f"Excel report generated successfully: {filename}")
                
        except Exception as e:
            print(f"Error generating Excel report: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", "Failed to generate Excel report")

    def create_vertical_test_case_table(self, test_case_data):
        """Create a vertical test case detail table"""
        data = [
            ["Test Case ID:", test_case_data[0]],
            ["Feature:", test_case_data[1]],
            ["Description:", test_case_data[2]],
            ["Test Steps:", test_case_data[3]],
            ["Expected Result:", test_case_data[4]],
            ["Actual Result:", test_case_data[5]],
            ["Status:", test_case_data[6]],
            ["Environment:", test_case_data[7]],
            ["Browser:", test_case_data[8]],
            ["Date:", test_case_data[9]],
            ["Notes:", test_case_data[10]]
        ]
        
        table = Table(data, colWidths=[100, 400])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        return table

    def calculate_percentage(self, value, total):
        """Calculate percentage with safety check for zero division"""
        return (value/total * 100) if total > 0 else 0