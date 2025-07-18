import os
import sys
from pathlib import Path
import shutil
import win32com.client


def add_to_startup(self):     
        shortcut_path, exe, script = _get_startup_shortcut_path(self)
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

def remove_from_startup(self):
    shortcut_path, _, _ = _get_startup_shortcut_path(self)
    if shortcut_path and os.path.exists(shortcut_path):
        try:
            os.remove(shortcut_path)
            self.log_event("Removed Backup-Buddy from startup.")
        except Exception as e:
            self.log_event(f"Failed to remove from startup: {e}")

def is_in_startup(self):
    shortcut_path, _, _ = _get_startup_shortcut_path(self)
    return shortcut_path and os.path.exists(shortcut_path)

def _get_startup_shortcut_path(self):
    if os.name == 'nt':
        startup_dir = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup')
        exe = sys.executable.replace("python.exe", "pythonw.exe")
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