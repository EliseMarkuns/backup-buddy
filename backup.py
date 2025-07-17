import os
import shutil
import time

def perform_backup(src, dst, logger, dry_run=False, update_progress=None):
    """ 
    Copy newer or missing files from src to dest.
    Uses logger(msg) to report status to GUI.
    """

    # Check if source and destination directions exist
    if not os.path.isdir(src):
        logger("Source path is not a valid directory.")
        return
    
    logger("Starting backup...")

    # Count the total number of files for the progress bar
    total_files = sum(len(files) for _, _, files in os.walk(src))
    copied_files = 0
    actually_copied = 0
    
    # Go through all folders and files in source
    for foldername, _, filenames in os.walk(src): # we don't need subfolders, so it's ignored with '_'
        # Create a relative path to maintain subfolder structure
        rel_path = os.path.relpath(foldername, src)
        target_folder = os.path.join(dst, rel_path)

        # Create the destination subfolder if it doesn't exist, proceed forward if folder exists
        if not dry_run:
            os.makedirs(target_folder, exist_ok=True)

        for filename in filenames:
            src_file = os.path.join(foldername, filename)
            dst_file = os.path.join(target_folder, filename)

            # Only copy the file if it doesn't already exist at destination
            # OR if the modification time on the source file is more recent
            if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                if dry_run:
                    logger(f"Would copy: {src_file} -> {dst_file}")
                else:
                    shutil.copy2(src_file, dst_file) # copy2 preserves metadata
                    logger(f"Copied: {src_file} -> {dst_file}")
                actually_copied += 1
            copied_files += 1
            logger(f"Progress: {copied_files}/{total_files}")
            if update_progress:
                update_progress(copied_files, total_files, src_file, actually_copied)
            time.sleep(0.001)
        

        if update_progress:
            update_progress(copied_files, total_files, None, actually_copied)
    logger("Backup complete.\n")
