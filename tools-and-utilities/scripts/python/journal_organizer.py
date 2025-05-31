import os
import shutil
import re

def organize_and_merge_files_by_date():
    """
    Organizes files from an input directory to an output directory
    based on dates found in the filenames. If a file with the
    same name already exists in the destination, it attempts to
    merge by appending content (suitable for text files).
    """
    # 1. Get input directory from user
    input_dir = input("Enter the path to the input directory: ")
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' not found.")
        return

    # 3. Get output directory from user
    output_dir = input("Enter the path to the output directory: ")
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"Output directory '{output_dir}' created.")
        except OSError as e:
            print(f"Error: Could not create output directory '{output_dir}': {e}")
            return

    print(f"\nScanning files in '{input_dir}'...")
    print("IMPORTANT: Content merging is done by appending. This is suitable for text files.")
    print("For binary files (images, docs, etc.), this may lead to corruption.\n")

    moved_files_count = 0
    merged_files_count = 0
    skipped_files_count = 0

    # Iterate over files in the input directory
    for filename in os.listdir(input_dir):
        original_filepath = os.path.join(input_dir, filename)

        # Skip if it's a directory
        if os.path.isdir(original_filepath):
            continue

        # 2. Look for file name with date format YYYY_MM_DD and parse it
        match = re.search(r'(\d{4})_(\d{2})_(\d{2})', filename)

        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            date_str = f"{year}_{month}_{day}"

            _, extension = os.path.splitext(filename)
            year_folder = os.path.join(output_dir, year)
            new_filename = f"{date_str}{extension}"
            new_filepath = os.path.join(year_folder, new_filename)

            try:
                # Create the YYYY directory if it doesn't exist
                if not os.path.exists(year_folder):
                    os.makedirs(year_folder)
                    print(f"Created directory: '{year_folder}'")

                # Check if the destination file already exists
                if os.path.exists(new_filepath):
                    print(f"Merging: '{filename}' into existing '{new_filepath}'")
                    try:
                        # Append content from original_filepath to new_filepath
                        with open(new_filepath, 'a+', encoding='utf-8') as dest_file: 
                            with open(original_filepath, 'r', encoding='utf-8') as src_file:
                                # Add a newline if the destination file is not empty
                                # and doesn't already end with a newline
                                dest_file.seek(0, os.SEEK_END) # Go to end of file
                                if dest_file.tell() > 0: # If file is not empty
                                    dest_file.seek(dest_file.tell() - 1, os.SEEK_SET) # Go to last char
                                    if dest_file.read(1) != '\n':
                                        dest_file.write('\n') # Add a newline if not present

                                
                                content_to_append = src_file.read()
                                dest_file.write(content_to_append)

                            # If merging was successful, remove the original file
                            os.remove(original_filepath)
                            print(f"Merged and removed original: '{filename}'")
                            merged_files_count += 1
                    except Exception as merge_error:
                        print(f"Error merging file '{filename}': {merge_error}")
                        skipped_files_count += 1
                else:
                    # Move the file if it doesn't exist in the destination
                    shutil.move(original_filepath, new_filepath)
                    print(f"Moved: '{filename}' to '{new_filepath}'")
                    moved_files_count += 1

            except Exception as e:
                print(f"Error processing file '{filename}': {e}")
                skipped_files_count += 1
        else:
            print(f"Skipped: '{filename}' (date not found or incorrect format).")
            skipped_files_count += 1

    print("\n--- Summary ---")
    print(f"Successfully moved new files: {moved_files_count}")
    print(f"Successfully merged files: {merged_files_count}")
    print(f"Skipped files (due to errors or no date): {skipped_files_count}")
    print("File organization complete. ✨")

if __name__ == "__main__":
    organize_and_merge_files_by_date()