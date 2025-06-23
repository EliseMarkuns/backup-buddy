import os
import shutil

def perform_backup(src, dst, logger):
    """ 
    Copy newer or missing files from src to dest.
    Uses logger(msg) to report status to GUI.
    """

    # Check if source and destination directions exist
    if not os.path.exists(src) or not os.path.exists(dst):
        logger("Invalid source or destination folder.")
        return
    
    logger("Starting backup...")

    # Go through all folders and files in source
    for foldername, subfolders, filenames in os.walk(src):
        # Create a relative path to maintain subfolder structure
        rel_path = os.path.relpath(foldername, src)
        target_folder = os.path.join(dst, rel_path)

        # Create the destination subfolder if it doesn't exist, proceed forward if folder exists
        os.makedirs(target_folder, exist_ok=True)

        for filename in filenames:
            src_file = os.path.join(foldername, filename)
            dst_file = os.path.join(target_folder, filename)

            # Only copy the file if it doesn't already exist at destination
            # OR if the modification time on the source file is more recent
            if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                shutil.copy2(src_file, dst_file) # copy2 preserves metadata
                logger(f"Copied: {src_file} -> {dst_file}")

    logger("Backup complete.\n")
