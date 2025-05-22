import customtkinter as ctk
from datetime import datetime
import json
import sqlite3
from typing import Dict, Any
from tkinter import messagebox
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from collections import Counter
from config.app_config import AppConfig

class JobApplicationEntry(ctk.CTkFrame):
    def __init__(self, master, job_data: Dict[str, Any], on_update_status=None, on_delete=None):
        super().__init__(master)
        self.config = AppConfig()
        self.job_data = job_data
        self.on_update_status = on_update_status
        self.on_delete = on_delete
        self.setup_ui()

    def setup_ui(self):
        # Fix grid configuration to handle all columns with equal weight
        self.grid_columnconfigure(tuple(range(10)), weight=1)
        
        # Get settings from config
        required_height = self.config.UI_SETTINGS["row_height"]
        theme_fg = "transparent"
        text_color = self._apply_appearance_mode(
            (self.config.COLORS["Light"]["text"], 
             self.config.COLORS["Dark"]["text"])
        )
        
        # Simple label parameters
        label_params = {
            'height': required_height,
            'text_color': text_color,
            'justify': 'center',
            'anchor': 'center',
            'font': self.config.FONT_STYLES["normal"]
        }

        # Define columns with exact same widths as headers
        columns = [
            (self.job_data['number'], 60),
            (self.job_data['company'], 150),
            (self.job_data['position'], 150),
            (self.job_data.get('location', '-'), 100),
            (self.job_data['salary'], 100),
            (datetime.strptime(self.job_data['apply_date'], "%Y-%m-%d").strftime("%d %b %Y"), 100),
            ("View" if self.job_data.get('job_link') else "-", 80),
            (self.job_data['current_stage'], 120),
            (self.job_data['current_status'], 100),
            (self.truncate_text(self.job_data['note'], self.config.UI_SETTINGS["note_max_length"]), 300)  # Truncate notes to 50 characters
        ]

        # Create labels with proper alignment and tooltips
        for col, (value, width) in enumerate(columns):
            if col == 6:  # Job link column - make it a button if URL exists
                if self.job_data.get('job_link'):
                    label = ctk.CTkButton(
                        self,
                        text=value,
                        width=width,
                        height=required_height-4,
                        command=lambda url=self.job_data['job_link']: self.open_job_link(url)
                    )
                else:
                    label = ctk.CTkLabel(
                        self,
                        text=value,
                        width=width,
                        fg_color=theme_fg,
                        **label_params
                    )
            elif col == 8:  # Status column with color
                label = ctk.CTkLabel(
                    self,
                    text=value,
                    width=width,
                    fg_color=self.get_status_color(value),
                    **label_params
                )
            elif col == 9:  # Notes column
                note_text = str(value)  # Convert to string
                label = ctk.CTkLabel(
                    self,
                    text=note_text,
                    width=width,
                    fg_color=theme_fg,
                    **label_params
                )
            else:
                label = ctk.CTkLabel(
                    self,
                    text=str(value),
                    width=width,
                    fg_color=theme_fg,
                    **label_params
                )
            label.grid(row=0, column=col, padx=1, pady=1, sticky="ew")
            
            # Configure column width
            self.grid_columnconfigure(col, minsize=width, weight=0)

        # Actions frame at the last column
        action_frame = ctk.CTkFrame(self, fg_color="transparent", width=150)
        action_frame.grid(row=0, column=10, padx=1, pady=1, sticky="ew")  # Changed from column 9 to 10
        self.grid_columnconfigure(10, minsize=150, weight=0)  # Changed from 9 to 10
        
        # Buttons in action frame
        ctk.CTkButton(
            action_frame,
            text="Update",
            command=self.on_update_status,
            width=70,
            height=required_height-4
        ).pack(side="left", padx=1)
        
        ctk.CTkButton(
            action_frame,
            text="Delete",
            command=self.on_delete,
            fg_color="red",
            hover_color="darkred",
            width=70,
            height=required_height-4
        ).pack(side="left", padx=1)

    def get_status_color(self, status):
        return self.config.STATUS_COLORS.get(status, ("gray85", "gray25"))

    def open_job_link(self, url):
        if url:
            import webbrowser
            webbrowser.open(url)

    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max_length and add ellipsis if needed"""
        text = str(text)
        return text[:max_length] + "..." if len(text) > max_length else text

class HomeView(ctk.CTkFrame):
    COLUMN_WIDTHS = {
        "number": 60,
        "company": 150,
        "position": 150,
        "location": 100,
        "salary": 100,
        "apply_date": 100,
        "job_link": 80,  # Add job link width
        "current_stage": 120,
        "status": 100,
        "notes": 300,
        "actions": 150
    }
    def __init__(self, master=None, app_controller=None):
        super().__init__(master)
        self.app_controller = app_controller
        self.charts_visible = False
        self.data_canvas = None  # Rename from self.canvas
        self.chart_canvas = None  # New variable for chart canvas
        self.figures = []
        self.page_size = 10  # Number of items per page
        self.current_page = 1
        self.setup_database()
        self.setup_ui()
        self.load_applications()
        self.pack(fill="both", expand=True)
        self._appearance_mode_callback = self.update_canvas_colors
        ctk.AppearanceModeTracker.add(self._appearance_mode_callback)

    def setup_database(self):
        self.conn = sqlite3.connect('db_jobapplications.db')
        self.cursor = self.conn.cursor()

        # Check if table exists
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_applications'")
        table_exists = self.cursor.fetchone()
        
        if not table_exists:
            # Create table if it doesn't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY,
                    company TEXT,
                    position TEXT,
                    location TEXT,
                    salary TEXT,
                    apply_date TEXT,
                    job_link TEXT,
                    current_stage TEXT,
                    stage_status TEXT,
                    notes TEXT,
                    last_update TEXT
                )
            ''')
            self.conn.commit()
            
            # Add test data only if table is empty
            self.cursor.execute('SELECT COUNT(*) FROM job_applications')
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute('''
                    INSERT INTO job_applications 
                    (company, position, apply_date, current_stage, stage_status, notes, last_update) 
                    VALUES 
                    ('Test Company', 'Test Position', ?, 'CV', 'Sent', 'Test Note', ?)
                ''', (datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                self.conn.commit()
        else:
            # Check if last_update column exists
            self.cursor.execute("PRAGMA table_info(job_applications)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            if 'last_update' not in columns:
                # Add last_update column if it doesn't exist
                self.cursor.execute('ALTER TABLE job_applications ADD COLUMN last_update TEXT')
                self.conn.commit()

    def setup_ui(self):
        # Configure main frame grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Give weight only to data container

        # 1. Matrix Frame (Top)
        matrix_frame = ctk.CTkFrame(self)
        matrix_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        matrix_frame.grid_columnconfigure(0, weight=1)
        
        # Title and metrics
        title_label = ctk.CTkLabel(matrix_frame, text="Job Application Tracking System", font=("Arial Bold", 20))
        title_label.pack(pady=10)
        self.metrics_frame = self.create_metrics_frame(matrix_frame)
        self.metrics_frame.pack(fill="x", padx=5, pady=5)

        # 2. Button Frame
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        button_frame.grid_columnconfigure(1, weight=1)  # Center space gets weight
        
        # Left buttons
        left_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_buttons.grid(row=0, column=0, sticky="w", padx=5)
        ctk.CTkButton(left_buttons, text="Add New Application", command=self.show_add_dialog).pack(side="left", padx=2)
        ctk.CTkButton(left_buttons, text="Export to CSV", command=self.export_to_csv).pack(side="left", padx=2)
        
        # Right buttons
        right_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_buttons.grid(row=0, column=2, sticky="e", padx=5)
        self.delete_all_button = ctk.CTkButton(right_buttons, text="Delete All", 
                                              command=self.delete_all_applications, 
                                              fg_color="red", hover_color="darkred")
        self.delete_all_button.pack(side="left", padx=2)
        self.show_stats_button = ctk.CTkButton(right_buttons, text="Show Statistics", 
                                              command=self.show_statistics_dialog)
        self.show_stats_button.pack(side="left", padx=2)

        # 3. Data Frame with dual scrollbars
        data_container = ctk.CTkFrame(self)
        data_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        data_container.grid_columnconfigure(0, weight=1)
        data_container.grid_rowconfigure(0, weight=1)

        # Create a canvas with themed background
        theme_color = self._apply_appearance_mode(self._fg_color)
        canvas_bg = self._apply_appearance_mode(("gray95", "gray20"))  # Lighter dark theme
        
        self.data_canvas = ctk.CTkCanvas(
            data_container, 
            highlightthickness=0, 
            bd=0,
            bg=canvas_bg  # Use theme-aware background
        )
        self.data_canvas.grid(row=0, column=0, sticky="nsew")

        # Add vertical scrollbar first
        v_scrollbar = ctk.CTkScrollbar(
            data_container,
            orientation="vertical",
            command=self.data_canvas.yview  # Updated
        )
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Add horizontal scrollbar
        h_scrollbar = ctk.CTkScrollbar(
            data_container, 
            orientation="horizontal",
            command=self.data_canvas.xview  # Updated
        )
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure scrollbars
        self.data_canvas.configure(  # Updated
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set
        )

        # Main container frame
        self.scrollable_frame = ctk.CTkFrame(self.data_canvas, fg_color=theme_color)  # Updated
        self.canvas_frame = self.data_canvas.create_window(  # Updated
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        # Calculate initial width
        total_width = sum(self.COLUMN_WIDTHS.values())
        self.scrollable_frame.configure(width=total_width + 20)

        # Content frames with proper theme colors
        header_frame = ctk.CTkFrame(
            self.scrollable_frame, 
            fg_color="transparent"
        )
        header_frame.pack(fill="x", pady=0, padx=0)
        
        # Configure header columns with exact same widths
        for col, (text, width) in enumerate(self.COLUMN_WIDTHS.items()):
            header_frame.grid_columnconfigure(col, minsize=width, weight=0)
            label_text = text.replace('_', ' ').title()
            header_label = ctk.CTkLabel(
                header_frame,
                text=label_text,
                width=width,
                height=25,
                fg_color="transparent",
                text_color=self._apply_appearance_mode(("black", "white")),
                corner_radius=0,
                anchor="center",  # Center align header text
                font=("Arial", 12, "bold")  # Make headers bold
            )
            header_label.grid(row=0, column=col, padx=1, sticky="ew")
            if not hasattr(self, '_header_labels'):
                self._header_labels = []
            self._header_labels.append(header_label)

        # Add separator line
        separator = ctk.CTkFrame(self.scrollable_frame, height=2, fg_color="gray50")
        separator.pack(fill="x", pady=(2, 2))

        # Entries container with transparent background
        self.entries_container = ctk.CTkFrame(
            self.scrollable_frame,
            fg_color="transparent"  # Make entries container transparent
        )
        self.entries_container.pack(fill="both", expand=True)

        # Update scroll bindings
        def update_scrollregion(event=None):
            self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all"))
            # Update the window size to fit content
            width = max(self.scrollable_frame.winfo_reqwidth(), data_container.winfo_width())
            height = self.scrollable_frame.winfo_reqheight()
            self.data_canvas.itemconfig(self.canvas_frame, width=width, height=height)

        self.scrollable_frame.bind("<Configure>", update_scrollregion)
        self.data_canvas.bind("<Configure>", self.on_canvas_configure)

        # Add mousewheel scrolling
        def _on_mousewheel(event):
            self.data_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.data_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Pagination Frame (row 3) - fix grid and ensure it's visible
        pagination_frame = ctk.CTkFrame(self)
        pagination_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        pagination_frame.grid_columnconfigure(0, weight=1)
        pagination_frame.grid_propagate(True)  # Allow frame to resize
        
        # Center pagination controls
        controls = ctk.CTkFrame(pagination_frame, fg_color="transparent")
        controls.pack(expand=True)
        
        # Page size selector
        page_size_frame = ctk.CTkFrame(controls, fg_color="transparent")
        page_size_frame.pack(side="left", padx=20)
        ctk.CTkLabel(page_size_frame, text="Items per page:").pack(side="left", padx=5)
        
        self.page_size_var = ctk.StringVar(value="10")
        size_menu = ctk.CTkOptionMenu(
            page_size_frame,
            values=["5", "10", "20", "50", "100"],
            variable=self.page_size_var,
            width=70,
            command=self.change_page_size
        )
        size_menu.pack(side="left", padx=5)
        
        # Navigation buttons
        self.prev_btn = ctk.CTkButton(controls, text="Previous", width=100, command=self.prev_page)
        self.prev_btn.pack(side="left", padx=5)
        
        self.page_label = ctk.CTkLabel(controls, text="Page 1", width=100)
        self.page_label.pack(side="left", padx=20)
        
        self.next_btn = ctk.CTkButton(controls, text="Next", width=100, command=self.next_page)
        self.next_btn.pack(side="left", padx=5)

        # Ensure proper frame update
        self.update_idletasks()

    def create_metrics_frame(self, parent):
        frame = ctk.CTkFrame(parent)
        
        metrics = [
            {"title": "Total Applications", "value": "0", "tooltip": "Total number of job applications"},
            {"title": "Active Process", "value": "0", "tooltip": "Applications in progress"},
            {"title": "Interviews Scheduled", "value": "0", "tooltip": "Upcoming interviews"},
            {"title": "Offers Pending", "value": "0", "tooltip": "Pending job offers"},
            {"title": "Rejected", "value": "0", "tooltip": "Rejected applications"}
        ]
        
        self.metric_labels = {}
        
        for i, metric in enumerate(metrics):
            box = ctk.CTkFrame(frame)
            box.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            frame.grid_columnconfigure(i, weight=1)
            
            ctk.CTkLabel(box, text=metric["title"], font=("Arial Bold", 12)).pack(pady=(5,0))
            
            value_label = ctk.CTkLabel(box, text=metric["value"], font=("Arial Bold", 16))
            value_label.pack(pady=(0,8))  # Adjust the height between each data here
            
            self.metric_labels[metric["title"]] = value_label
        
        return frame

    def update_metrics(self):
        try:
            self.cursor.execute('SELECT COUNT(*) FROM job_applications')
            total = self.cursor.fetchone()[0]
            self.metric_labels["Total Applications"].configure(text=str(total))
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM job_applications 
                WHERE stage_status NOT IN ('Rejected', 'Completed', 'Withdrawn')
            ''')
            active = self.cursor.fetchone()[0]
            self.metric_labels["Active Process"].configure(text=str(active))
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM job_applications 
                WHERE stage_status = 'Scheduled' 
                AND current_stage LIKE '%Interview%'
            ''')
            interviews = self.cursor.fetchone()[0]
            self.metric_labels["Interviews Scheduled"].configure(text=str(interviews))
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM job_applications 
                WHERE current_stage = 'Offer' 
                AND stage_status = 'Pending'
            ''')
            offers = self.cursor.fetchone()[0]
            self.metric_labels["Offers Pending"].configure(text=str(offers))
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM job_applications 
                WHERE stage_status = 'Rejected'
            ''')
            rejected = self.cursor.fetchone()[0]
            self.metric_labels["Rejected"].configure(text=str(rejected))
            
        except sqlite3.Error as e:
            print(f"Error updating metrics: {e}")

    def export_to_csv(self):
        try:
            from tkinter import filedialog
            import csv
            from datetime import datetime

            filename = filedialog.asksaveasfilename(
                defaultextension='.csv',
                filetypes=[("CSV files", '*.csv')],
                initialfile=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv"
            )
            
            if not filename:
                return

            self.cursor.execute('''
                SELECT company, position, location, salary, apply_date, 
                       job_link, stage_status, notes
                FROM job_applications
                ORDER BY apply_date DESC
            ''')
            
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Company', 'Position', 'Location', 'Salary', 
                               'Apply Date', 'Job Link', 'Status', 'Notes'])
                writer.writerows(self.cursor.fetchall())

            messagebox.showinfo("Success", "Data exported successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {str(e)}")

    def show_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Job Application")
        dialog.geometry("300x550")
        dialog.grab_set()

        main_container = ctk.CTkFrame(dialog)
        main_container.pack(fill="both", expand=True, padx=15, pady=10)

        company_frame = self.create_labeled_frame(main_container, "Company Information")
        
        self.company_entry = ctk.CTkEntry(company_frame, placeholder_text="Company Name")
        self.company_entry.pack(fill="x", padx=5, pady=5)
        
        self.position_var = ctk.StringVar()
        self.position_menu = ctk.CTkOptionMenu(company_frame, values=["Quality Engineer", "Software Engineer", "Data Scientist", "Product Manager", "Designer", "Other"], variable=self.position_var)
        self.position_menu.pack(fill="x", padx=5, pady=5)
        
        self.location_var = ctk.StringVar()
        self.location_menu = ctk.CTkOptionMenu(company_frame, values=["Indonesia", "Malaysia", "Singapore", "Australia", "Europe", "Asia", "Remote", "Other"], variable=self.location_var)
        self.location_menu.pack(fill="x", padx=5, pady=5)
        
        self.salary_var = ctk.StringVar()
        self.salary_menu = ctk.CTkOptionMenu(company_frame, values=["$50k-$70k", "$70k-$90k", "$90k-$110k", "$110k+", "unknow"], variable=self.salary_var)
        self.salary_menu.pack(fill="x", padx=5, pady=5)

        job_link_frame = ctk.CTkFrame(company_frame)
        job_link_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(job_link_frame, text="Job Link:").pack(side="left", padx=5)
        self.job_link_entry = ctk.CTkEntry(job_link_frame, placeholder_text="https://...")
        self.job_link_entry.pack(side="left", expand=True, fill="x", padx=5)

        date_frame = ctk.CTkFrame(main_container)
        date_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(date_frame, text="Application Date:").pack(side="left", padx=5)
        
        current_date = datetime.now()
        self.date_picker = DateEntry(date_frame, width=12, background='darkblue', foreground='white', borderwidth=2, year=current_date.year, month=current_date.month, day=current_date.day, date_pattern='y-mm-dd', locale='en_US')
        self.date_picker.pack(side="left", padx=5)

        # Make the note section bigger and more prominent
        note_frame = self.create_labeled_frame(main_container, "Notes (Required)")
        self.note_entry = ctk.CTkTextbox(note_frame, height=120)  # Double the height
        self.note_entry.pack(fill="x", padx=5, pady=5)
        self.note_entry.insert("1.0", "Enter your notes here...")  # Add placeholder text

        bottom_container = ctk.CTkFrame(main_container)
        bottom_container.pack(fill="x", padx=5, pady=(0, 10))

        save_button = ctk.CTkButton(bottom_container, text="Save Application", command=lambda: self.save_new_application(dialog))
        save_button.pack(fill="x", padx=5, pady=10)

        cancel_button = ctk.CTkButton(bottom_container, text="Cancel", command=dialog.destroy)
        cancel_button.pack(fill="x", padx=5, pady=(0, 10))

    def create_labeled_frame(self, parent, text):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=10)
        ctk.CTkLabel(frame, text=text, font=("Arial Bold", 12)).pack(anchor="w", padx=5, pady=5)
        return frame

    def load_applications(self):
        try:
            self.update_metrics()
            
            # Clear existing entries
            for widget in self.entries_container.winfo_children():
                widget.destroy()

            # Calculate pagination
            offset = (self.current_page - 1) * self.page_size
            
            # Get total records count
            self.cursor.execute('SELECT COUNT(*) FROM job_applications')
            total_records = self.cursor.fetchone()[0]
            
            # Fetch page data with all fields including notes
            self.cursor.execute('''
                SELECT id, company, position, location, salary, apply_date, 
                       job_link, current_stage, stage_status, notes
                FROM job_applications 
                ORDER BY apply_date DESC, id DESC
                LIMIT ? OFFSET ?
            ''', (self.page_size, offset))
            
            applications = self.cursor.fetchall()

            if not applications:
                no_data_label = ctk.CTkLabel(
                    self.entries_container,
                    text="No applications found",
                    font=("Arial Bold", 14)
                )
                no_data_label.pack(pady=20)
                return

            # Create entries with proper notes display
            for i, app in enumerate(applications, offset + 1):
                # Ensure note is not None or empty
                note_text = app[9] if app[9] and app[9].strip() else "No notes"
                
                job_data = {
                    "id": app[0],
                    "number": f"#{i}",
                    "company": app[1] if app[1] else "Unknown Company",
                    "position": app[2] if app[2] else "Unknown Position",
                    "location": app[3] if app[3] else "Not specified",
                    "salary": app[4] if app[4] else "Not specified",
                    "apply_date": app[5] if app[5] else datetime.now().strftime("%Y-%m-%d"),
                    "job_link": app[6],
                    "current_stage": app[7] if app[7] else "CV",
                    "current_status": app[8] if app[8] else "Sent",
                    "note": note_text
                }

                entry = JobApplicationEntry(
                    self.entries_container, 
                    job_data,
                    on_update_status=lambda id=app[0]: self.update_application_status(id),
                    on_delete=lambda id=app[0]: self.delete_application(id)
                )
                entry.pack(fill="x", pady=0, padx=0)
                
                # Add thinner separator line between entries
                separator = ctk.CTkFrame(self.entries_container, height=1, fg_color="gray30")
                separator.pack(fill="x", pady=0)

            # Update scroll region and canvas size
            self.entries_container.update_idletasks()
            total_width = sum(self.COLUMN_WIDTHS.values())
            self.scrollable_frame.configure(width=total_width + 20, height=self.entries_container.winfo_reqheight() + 50)
            self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all"))
            
            # Force update of scroll region
            def ensure_scroll_region():
                self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all"))
                self.entries_container.update_idletasks()
            
            self.after(100, ensure_scroll_region)  # Schedule update after initial render

            # Update pagination controls
            total_pages = max(1, (total_records + self.page_size - 1) // self.page_size)
            self.page_label.configure(text=f"Page {self.current_page} of {total_pages}")
            self.prev_btn.configure(state="normal" if self.current_page > 1 else "disabled")
            self.next_btn.configure(state="normal" if self.current_page < total_pages else "disabled")

        except Exception as e:
            print(f"Error loading applications: {str(e)}")
            messagebox.showerror("Error", f"Failed to load applications: {str(e)}")

    def delete_application(self, app_id):
        if messagebox.askyesno("Delete Application", "Are you sure you want to delete this application?"):
            try:
                self.cursor.execute('DELETE FROM job_applications WHERE id = ?', (app_id,))
                self.conn.commit()
                self.load_applications()
                messagebox.showinfo("Success", "Application deleted successfully!")
                if self.charts_visible:
                    self.update_pie_charts()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to delete application: {str(e)}")

    def update_status_options(self, selected_stage):
        if hasattr(self, 'status_menu'):
            statuses = list(JobApplicationEntry.STAGES[selected_stage].keys())
            self.status_menu.configure(values=statuses)
            self.status_var.set(statuses[0])

    def update_application_status(self, app_id):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update App Status")
        dialog.geometry("300x400")  # Increased height for note field

        self.cursor.execute('SELECT current_stage, stage_status, notes FROM job_applications WHERE id = ?', (app_id,))
        app = self.cursor.fetchone()

        stage_frame = self.create_labeled_frame(dialog, "Current Stage")
        
        self.stage_var = ctk.StringVar(value=app[0])
        stage_menu = ctk.CTkOptionMenu(stage_frame, values=list(JobApplicationEntry.STAGES.keys()), variable=self.stage_var, command=self.update_status_options)
        stage_menu.pack(fill="x", padx=5, pady=5)
        
        self.status_var = ctk.StringVar(value=app[1])
        self.status_menu = ctk.CTkOptionMenu(stage_frame, values=list(JobApplicationEntry.STAGES[app[0]].keys()), variable=self.status_var)
        self.status_menu.pack(fill="x", padx=5, pady=5)

        # Make the note section bigger and more prominent
        note_frame = self.create_labeled_frame(dialog, "Notes (Required)")
        self.note_entry = ctk.CTkTextbox(note_frame, height=120)  # Double the height
        self.note_entry.pack(fill="x", padx=5, pady=5)
        
        # Set existing note or placeholder
        if app[2]:
            self.note_entry.insert("1.0", app[2])
        else:
            self.note_entry.insert("1.0", "Enter your notes here...")

        save_button = ctk.CTkButton(dialog, text="Save Changes", command=lambda: self.save_status_update(app_id, dialog))
        save_button.pack(fill="x", padx=5, pady=5)

    def save_status_update(self, app_id, dialog):
        try:
            # Get and validate note
            note = self.note_entry.get("1.0", "end-1c").strip()
            if not note:
                if not messagebox.askyesno("Warning", "No notes added. Do you want to continue without notes?"):
                    return
                note = "No notes"

            self.cursor.execute('''
                UPDATE job_applications 
                SET current_stage=?, 
                    stage_status=?, 
                    notes=?,
                    last_update=?
                WHERE id=?
            ''', (
                self.stage_var.get(),
                self.status_var.get(),
                note,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                app_id
            ))
            self.conn.commit()
            
            self.load_applications()
            dialog.destroy()
            messagebox.showinfo("Success", "Status updated successfully!")
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update status: {str(e)}")

    def save_new_application(self, dialog):
        try:
            if not self.company_entry.get():
                messagebox.showerror("Error", "Company name is required!")
                return
                
            if not self.position_var.get():
                messagebox.showerror("Error", "Position is required!")
                return

            try:
                apply_date = self.date_picker.get_date().strftime("%Y-%m-%d")
            except Exception as e:
                messagebox.showerror("Error", "Invalid application date. Please select a valid date.")
                return

            # Get and validate note
            note = self.note_entry.get("1.0", "end-1c").strip()
            if not note:
                if not messagebox.askyesno("Warning", "No notes added. Do you want to continue without notes?"):
                    return
                note = "No notes"

            # Make sure to get the salary value
            salary = self.salary_var.get() if hasattr(self, 'salary_var') else ""

            data = (
                self.company_entry.get().strip(),
                self.position_var.get().strip(),
                self.location_var.get(),
                salary,
                apply_date,
                self.job_link_entry.get().strip(),
                "CV",  # Default stage
                "Sent",  # Default status
                note  # Use validated note
            )
            
            self.cursor.execute('''
                INSERT INTO job_applications (
                    company, position, location, salary, apply_date, job_link,
                    current_stage, stage_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
            self.conn.commit()
            self.load_applications()
            dialog.destroy()
            messagebox.showinfo("Success", "Application saved successfully!")
            if self.charts_visible:
                self.update_pie_charts()
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save to database: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save application: {str(e)}")

    def create_pie_charts(self, parent_frame):
        try:
            if self.chart_canvas:  # Updated from self.canvas
                self.chart_canvas.get_tk_widget().destroy()
                self.figures.clear()

            fig = plt.Figure(figsize=(15, 3), dpi=100)
            
            bg_color = '#333333' if ctk.get_appearance_mode() == 'Dark' else '#FFFFFF'
            fig.patch.set_facecolor(bg_color)
            
            ax1 = fig.add_subplot(131)
            ax2 = fig.add_subplot(132)
            ax3 = fig.add_subplot(133)
            
            for ax in [ax1, ax2, ax3]:
                ax.set_facecolor(bg_color)
                text_color = 'white' if ctk.get_appearance_mode() == 'Dark' else 'black'
                ax.tick_params(colors=text_color)
                for text in ax.texts:
                    text.set_color(text_color)
            
            self.chart_axes = [ax1, ax2, ax3]
            
            self.chart_canvas = FigureCanvasTkAgg(fig, parent_frame)  # Updated
            self.chart_canvas.draw()
            self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
            
            self.figures.append(fig)
            
            self.update_pie_charts()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create charts: {str(e)}")

    def plot_pie(self, ax, data, title):
        if not data:
            return

        try:
            ax.clear()

            labels = list(data.keys())
            values = list(data.values())
            
            text_color = 'white' if ctk.get_appearance_mode() == 'Dark' else 'black'
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(values)))
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            
            plt.setp(texts, color=text_color)
            plt.setp(autotexts, color=text_color)
            
            ax.set_title(title, color=text_color)
            
        except Exception as e:
            print(f"Error plotting pie chart: {e}")

    def update_pie_charts(self):
        try:
            self.cursor.execute('''
                SELECT current_stage, stage_status, apply_date 
                FROM job_applications
            ''')
            applications = self.cursor.fetchall()

            if not applications:
                return

            stages = Counter(app[0] for app in applications if app[0])
            statuses = Counter(app[1] for app in applications if app[1])
            months = Counter(datetime.strptime(app[2], "%Y-%m-%d").strftime("%B") for app in applications if app[2])

            stages = {f"{k} ({v})": v for k, v in stages.items()}
            statuses = {f"{k} ({v})": v for k, v in statuses.items()}
            months = {f"{k} ({v})": v for k, v in months.items()}

            self.plot_pie(self.chart_axes[0], stages, "Applications by Stage")
            self.plot_pie(self.chart_axes[1], statuses, "Applications by Status")
            self.plot_pie(self.chart_axes[2], months, "Applications by Month")

            self.chart_canvas.draw()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update charts: {str(e)}")

    def show_statistics_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Application Statistics Dashboard")
        dialog.geometry("1000x800")
        dialog.grab_set()

        title_frame = ctk.CTkFrame(dialog)
        title_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(title_frame, text="Job Application Statistics Overview", font=("Arial Bold", 24)).pack(pady=10)
        
        ctk.CTkLabel(title_frame, text="Comprehensive view of your job application progress and status distribution", font=("Arial", 12)).pack(pady=(0, 10))

        summary_frame = ctk.CTkFrame(dialog)
        summary_frame.pack(fill="x", padx=10, pady=5)
        
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN stage_status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN current_stage LIKE '%Interview%' THEN 1 ELSE 0 END) as interviews,
                SUM(CASE WHEN current_stage = 'Offer' THEN 1 ELSE 0 END) as offers
            FROM job_applications
        ''')
        stats = self.cursor.fetchone()
        
        summary_text = (
            f"Total Applications: {stats[0] or 0}\n"
            f"Success Rate: {100 - (stats[1] or 0)/(stats[0] or 1)*100:.1f}%\n"
            f"Interview Rate: {(stats[2] or 0)/(stats[0] or 1)*100:.1f}%\n"
            f"Offer Rate: {(stats[3] or 0)/(stats[0] or 1)*100:.1f}%"
        )
        ctk.CTkLabel(summary_frame, text=summary_text, font=("Arial", 12), justify="left").pack(pady=10, padx=10, anchor="w")

        charts_frame = ctk.CTkFrame(dialog)
        charts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_pie_charts(charts_frame)

        desc_frame = ctk.CTkFrame(dialog)
        desc_frame.pack(fill="x", padx=10, pady=5)
        
        descriptions = [
            ("Applications by Stage", "Distribution of applications across different recruitment stages"),
            ("Status Distribution", "Current status breakdown of all applications"),
            ("Monthly Activity", "Application submission trend by month")
        ]
        
        for title, desc in descriptions:
            section = ctk.CTkFrame(desc_frame)
            section.pack(side="left", expand=True, fill="x", padx=5)
            
            ctk.CTkLabel(section, text=title, font=("Arial Bold", 12)).pack(anchor="w", pady=(5,0))
            
            ctk.CTkLabel(section, text=desc, font=("Arial", 10), wraplength=250).pack(anchor="w", pady=(0,5))

    def delete_all_applications(self):
        if messagebox.askyesno("Delete All Applications", "Are you sure you want to delete ALL applications? This action cannot be undone!", icon='warning'):
            try:
                self.cursor.execute('DELETE FROM job_applications')
                self.conn.commit()
                self.load_applications()
                messagebox.showinfo("Success", "All applications have been deleted!")
                if self.charts_visible:
                    self.update_pie_charts()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to delete applications: {str(e)}")

    def next_page(self):
        self.current_page += 1
        self.load_applications()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_applications()

    def change_page_size(self, new_size):
        try:
            old_size = self.page_size
            self.page_size = int(new_size)
            
            # Adjust current page to maintain approximate position
            total_items = (self.current_page - 1) * old_size
            self.current_page = (total_items // self.page_size) + 1
            
            # Reload with new page size
            self.load_applications()
            
            # Force scroll region update
            self.after(100, lambda: self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all")))
        except Exception as e:
            print(f"Error changing page size: {e}")

    def on_frame_configure(self, event=None):
        self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        # Update the width of the canvas window
        self.data_canvas.itemconfig(
            self.canvas_frame,
            width=max(self.scrollable_frame.winfo_reqwidth(), event.width)
        )

    def update_canvas_colors(self, _=None):
        """Update canvas colors when theme changes"""
        try:
            theme_color = self._fg_color
            canvas_bg = self._apply_appearance_mode(("gray95", "gray20"))
            text_color = self._apply_appearance_mode(("black", "white"))
            
            self.data_canvas.configure(bg=canvas_bg)
            self.scrollable_frame.configure(fg_color=theme_color)
            self.entries_container.configure(fg_color=theme_color)

            # Update header labels
            if hasattr(self, '_header_labels'):
                for label in self._header_labels:
                    label.configure(
                        fg_color="transparent",
                        text_color=text_color
                    )

            # Update all entries
            for child in self.entries_container.winfo_children():
                if isinstance(child, JobApplicationEntry):
                    child.configure(fg_color=theme_color)
                    for widget in child.winfo_children():
                        if isinstance(widget, ctk.CTkLabel):
                            if 'current_status' not in str(widget.cget('text')):
                                widget.configure(
                                    fg_color="transparent",
                                    text_color=text_color
                                )
        except Exception as e:
            print(f"Warning: Failed to apply theme colors: {str(e)}")

    def destroy(self):
        ctk.AppearanceModeTracker.remove(self._appearance_mode_callback)
        super().destroy()