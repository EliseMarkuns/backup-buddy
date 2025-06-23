import tkinter as tk
import time

def timestamped(message):
        # Returns a timestampted log entry as a string

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        return f"{timestamp} - {message}"

def log_message(widget, message):
        msg = timestamped(message)
        widget.insert(tk.END, msg + "\n")
        widget.see(tk.END)