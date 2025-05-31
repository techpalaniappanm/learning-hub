import os
import shutil

def organize_files_by_extension(root_folder, extensions_to_organize):
    """
    Organizes files in a folder and its subfolders based on their extensions.

    Args:
        root_folder (str): The path to the main folder to organize.
        extensions_to_organize (list): A list of file extensions (without the dot)
                                         to organize (e.g., ['md', 'txt', 'jpg']).
    """
    if not os.path.isdir(root_folder):
        print(f"Error: Folder '{root_folder}' not found.")
        return

    print(f"Starting organization in: {root_folder}")
    print(f"Organizing for extensions: {', '.join(extensions_to_organize)}")

    moved_files_count = 0
    deleted_dirs_count = 0

    # Create target directories for specified extensions at the root level
    for ext in extensions_to_organize:
        target_ext_folder = os.path.join(root_folder, ext)
        if not os.path.exists(target_ext_folder):
            try:
                os.makedirs(target_ext_folder)
                print(f"Created directory: {target_ext_folder}")
            except OSError as e:
                print(f"Error creating directory {target_ext_folder}: {e}")
                return  # Stop if we can't create essential directories

    # Walk through the directory tree
    for dirpath, dirnames, filenames in os.walk(root_folder, topdown=False):
        # Skip the target extension directories we just created at the root
        if os.path.basename(dirpath) in extensions_to_organize and os.path.dirname(dirpath) == root_folder:
            continue

        for filename in filenames:
            file_extension = filename.split('.')[-1].lower()

            if file_extension in extensions_to_organize:
                source_file_path = os.path.join(dirpath, filename)
                target_folder_for_ext = os.path.join(root_folder, file_extension)
                target_file_path = os.path.join(target_folder_for_ext, filename)

                # Ensure target filename is unique if it already exists
                counter = 1
                original_target_file_path = target_file_path
                while os.path.exists(target_file_path):
                    name, ext = os.path.splitext(original_target_file_path)
                    target_file_path = f"{name}_{counter}{ext}"
                    counter += 1

                try:
                    shutil.move(source_file_path, target_file_path)
                    print(f"Moved: '{source_file_path}' to '{target_file_path}'")
                    moved_files_count += 1
                except Exception as e:
                    print(f"Error moving file '{source_file_path}': {e}")

        # After processing files in a directory, check if it's empty
        # (and not one of the root extension folders or the root folder itself)
        if dirpath != root_folder and not os.listdir(dirpath) and \
           os.path.basename(dirpath) not in extensions_to_organize:
            try:
                os.rmdir(dirpath)
                print(f"Deleted empty directory: '{dirpath}'")
                deleted_dirs_count += 1
            except OSError as e:
                # It's possible it was deleted in a previous iteration if it was a nested empty folder
                # Or it might not be truly empty due to hidden files not caught by os.listdir
                # Or permission issues.
                if os.path.exists(dirpath) and os.listdir(dirpath): # Check again
                     print(f"Could not delete directory '{dirpath}' as it's not empty: {e}")
                elif not os.path.exists(dirpath):
                    pass # Already deleted, no issue
                else:
                    print(f"Error deleting directory '{dirpath}': {e}")


    print("\n--- Organization Summary ---")
    print(f"Total files moved: {moved_files_count}")
    print(f"Total empty directories deleted: {deleted_dirs_count}")
    print("Organization complete.")

if __name__ == "__main__":
    print("📂 File Organizer Script 📂")
    print("This script will move files into folders named after their extensions.")
    print("It will also attempt to delete empty subdirectories after moving files.")
    print("-" * 30)

    while True:
        folder_to_scan = input("Enter the full path to the folder you want to organize: ").strip()
        if os.path.isdir(folder_to_scan):
            break
        else:
            print("Invalid folder path. Please try again.")

    while True:
        extensions_input = input("Enter the file extensions to organize, separated by commas (e.g., md,txt,jpg): ").strip().lower()
        if extensions_input:
            extensions_list = [ext.strip() for ext in extensions_input.split(',') if ext.strip()]
            if extensions_list:
                break
            else:
                print("No valid extensions provided. Please enter at least one extension.")
        else:
            print("Please enter at least one extension.")

    print("-" * 30)
    confirmation = input(f"Are you sure you want to organize files with extensions '{', '.join(extensions_list)}' in '{folder_to_scan}'? (yes/no): ").strip().lower()

    if confirmation == 'yes':
        organize_files_by_extension(folder_to_scan, extensions_list)
    else:
        print("Operation cancelled by the user.")