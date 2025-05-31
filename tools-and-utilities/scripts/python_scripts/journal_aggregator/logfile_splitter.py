import re
import argparse # Import the argparse module
from datetime import datetime

def process_log_file(input_filepath, user_info):
    """
    Reads a log file, splits content based on date lines, and writes segments to new files.

    Each new file is named after the date found (YYYY_MM_DD.md) and includes:
    1. The original date line.
    2. User-provided information.
    3. The new filename.
    4. The content lines that followed the date line in the input file until the next date.
    """
    # Regex to find lines starting with a date like [YYYY-MM-DD HH:MM:SS]
    # It captures the YYYY-MM-DD part in group 1.
    # Allows for optional milliseconds like .123
    date_pattern = r"\[(\d{1,2})/(\d{1,2})/(\d{2}),\s*(\d{1,2}:\d{2}:\d{2})\s*(AM|PM)\].*"

    current_output_file_handler = None
    current_output_filename = None
    lines_for_current_segment = []

    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile:
            for line in infile:
                print(f"read {line}")
                match = re.search(date_pattern, line) # Check if the line starts with the date pattern
                print(f"Line matched {line} {match}")

                if match:
                    # A new date segment has begun.
                    # If there's an existing segment, write its collected lines and close its file.
                    if current_output_file_handler:
                        for content_line in lines_for_current_segment:
                            current_output_file_handler.write(content_line)
                        current_output_file_handler.close()
                        print(f"✅ Finished writing to {current_output_filename}")
                        lines_for_current_segment = [] # Reset for the new segment

                    # --- START DEBUGGING PRINTS ---
                    print(f"DEBUG: Group 1 (month_str)    = '{match.group(1)}'")
                    print(f"DEBUG: Group 2 (day_str)       = '{match.group(2)}'")
                    print(f"DEBUG: Group 3 (year_short_str)= '{match.group(3)}'")
                    print(f"DEBUG: Group 4 (time_str)      = '{match.group(4)}'")
                    print(f"DEBUG: Group 5 (ampm_str)      = '{match.group(5)}'")
                    # --- END DEBUGGING PRINTS ---

                    month_str = match.group(1)
                    day_str = match.group(2)
                    year_short_str = match.group(3)
                    time_str = match.group(4)
                    ampm_str = match.group(5)

                    # Ensure this line is exactly as follows:
                    datetime_str_to_parse = f"{month_str}/{day_str}/{year_short_str} {time_str} {ampm_str}"
                    
                    print(f"DEBUG: datetime_str_to_parse = '{datetime_str_to_parse}'") # Debug print for the string to be parsed

                    # --- Start processing the new date segment ---
                    date_str_for_filename = match.group(3) + '-' + match.group(1) + '-' + match.group(2) # This is "YYYY-MM-DD"

                    try:
                        # Create the output filename e.g., YYYY_MM_DD.txt
                        dt_obj = datetime.strptime(date_str_for_filename, "%Y-%m-%d")
                        output_filename_base = dt_obj.strftime("%Y_%m_%d")
                        current_output_filename = f"{output_filename_base}.md"
                    except ValueError:
                        print(f"⚠️ Warning: Could not parse date '{date_str_for_filename}' from line: {line.strip()}")
                        print("Skipping this segment.")
                        current_output_file_handler = None # Ensure no file is processed for this bad date
                        lines_for_current_segment = []
                        continue # Move to the next line in the input file

                    # Open the new output file
                    try:
                        current_output_file_handler = open(current_output_filename, 'w', encoding='utf-8')
                        print(f"🆕 Creating and writing to file: {current_output_filename}")

                        # 1. Write the original date line that started this segment
                        current_output_file_handler.write(line) # 'line' includes its original newline

                        # 2. Write the user information
                        current_output_file_handler.write(f" {user_info}: ")

                        # 3. Write the filename
                        current_output_file_handler.write(f" {current_output_filename}: ")

                        # Subsequent lines will be collected in lines_for_current_segment

                    except IOError as e:
                        print(f"❌ Error opening or writing initial header to {current_output_filename}: {e}")
                        current_output_file_handler = None # Prevent further writes if open/header write failed
                        lines_for_current_segment = []
                        # Attempt to continue to the next date segment if possible

                elif current_output_file_handler:
                    # This line is not a date line, and we have an active output file.
                    # So, it's content for the current segment.
                    lines_for_current_segment.append(line)

            # End of input file. If there's an open segment, write its lines and close the file.
            if current_output_file_handler:
                if lines_for_current_segment:
                    for content_line in lines_for_current_segment:
                        current_output_file_handler.write(content_line)
                current_output_file_handler.close()
                print(f"✅ Finished writing to {current_output_filename} (End of Input File)")

    except FileNotFoundError:
        print(f"❌ Error: Input file '{input_filepath}' not found.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        # Ensure the very last file is closed if an error broke the loop unexpectedly
        # and it was still open.
        if current_output_file_handler and not current_output_file_handler.closed:
            current_output_file_handler.close()
            print(f"⚠️ Force-closed {current_output_filename} due to script end or error.")

if __name__ == "__main__":
    print("📄 Log File Processor")
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Processes a log file, splits its content based on date lines, "
                    "and writes segments to new files named after the dates. Each "
                    "output file includes the original date line, user information, "
                    "the new filename, and subsequent content."
    )
    parser.add_argument(
        "input_filepath",
        help="Path to the input log file."
    )
    parser.add_argument(
        "user_info",
        help="User information string to include in the header of output files."
    )
    
    args = parser.parse_args()
    # --- End Argument Parsing ---

    print("📄 Log File Processor")
    # Call the main processing function with arguments from the command line
    process_log_file(args.input_filepath, args.user_info)
    print("🏁 Processing complete.")