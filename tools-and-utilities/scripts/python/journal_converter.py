import os
import re
from datetime import datetime

def get_file_creation_date(filepath):
    """
    Tries to get the file's birth time (creation time).
    Falls back to ctime (last metadata change on Unix, creation on Windows)
    if birthtime attribute is not available.
    Returns a datetime.date object.
    """
    try:
        # Attempt to get st_birthtime (available on macOS, Windows, some Linux systems)
        stat_info = os.stat(filepath)
        timestamp = stat_info.st_birthtime
    except AttributeError:
        # Fallback: os.path.getctime()
        # On Windows, this is the creation time.
        # On Unix (Linux/macOS), this is the time of the last metadata change.
        timestamp = os.path.getctime(filepath)
    return datetime.fromtimestamp(timestamp).date()

def get_base_name_and_ext_from_filename(filename):
    """
    Splits filename into its name part and extension.
    Intelligently extracts a base name by removing a trailing _YYYY_MM_DD pattern
    if it exists and is a valid date.
    Returns (base_name, existing_date_str_or_None, extension_including_dot)
    """
    name_part_full, ext_part = os.path.splitext(filename)
    
    # Regex to find an optional date like _YYYY_MM_DD at the very end of the name_part_full
    # and capture the part before it.
    match = re.fullmatch(r'(.*?)(_(\d{4}_\d{2}_\d{2}))?$', name_part_full)
    
    base_name = name_part_full # Default to the full name part
    existing_date_str = None

    if match:
        # Check if the optional date group (group 2 which is _YYYY_MM_DD) was matched
        if match.group(2): 
            potential_base = match.group(1) # Part before the date pattern
            potential_date_str = match.group(3) # The YYYY_MM_DD part
            try:
                # Validate if the matched string is a real date
                datetime.strptime(potential_date_str, '%Y_%m_%d')
                # If it's a valid date, then it was a date suffix
                base_name = potential_base # Use the part before the date as the base
                existing_date_str = potential_date_str
            except ValueError:
                # Not a valid date, so the underscore and numbers were part of the name.
                # base_name remains name_part_full, existing_date_str remains None.
                pass 
        else: # No date pattern matched at the end (group 2 was None)
            base_name = match.group(1) # This should be name_part_full
            # existing_date_str remains None
            
    return base_name, existing_date_str, ext_part


