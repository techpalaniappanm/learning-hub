import os
import shutil

def compare_and_process_dirs(input_dir, output_dir):
    """
    Compares files in input_dir with output_dir and processes them.

    - If a file in input_dir has the same name and size as a file in the
      corresponding location in output_dir, it's deleted from input_dir.
    - If a file in input_dir has a different size, or doesn't exist in
      the corresponding location in output_dir, it's moved to output_dir,
      creating subdirectories as needed.

    Args:
        input_dir (str): The path to the input directory.
        output_dir (str): The path to the output directory.
    """
    print(f"Processing input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    for dirpath, dirnames, filenames in os.walk(input_dir):
        # Create the corresponding subdirectory structure in the output directory
        relative_path = os.path.relpath(dirpath, input_dir)
        output_subdir = os.path.join(output_dir, relative_path)

        if not os.path.exists(output_subdir):
            if relative_path != ".": # Avoid trying to create '.' relative to output_dir
                print(f"Creating directory: {output_subdir}")
                os.makedirs(output_subdir, exist_ok=True)
            else: # Handle the root of the input directory case
                if not os.path.exists(output_dir):
                     print(f"Creating directory: {output_dir}")
                     os.makedirs(output_dir, exist_ok=True)


        for filename in filenames:
            input_file_path = os.path.join(dirpath, filename)
            output_file_path = os.path.join(output_subdir, filename)

            try:
                if os.path.exists(output_file_path):
                    input_file_size = os.path.getsize(input_file_path)
                    output_file_size = os.path.getsize(output_file_path)

                    if input_file_size == output_file_size:
                        # No conflict, same name and size
                        print(f"Deleting (no conflict): {input_file_path}")
                        os.remove(input_file_path)
                    else:
                        # Conflict: same name, different size
                        print(f"Conflict (moving): {input_file_path} -> {output_file_path}")
                        shutil.move(input_file_path, output_file_path)
                else:
                    # File does not exist in output, move it
                    print(f"Moving (new file): {input_file_path} -> {output_file_path}")
                    shutil.move(input_file_path, output_file_path)

            except FileNotFoundError:
                print(f"Skipping (source file moved or deleted): {input_file_path}")
            except Exception as e:
                print(f"Error processing {input_file_path}: {e}")

    print("\nProcessing complete.")
    # Optional: Clean up empty directories in input_dir after processing
    for dirpath, dirnames, filenames in os.walk(input_dir, topdown=False):
        if not dirnames and not filenames:
            try:
                print(f"Removing empty input directory: {dirpath}")
                os.rmdir(dirpath)
            except OSError as e:
                print(f"Error removing directory {dirpath}: {e}")


if __name__ == "__main__":

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Compare two directories and merge into the second one"
    )
    parser.add_argument(
        "input_directory",
        help="Path to the input directory."
    )
    parser.add_argument(
        "output_directory",
        help="Path to the output directory"
    )
    
    args = parser.parse_args()
    # --- End Argument Parsing ---

    if not os.path.isdir(input_directory):
        print(f"Error: Input directory '{input_directory}' does not exist.")
    elif input_directory == output_directory:
        print("Error: Input and output directories cannot be the same.")
    else:
        compare_and_process_dirs(input_directory, output_directory)