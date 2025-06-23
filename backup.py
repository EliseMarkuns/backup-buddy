import os
import shutil

def perform_backup(src, dst, logger, dry_run = False):
    """ 
    Copy newer or missing files from src to dest.
    Uses logger(msg) to report status to GUI.
    """

    # Check if source and destination directions exist
    if not os.path.isdir(src):
        logger("Source path is not a valid directory.")
        return
    
    logger("Starting backup...")

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

    logger("Backup complete.\n")
