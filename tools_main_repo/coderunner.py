import os
import subprocess

def run_python_code(code, filename="script.py", remove_after_execution=True):

    """

    Write the given Python code to a file and execute it.

    :param code: Python code to be written and executed.

    :param filename: Name of the file where the code will be written.

    :return: Output from the executed Python script.

    """

    # Define the full path for the script, relative to this file's location

    folder_name = 'code_interpreter'

    folder_dir = os.path.join(os.path.dirname(__file__),folder_name)

    script_path = os.path.join(folder_dir ,filename)



    # Create the folder if it doesn't exist

    if not os.path.exists(folder_dir):

        os.makedirs(folder_dir)

    

    # Write the Python code to the file

    with open(script_path, 'w', encoding='utf-8') as file:

        file.write(code)

    

    # Execute the Python script and capture the output

    try:

        result = subprocess.run(['python', script_path], text=True, capture_output=True, check=True)

        output = result.stdout

        print('output:', output)

    except subprocess.CalledProcessError as e:

        output = e.output  # Get the error output if the script fails

    

    # Optionally, clean up by removing the script file after execution
    if remove_after_execution:
        os.remove(script_path)

    

    return output