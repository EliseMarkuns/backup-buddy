import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import time
from scheduling import get_jobs, add_job, remove_job, update_job_status, update_job_last_run, get_next_run_time
from backup import perform_backup

class BackupBuddyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Backup Buddy")
        self.job_frames = {}  # job_id: frame
        self.job_threads = {}
        self.job_pause_events = {}
        self.job_stop_events = {}
        self.job_progress = {}
        self.selected_job_id = None

        # --- Top Buttons ---
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(top_frame, text="New Job", command=self.open_new_job_window).pack(side="left", padx=5)
        tk.Button(top_frame, text="Rename", command=self.rename_selected_job).pack(side="left", padx=5)
        tk.Button(top_frame, text="Remove", command=self.remove_selected_job).pack(side="left", padx=5)
        tk.Button(top_frame, text="Edit", command=self.edit_selected_job).pack(side="left", padx=5)

        # Add Settings button to top right
        settings_btn = tk.Button(top_frame, text="Settings", command=self.open_settings_window)
        settings_btn.pack(side="right", padx=5)

        # --- Jobs Area with Scrollbar ---
        jobs_frame = tk.Frame(root)
        jobs_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        jobs_canvas = tk.Canvas(jobs_frame, borderwidth=0)
        jobs_canvas.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(jobs_frame, orient="vertical", command=jobs_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.jobs_area = tk.Frame(jobs_canvas)
        self.jobs_area_id = jobs_canvas.create_window((0, 0), window=self.jobs_area, anchor="nw")
        def _on_frame_configure(event):
            jobs_canvas.configure(scrollregion=jobs_canvas.bbox("all"))
            jobs_canvas.itemconfig(self.jobs_area_id, width=jobs_canvas.winfo_width())
        self.jobs_area.bind("<Configure>", _on_frame_configure)
        def _on_canvas_configure(event):
            jobs_canvas.itemconfig(self.jobs_area_id, width=event.width)
        jobs_canvas.bind("<Configure>", _on_canvas_configure)
        jobs_canvas.configure(yscrollcommand=scrollbar.set)
        # Set a fixed or minimum window size
        self.root.minsize(600, 500)
        self.root.geometry("700x500")

        # Custom style for thicker progress bars
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Thick.Horizontal.TProgressbar", thickness=16)

        self.refresh_job_list()

        # Start auto-scheduler in background
        threading.Thread(target=self.auto_scheduler_loop, daemon=True).start()

        # --- Events Log Area at Bottom ---
        log_frame = tk.Frame(root, bd=2, relief="groove", height=120)
        log_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
        log_frame.pack_propagate(False)
        tk.Label(log_frame, text="Events", font=("Arial", 10, "bold")).pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=5, state="disabled", font=("Consolas", 9), wrap="word")
        self.log_text.pack(fill="x", expand=False)
        self.log_text.configure(height=5)

        # Enable mouse wheel scrolling for jobs_canvas only when mouse is over jobs_area
        def _on_mousewheel(event):
            if os.name == 'nt':  # Windows
                jobs_canvas.yview_scroll(-1 * int(event.delta / 120), "units")
            else:  # MacOS, Linux
                jobs_canvas.yview_scroll(-1 * int(event.delta), "units")
        def _bind_mousewheel(event):
            jobs_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            jobs_canvas.bind_all("<Button-4>", lambda e: jobs_canvas.yview_scroll(-1, "units"))  # Linux scroll up
            jobs_canvas.bind_all("<Button-5>", lambda e: jobs_canvas.yview_scroll(1, "units"))   # Linux scroll down
        def _unbind_mousewheel(event):
            jobs_canvas.unbind_all("<MouseWheel>")
            jobs_canvas.unbind_all("<Button-4>")
            jobs_canvas.unbind_all("<Button-5>")
        self.jobs_area.bind("<Enter>", _bind_mousewheel)
        self.jobs_area.bind("<Leave>", _unbind_mousewheel)

    def safe_refresh_job_list(self):
        if threading.current_thread() is threading.main_thread():
            self.refresh_job_list()
        else:
            self.root.after(0, self.refresh_job_list)

    def refresh_job_list(self):
        # Clear existing job frames
        for frame in self.job_frames.values():
            frame.destroy()
        self.job_frames.clear()

        jobs = get_jobs()
        # In-memory status for this session only
        if not hasattr(self, 'job_status'):  # Only initialize once
            self.job_status = {}
        for job in jobs:
            job_id = job['id']
            # If job is new or app just started, set status to idle
            if job_id not in self.job_status:
                self.job_status[job_id] = 'idle'
            self.add_job_frame(job)
        # Reselect previously selected job if it still exists
        if self.selected_job_id and self.selected_job_id in self.job_frames:
            self.highlight_selected_job()
        else:
            self.selected_job_id = None

    def add_job_frame(self, job):
        job_id = job['id']
        frame = tk.Frame(self.jobs_area, bd=2, relief="groove", pady=4)
        frame.pack(fill="x", pady=4)

        # Job name and destination
        name_lbl = tk.Label(frame, text=f"Name: {job['id']}", font=("Arial", 12, "bold"))
        name_lbl.pack(anchor="w")
        dest_lbl = tk.Label(frame, text=f"Destination: {job['destination']}", font=("Arial", 10))
        dest_lbl.pack(anchor="w")

        # Button area
        btn_frame = tk.Frame(frame)
        btn_frame.pack(anchor="w", pady=2)

        # Progress bar and status label (always visible)
        progress = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate", style="Thick.Horizontal.TProgressbar")
        progress.pack(anchor="w", pady=2)
        status_label = tk.Label(frame, text="", font=("Arial", 9))
        status_label.pack(anchor="w")

        # Action buttons
        status = self.job_status.get(job_id, 'idle')
        if status == 'idle':
            start_btn = tk.Button(btn_frame, text="Start Backup", command=lambda j=job: self.start_job(j, progress, btn_frame, status_label))
            start_btn.pack(side="left")
            # Show last_run info in status_label
            last_run = job.get('last_run')
            if last_run:
                try:
                    import datetime
                    dt = datetime.datetime.fromisoformat(last_run)
                    formatted = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    formatted = last_run
                status_label['text'] = f"Last run: {formatted}"
            else:
                status_label['text'] = "Last run: Never"
            progress['value'] = 0
        elif status == 'paused':
            continue_btn = tk.Button(btn_frame, text="Continue", command=lambda j=job_id: self.continue_job(j))
            continue_btn.pack(side="left")
            stop_btn = tk.Button(btn_frame, text="Stop", command=lambda j=job_id: self.stop_job(j))
            stop_btn.pack(side="left")
            progress['value'] = self.job_progress.get(job_id, 0)
            status_label['text'] = self.job_progress.get(f"{job_id}_status", "Paused")
        else:  # running
            pause_btn = tk.Button(btn_frame, text="Pause", command=lambda j=job_id: self.pause_job(j))
            pause_btn.pack(side="left")
            stop_btn = tk.Button(btn_frame, text="Stop", command=lambda j=job_id: self.stop_job(j))
            stop_btn.pack(side="left")
            progress['value'] = self.job_progress.get(job_id, 0)
            status_label['text'] = self.job_progress.get(f"{job_id}_status", "")

        # Select job on click
        def select_and_highlight(event=None, jid=job_id):
            self.selected_job_id = jid
            self.highlight_selected_job()
        frame.bind("<Button-1>", select_and_highlight)
        name_lbl.bind("<Button-1>", select_and_highlight)
        dest_lbl.bind("<Button-1>", select_and_highlight)

        self.job_frames[job_id] = frame

    def highlight_selected_job(self):
        for jid, frame in self.job_frames.items():
            if jid == self.selected_job_id:
                frame.config(bg="#cce6ff")  # Light blue highlight
            else:
                frame.config(bg=self.root.cget('bg'))

    def open_new_job_window(self):
        win = tk.Toplevel(self.root)
        win.title("Create New Backup Job")
        win.grab_set()
        win.focus_force()
        tk.Label(win, text="Job Name:").grid(row=0, column=0, sticky="w")
        name_entry = tk.Entry(win, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(win, text="Source Folder:").grid(row=1, column=0, sticky="w")
        src_entry = tk.Entry(win, width=30)
        src_entry.grid(row=1, column=1, padx=5, pady=2)
        tk.Button(win, text="Browse", command=lambda: self.browse_entry(src_entry)).grid(row=1, column=2)
        tk.Label(win, text="Destination Folder:").grid(row=2, column=0, sticky="w")
        dst_entry = tk.Entry(win, width=30)
        dst_entry.grid(row=2, column=1, padx=5, pady=2)
        tk.Button(win, text="Browse", command=lambda: self.browse_entry(dst_entry)).grid(row=2, column=2)
        tk.Label(win, text="Interval:").grid(row=3, column=0, sticky="w")
        interval_var = tk.StringVar(value="Daily")
        interval_dropdown = ttk.Combobox(win, textvariable=interval_var, values=["Daily", "Weekly", "Every N Days"])
        interval_dropdown.grid(row=3, column=1, padx=5, pady=2)
        tk.Label(win, text="Time (HH:MM):").grid(row=4, column=0, sticky="w")
        time_entry = tk.Entry(win)
        time_entry.insert(0, "02:00")
        time_entry.grid(row=4, column=1, padx=5, pady=2)
        tk.Label(win, text="N Days:").grid(row=5, column=0, sticky="w")
        n_days_entry = tk.Entry(win)
        n_days_entry.grid(row=5, column=1, padx=5, pady=2)
        n_days_entry.insert(0, "3")
        n_days_entry.configure(state="disabled")
        def toggle_n_days(*args):
            if interval_var.get() == "Every N Days":
                n_days_entry.configure(state="normal")
            else:
                n_days_entry.configure(state="disabled")
        interval_var.trace("w", toggle_n_days)
        def create_job():
            name = name_entry.get().strip()
            src = src_entry.get().strip()
            dst = dst_entry.get().strip()
            interval = interval_var.get()
            time_str = time_entry.get().strip()
            n_days = int(n_days_entry.get()) if interval == 'Every N Days' else None
            if not name or not src or not dst or not time_str:
                messagebox.showerror("Error", "All fields are required.")
                return
            add_job(name, src, dst, interval, time_str, n_days)
            self.log_event(f"Job created: {name}")
            win.destroy()
            self.safe_refresh_job_list()
        tk.Button(win, text="Create", command=create_job).grid(row=6, column=1, pady=5)

    def browse_entry(self, entry):
        folder = filedialog.askdirectory()
        if folder:
            entry.delete(0, tk.END)
            entry.insert(0, folder)

    # --- Rename Dialog ---
    def rename_selected_job(self):
        if not self.selected_job_id:
            messagebox.showinfo("Rename", "Please select a job to rename.")
            return
        new_name = simpledialog.askstring("Rename Job", "Enter new job name:")
        if new_name:
            jobs = get_jobs()
            job = next((j for j in jobs if j['id'] == self.selected_job_id), None)
            if job:
                add_job(new_name, job['source'], job['destination'], job['interval'], job['time'], job['n_days'])
                remove_job(self.selected_job_id)
                self.log_event(f"Job renamed: {self.selected_job_id} -> {new_name}")
                #self.selected_job_id = new_name
                self.refresh_job_list()
                #self.log_event(f"Job renamed to: {new_name}")  # Log job renaming

    def remove_selected_job(self):
        if not self.selected_job_id:
            messagebox.showinfo("Remove", "Please select a job to remove.")
            return
        self.log_event(f"Job deleted: {self.selected_job_id}")
        remove_job(self.selected_job_id)
        if hasattr(self, 'job_status') and self.selected_job_id in self.job_status:
            del self.job_status[self.selected_job_id]
        self.selected_job_id = None
        self.safe_refresh_job_list()

    def start_job(self, job, progress, btn_frame, status_label):
        job_id = job['id']
        pause_event = self.job_pause_events.setdefault(job_id, threading.Event())
        stop_event = self.job_stop_events.setdefault(job_id, threading.Event())
        pause_event.clear()
        stop_event.clear()
        self.job_status[job_id] = 'running'
        self.log_event(f"Job started: {job_id}")
        # Replace Start with Pause/Stop
        for widget in btn_frame.winfo_children():
            widget.destroy()
        pause_btn = tk.Button(btn_frame, text="Pause", command=lambda: self.pause_job(job_id))
        pause_btn.pack(side="left")
        stop_btn = tk.Button(btn_frame, text="Stop", command=lambda: self.stop_job(job_id))
        stop_btn.pack(side="left")
        progress.pack(anchor="w", pady=2)
        status_label.pack(anchor="w")
        progress['value'] = 0
        progress.update_idletasks()
        status_label['text'] = ""
        status_label.update_idletasks()

        def progress_callback(current, total, filename=None, actually_copied=None):
            percent = int((current / total) * 100)
            def update_ui():
                self.job_progress[job_id] = percent
                prev_copied = getattr(self, '_last_files_copied', 0)
                progress['value'] = percent
                if filename:
                    shortname = os.path.basename(filename)
                    # Determine if this file is being copied or just scanned
                    op = "Copying" if (actually_copied is not None and actually_copied > prev_copied) else "Scanning"
                    status_label['text'] = f"{op}: {shortname} ({current}/{total})"
                else:
                    status_label['text'] = f"{current}/{total}"
                self._last_files_copied = actually_copied if actually_copied is not None else current
                progress.update_idletasks()
                status_label.update_idletasks()
            self.root.after(0, update_ui)
            while pause_event.is_set():
                threading.Event().wait(0.1)
            if stop_event.is_set():
                raise Exception('Backup stopped by user.')

        def log_callback(msg):
            pass

        def on_finish(success):
            self.job_status[job_id] = 'idle'
            if success:
                update_job_last_run(job_id)
                # Count files copied from job_progress (should be 100% at end)
                files_copied = None
                if hasattr(self, 'job_progress'):
                    # Try to get total from last progress update
                    files_copied = getattr(self, '_last_files_copied', None)
                msg = f"Job finished: {job_id}"
                if files_copied is not None:
                    msg += f" ({files_copied} files copied)"
                self.log_event(msg)
            else:
                self.log_event(f"Job failed or stopped: {job_id}")
            self.root.after(0, self.refresh_job_list)

        def backup_thread():
            success = False
            try:
                perform_backup(job['source'], job['destination'], log_callback, False, progress_callback)
                success = True
            except Exception:
                pass
            on_finish(success)

        t = threading.Thread(target=backup_thread, daemon=True)
        self.job_threads[job_id] = t
        t.start()

    def pause_job(self, job_id):
        self.job_pause_events[job_id].set()
        self.job_status[job_id] = 'paused'
        if threading.current_thread() is threading.main_thread():
            self._update_job_buttons_and_status(job_id)
        else:
            self.root.after(0, self._update_job_buttons_and_status, job_id)

    def continue_job(self, job_id):
        if job_id in self.job_pause_events:
            self.job_pause_events[job_id].clear()
        self.job_status[job_id] = 'running'
        if threading.current_thread() is threading.main_thread():
            self._update_job_buttons_and_status(job_id)
        else:
            self.root.after(0, self._update_job_buttons_and_status, job_id)

    def stop_job(self, job_id):
        self.job_stop_events[job_id].set()
        self.job_status[job_id] = 'idle'
        self.safe_refresh_job_list()

    def log_event(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.config(state="normal")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
        self.log_text.config(state="disabled")

    def _update_job_buttons_and_status(self, job_id):
        frame = self.job_frames.get(job_id)
        if not frame:
            return
        btn_frame = None
        progress = None
        status_label = None
        for child in frame.winfo_children():
            if isinstance(child, tk.Frame):
                btn_frame = child
            if isinstance(child, ttk.Progressbar):
                progress = child
            if isinstance(child, tk.Label):
                status_label = child
        if not btn_frame or not status_label:
            return
        # Remove all buttons
        for widget in btn_frame.winfo_children():
            widget.destroy()
        status = self.job_status.get(job_id, 'idle')
        if status == 'paused':
            continue_btn = tk.Button(btn_frame, text="Continue", command=lambda j=job_id: self.continue_job(j))
            continue_btn.pack(side="left")
            stop_btn = tk.Button(btn_frame, text="Stop", command=lambda j=job_id: self.stop_job(j))
            stop_btn.pack(side="left")
            status_label['text'] = self.job_progress.get(f"{job_id}_status", "Paused")
        elif status == 'running':
            pause_btn = tk.Button(btn_frame, text="Pause", command=lambda j=job_id: self.pause_job(j))
            pause_btn.pack(side="left")
            stop_btn = tk.Button(btn_frame, text="Stop", command=lambda j=job_id: self.stop_job(j))
            stop_btn.pack(side="left")
            status_label['text'] = self.job_progress.get(f"{job_id}_status", "")
        btn_frame.update_idletasks()
        status_label.update_idletasks()

    # --- Automatic Scheduler ---
    def auto_scheduler_loop(self):
        while True:
            jobs = get_jobs()
            for job in jobs:
                job_id = job['id']
                if self.job_status.get(job_id, 'idle') == 'idle':
                    next_run = get_next_run_time(job)
                    if next_run and time.time() >= next_run.timestamp():
                        pause_event = self.job_pause_events.setdefault(job_id, threading.Event())
                        stop_event = self.job_stop_events.setdefault(job_id, threading.Event())
                        pause_event.clear()
                        stop_event.clear()
                        update_job_status(job_id, 'running')
                        # Schedule widget lookup and job start on main thread
                        self.root.after(0, self._start_job_by_id, job)
            time.sleep(30)

    def _start_job_by_id(self, job):
        job_id = job['id']
        frame = self.job_frames.get(job_id)
        if frame:
            btn_frame = None
            progress = None
            status_label = None
            for child in frame.winfo_children():
                if isinstance(child, tk.Frame):
                    btn_frame = child
                if isinstance(child, ttk.Progressbar):
                    progress = child
                if isinstance(child, tk.Label):
                    status_label = child
            if btn_frame and progress and status_label:
                self.start_job(job, progress, btn_frame, status_label)

    def edit_selected_job(self):
        if not self.selected_job_id:
            messagebox.showinfo("Edit", "Please select a job to edit.")
            return
        jobs = get_jobs()
        job = next((j for j in jobs if j['id'] == self.selected_job_id), None)
        if not job:
            messagebox.showerror("Error", "Selected job not found.")
            return
        win = tk.Toplevel(self.root)
        win.title(f"Edit Job: {job['id']}")
        win.grab_set()
        win.focus_force()
        tk.Label(win, text="Job Name:").grid(row=0, column=0, sticky="w")
        name_entry = tk.Entry(win, width=30)
        name_entry.insert(0, job['id'])
        name_entry.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(win, text="Source Folder:").grid(row=1, column=0, sticky="w")
        src_entry = tk.Entry(win, width=30)
        src_entry.insert(0, job['source'])
        src_entry.grid(row=1, column=1, padx=5, pady=2)
        tk.Button(win, text="Browse", command=lambda: self.browse_entry(src_entry)).grid(row=1, column=2)
        tk.Label(win, text="Destination Folder:").grid(row=2, column=0, sticky="w")
        dst_entry = tk.Entry(win, width=30)
        dst_entry.insert(0, job['destination'])
        dst_entry.grid(row=2, column=1, padx=5, pady=2)
        tk.Button(win, text="Browse", command=lambda: self.browse_entry(dst_entry)).grid(row=2, column=2)
        tk.Label(win, text="Interval:").grid(row=3, column=0, sticky="w")
        interval_var = tk.StringVar(value=job.get('interval', 'Daily'))
        interval_dropdown = ttk.Combobox(win, textvariable=interval_var, values=["Daily", "Weekly", "Every N Days"])
        interval_dropdown.grid(row=3, column=1, padx=5, pady=2)
        tk.Label(win, text="Time (HH:MM):").grid(row=4, column=0, sticky="w")
        time_entry = tk.Entry(win)
        time_entry.insert(0, job.get('time', '02:00'))
        time_entry.grid(row=4, column=1, padx=5, pady=2)
        tk.Label(win, text="N Days:").grid(row=5, column=0, sticky="w")
        n_days_entry = tk.Entry(win)
        n_days_entry.grid(row=5, column=1, padx=5, pady=2)
        n_days_val = job.get('n_days')
        n_days_entry.insert(0, str(n_days_val) if n_days_val is not None else "3")
        if interval_var.get() != "Every N Days":
            n_days_entry.configure(state="disabled")
        def toggle_n_days(*args):
            if interval_var.get() == "Every N Days":
                n_days_entry.configure(state="normal")
            else:
                n_days_entry.configure(state="disabled")
        interval_var.trace("w", toggle_n_days)
        def save_edits():
            name = name_entry.get().strip()
            src = src_entry.get().strip()
            dst = dst_entry.get().strip()
            interval = interval_var.get()
            time_str = time_entry.get().strip()
            n_days = int(n_days_entry.get()) if interval == 'Every N Days' else None
            if not name or not src or not dst or not time_str:
                messagebox.showerror("Error", "All fields are required.")
                return
            # Remove old job, add new/edited job
            remove_job(job['id'])
            add_job(name, src, dst, interval, time_str, n_days)
            self.log_event(f"Job edited: {job['id']} -> {name}")
            self.selected_job_id = name
            win.destroy()
            self.safe_refresh_job_list()
        tk.Button(win, text="Save", command=save_edits).grid(row=6, column=1, pady=5)

    def open_settings_window(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.grab_set()
        win.focus_force()
        win.resizable(False, False)
        # Checkbox for startup
        current = self._is_in_startup()
        var = tk.BooleanVar()
        var.set(current)
        chk = tk.Checkbutton(win, text="Launch Backup-Buddy on Startup", variable=var)
        chk.pack(padx=20, pady=20)
        def on_close():
            new_val = var.get()
            if new_val != current:
                if new_val:
                    self._add_to_startup()
                else:
                    self._remove_from_startup()
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", on_close)

    def _get_startup_shortcut_path(self):
        import os
        import sys
        from pathlib import Path
        if os.name == 'nt':
            startup_dir = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup')
            exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            shortcut_name = "Backup-Buddy.lnk"
            return os.path.join(startup_dir, shortcut_name), exe, script
        elif sys.platform.startswith('linux'):
            autostart_dir = os.path.expanduser('~/.config/autostart')
            if not os.path.exists(autostart_dir):
                os.makedirs(autostart_dir, exist_ok=True)
            desktop_file = os.path.join(autostart_dir, 'backup-buddy.desktop')
            exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            return desktop_file, exe, script
        else:
            return None, None, None

    def _add_to_startup(self):
        import sys
        import os
        shortcut_path, exe, script = self._get_startup_shortcut_path()
        if os.name == 'nt':
            try:
                import pythoncom
                import win32com.client
            except ImportError:
                try:
                    import subprocess
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pywin32'])
                    import pythoncom
                    import win32com.client
                except Exception:
                    self.log_event("pywin32 is required for startup shortcut. Please install it manually.")
                    return
            shell = win32com.client.Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe
            shortcut.Arguments = f'"{script}"'
            shortcut.WorkingDirectory = os.path.dirname(script)
            shortcut.IconLocation = exe
            shortcut.save()
            self.log_event("Added Backup-Buddy to startup.")
        elif sys.platform.startswith('linux'):
            desktop_entry = f"""[Desktop Entry]\nType=Application\nExec={exe} {script}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\nName=Backup-Buddy\nComment=Backup-Buddy Auto Start\n"""
            try:
                with open(shortcut_path, 'w') as f:
                    f.write(desktop_entry)
                os.chmod(shortcut_path, 0o755)
                self.log_event("Added Backup-Buddy to startup (Linux autostart).")
            except Exception as e:
                self.log_event(f"Failed to add to startup: {e}")
        else:
            self.log_event("Startup feature not supported on this OS.")

    def _remove_from_startup(self):
        import sys
        import os
        shortcut_path, _, _ = self._get_startup_shortcut_path()
        if shortcut_path and os.path.exists(shortcut_path):
            try:
                os.remove(shortcut_path)
                self.log_event("Removed Backup-Buddy from startup.")
            except Exception as e:
                self.log_event(f"Failed to remove from startup: {e}")

    def _is_in_startup(self):
        import sys
        import os
        shortcut_path, _, _ = self._get_startup_shortcut_path()
        return shortcut_path and os.path.exists(shortcut_path)

def main():
    root = tk.Tk()
    app = BackupBuddyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()