def process_files_in_directory(directory_path):
    """
    Processes files in a directory:
    1. Adds filename as a header line into the file.
    2. Renames the file to 'BaseName_CreationDate.ext'.
    3. If a file with the target name already exists, merges content and deletes original.
    """
    overall_file_counter = 0 # Counts files encountered by os.walk
    processed_successfully = 0 # Counts files successfully renamed, merged, or confirmed as correct
    files_to_process = []

    # Pass 1: Collect all files to process
    for root, _, files in os.walk(directory_path):
        for filename in files:
            # Prevent the script from processing itself
            if os.path.abspath(os.path.join(root, filename)) == os.path.abspath(__file__):
                print(f"Skipping the script file itself: {os.path.join(root, filename)}")
                continue
            files_to_process.append(os.path.join(root, filename))
            overall_file_counter +=1

    if not files_to_process:
        print(f"No eligible files found in '{directory_path}'.")
        return

    print(f"Found {len(files_to_process)} eligible files to process out of {overall_file_counter} total items scanned.")

    # Pass 2: Process collected files
    for current_iteration_idx, original_filepath in enumerate(files_to_process):
        print(f"\nProcessing file {current_iteration_idx + 1}/{len(files_to_process)}: {original_filepath}")
        original_filename = os.path.basename(original_filepath)
        original_dirname = os.path.dirname(original_filepath)

        # Requirement 2: Add filename as a header line
        filename = f"# {original_filename}\n"
        header_line, ext_part = os.path.splitext(filename)
        current_file_content = "" # To store content for merging if needed
        try:
            with open(original_filepath, 'r', encoding='utf-8') as f:
                current_file_content = f.read()
            
            if not current_file_content.startswith(header_line):
                 with open(original_filepath, 'w', encoding='utf-8') as f:
                    f.write(header_line + "\n" + current_file_content)
                 current_file_content = header_line + current_file_content # Update in-memory version too
                 print(f"Added filename header to: '{original_filename}'")
            else:
                print(f"Filename header already exists in: '{original_filename}'")
                # Ensure current_file_content is the actual content with header
                current_file_content = header_line + current_file_content[len(header_line):] if not current_file_content.startswith(header_line+header_line) else current_file_content


        except PermissionError:
            print(f"  Error: Permission denied when trying to read/write header for: '{original_filename}'. Skipping.")
            continue
        except Exception as e:
            print(f"  Error: Could not add header to '{original_filename}': {e}. Skipping.")
            continue

        # Requirement 3 & 4: Get creation date and determine target filename
        try:
            file_creation_date_obj = get_file_creation_date(original_filepath) # datetime.date object
            file_creation_date_str = file_creation_date_obj.strftime('%Y_%m_%d')

            # Get base name (stripped of old valid date if present) and original extension
            base_name_for_target, _, ext_part = get_base_name_and_ext_from_filename(original_filename)
            
            target_filename = f"{file_creation_date_str}{ext_part}"
            target_filepath = os.path.join(original_dirname, target_filename)

        except Exception as e:
            print(f"  Error: Could not determine target filename for '{original_filename}': {e}. Skipping.")
            continue

        # Requirement 4 & 5: Rename or Merge
        try:
            # Case 1: File is already named correctly
            if os.path.abspath(original_filepath).lower() == os.path.abspath(target_filepath).lower():
                print(f"  Action: File '{original_filename}' is already named correctly. Header processed.")
                processed_successfully += 1
                continue

            # Case 2: Target file exists -> Merge (Requirement 5)
            elif os.path.exists(target_filepath):
                print(f"  Action: Target file '{target_filename}' exists. Merging content from '{original_filename}'.")
                
                with open(target_filepath, 'a', encoding='utf-8') as f_target:
                    merge_marker = (
                        f"\n\n# --- Merged content from: {original_filename} "
                        f"(Source file's creation date: {file_creation_date_str}, " # Date of the content block
                        f"Merge performed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n"
                    )
                    f_target.write(merge_marker)
                    # current_file_content already has the header for original_filename
                    f_target.write(current_file_content) 

                print(f"  Successfully merged content into '{target_filename}'.")
                os.remove(original_filepath)
                print(f"  Deleted original file: '{original_filename}'.")
                processed_successfully += 1
            
            # Case 3: Target does not exist -> Rename (Requirement 4)
            else: 
                os.rename(original_filepath, target_filepath)
                print(f"  Action: Renamed '{original_filename}' to '{target_filename}'.")
                processed_successfully += 1

        except PermissionError as e:
            print(f"  Error: Permission error during rename/merge for '{original_filename}': {e}. File may remain as is.")
        except Exception as e:
            print(f"  Error: Unexpected issue during rename/merge for '{original_filename}': {e}")
            
    print(f"\n--- Script Summary ---")
    print(f"Total eligible files found: {len(files_to_process)}")
    print(f"Successfully processed (header added/verified, and renamed/merged/confirmed): {processed_successfully}")
    print(f"Files skipped due to errors or already being the script: {len(files_to_process) - processed_successfully}")

if __name__ == "__main__":
    target_directory = input("Enter the full directory path to process: ")
    if not os.path.isdir(target_directory):
        print(f"Error: Directory '{target_directory}' not found or is not a directory.")
    else:
        print(f"\nSelected directory: {os.path.abspath(target_directory)}\n")
        print("This script will perform the following actions:")
        print("1. Add a header line (# original_filename) to each file (if not already present).")
        print("2. Rename files to 'BaseName_CreationDate_YYYY_MM_DD.ext'.")
        print("3. If a target dated filename already exists, MERGE the current file's content into it.")
        print("4. Original files WILL BE DELETED after a successful merge.\n")
        
        confirm = input(f"WARNING: This script MODIFIES files and can DELETE files during merges.\n"
                        f"Ensure you have a BACKUP of your data in '{target_directory}' before proceeding.\n"
                        f"Are you absolutely sure you want to continue? (yes/no): ")
        if confirm.lower() == 'yes':
            print("\nStarting file processing...")
            process_files_in_directory(target_directory)
            print("\nFile processing complete.")
        else:
            print("Operation cancelled by the user.")