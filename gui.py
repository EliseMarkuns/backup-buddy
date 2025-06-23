from tkinter import Label, Button, Entry, Text, StringVar, IntVar, END, filedialog
from tkinter.ttk import Spinbox

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
        Button(master, text="Browse").grid(row=0, column=2)

        # Destination folder
        Label(master, text="Backup Folder:").grid(row=1, column=0)
        Entry(master, textvariable=self.dest_dir, width=50).grid(row=1, column=1)
        Button(master, text="Browse").grid(row=1,column=2)

        # Start/Stop backup button
        self.start_button = Button(master, text="Start Backup").grid(row=2, column=1)

        
        