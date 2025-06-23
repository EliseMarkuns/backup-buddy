import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import time
from backup import perform_backup
from utils import log_message
import threading

class BackupBuddyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Backup Buddy - Backups made easy :)")

    # --- GUI Layout ---

        # Row 0: Source folder
        tk.Label(root, text="Source Folder:").grid(row=0, column=0, sticky="w")
        self.source_entry = tk.Entry(root, width=50)
        self.source_entry.grid(row=0, column=1, padx=5)
        tk.Button(root, text="Browse", command=self.browse_source).grid(row=0, column=2)

        # Row 1: Destination folder
        tk.Label(root, text="Backup Folder:").grid(row=1, column=0, sticky="w")
        self.dest_entry = tk.Entry(root, width=50)
        self.dest_entry.grid(row=1, column=1, padx=5)
        tk.Button(root, text="Browse", command=self.browse_dest).grid(row=1, column=2)

        # Row 2: Start backup button
        self.start_button = tk.Button(root, text="Start Backup", command=self.start_backup)
        self.start_button.grid(row=2, column=0, pady=10)

        # Row 2: Dry run checkbox
        self.dry_run_var = tk.BooleanVar()
        self.dry_run_check = tk.Checkbutton(root, text="Dry Run", variable=self.dry_run_var)
        self.dry_run_check.grid(row=2, column=1)

        # Row 2: Clear log button
        self.clear_button = tk.Button(root, text="Clear Log", command=self.clear_log)
        self.clear_button.grid(row=2, column=2)

        # Row 3: Progress bar
        self.progress = ttk.Progressbar(root, length=400, mode="determinate")
        self.progress.grid(row=3, column=0, columnspan=3, pady=5)

        # Row 4+: Log output
        self.log = tk.Text(root, height=10, width=60)
        self.log.grid(row=4, column=0, columnspan=3, padx=10, pady=5)

        self.scrollbar = tk.Scrollbar(root, command=self.log.yview)
        self.scrollbar.grid(row=4, column=3, sticky="ns")
        self.log.config(yscrollcommand=self.scrollbar.set)

    # --- GUI Functions ---

    def browse_source(self):
        # Open a file browser and select the source path
        folder = filedialog.askdirectory()
        if folder:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, folder)

    def browse_dest(self):
        # Open a file browser and select the destination path
        folder = filedialog.askdirectory()
        if folder:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, folder)
          
    def clear_log(self):
        self.log.delete("1.0", tk.END)

    def log_message(self, msg):
        log_message(self.log, msg)

    def update_progress(self, current, total):
        percent = int((current / total) * 100)
        self.progress["value"] = percent
        self.root.update_idletasks()

    def start_backup(self):
        # Get inputs from GUI
        src = self.source_entry.get()
        dst = self.dest_entry.get()
        dry_run = self.dry_run_var.get()

        # Reset progress and clear log
        self.progress["value"] = 0
        self.log.delete("1.0", tk.END)

        # Start the backup in a new thread
        thread = threading.Thread(
            target=perform_backup,
            args=(src, dst, self.log_message),
            kwargs={
                "dry_run": dry_run,
                "update_progress": self.update_progress
            },
            daemon=True
        )
        thread.start()
            

        