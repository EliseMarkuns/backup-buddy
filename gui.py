from tkinter import Label, Button, Entry, Text, StringVar, IntVar, END, filedialog
from tkinter.ttk import Spinbox
import time
from backup import perform_backup
import threading

class BackupBuddyApp:
    def __init__(self, master):
        self.master = master
        master.title("Backup Buddy - Backups made easy :)")

        # Preparing variables for user input
        self.source_dir = StringVar()       # Path to source folder
        self.dest_dir = StringVar()         # Path to destination folder
        self.interval = IntVar(value=5)     # Backup interval in minutes
        self.running = False                # Is backup actively being performed


    # --- GUI Layout ---

        # Source folder
        Label(master, text="Source Folder:").grid(row=0, column=0)
        Entry(master, textvariable=self.source_dir, width=50).grid(row=0, column=1)
        Button(master, text="Browse", command=self.browse_source).grid(row=0, column=2)

        # Destination folder
        Label(master, text="Backup Folder:").grid(row=1, column=0)
        Entry(master, textvariable=self.dest_dir, width=50).grid(row=1, column=1)
        Button(master, text="Browse", command=self.browse_dest).grid(row=1,column=2)

        # Start/Stop backup button
        self.start_button = Button(master, text="Start Backup", command=self.toggle_backup)
        self.start_button.grid(row=2, column=1)

        # Log box
        self.log = Text(master, height=10, width=70)
        self.log.grid(row=4, column=0, columnspan=3)

    # --- GUI Functions ---

    def browse_source(self):
        # Open a file browser and select the source path
        folder = filedialog.askdirectory()
        if folder:
            self.source_dir.set(folder)

    def browse_dest(self):
        # Open a file browser and select the destination path
        folder = filedialog.askdirectory()
        if folder:
            self.dest_dir.set(folder)

    def toggle_backup(self):
        # Start or stop the backup loop based on current state
        if not self.running:
            self.running = True
            self.start_button.config(text="Stop Backup")
            threading.Thread(target=self.backup_loop, daemon=True).start()
            self.log_message("Backup started.")
        else:
            self.running = False
            self.start_button.config(text="Start Backup")
            self.log_message("Backup stopped.")

    def backup_loop(self):
        while self.running:
            try:
                perform_backup(self.source_dir.get(), self.dest_dir.get(), self.log_message)
                self.toggle_backup()
            except Exception as e:
                self.log_message(f"Error: {e}")
            

    def timestamped(self, message):
        # Returns a timestampted log entry as a string

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        return f"{timestamp} - {message}\n"
          
    def log_message(self, msg):
        self.log.insert(END, self.timestamped(msg))
        