import tkinter as tk
import time
import json
import os

CONFIG_FILE = "config.json"

def save_config(src, dst):
    config = {"source": src, "destination": dst}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_config():
      if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                  return json.load(f)
            return {}


def timestamped(message):
        # Returns a timestampted log entry as a string

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        return f"{timestamp} - {message}"

def log_message(widget, message):
        msg = timestamped(message)
        widget.insert(tk.END, msg + "\n")
        widget.see(tk.END)

