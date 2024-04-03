# setup.ps1

# Define the name of the virtual environment directory
$envName = "venv"

# Define the path to the requirements file
$requirementsPath = "requirements.txt"

# Check if the virtual environment directory already exists
if (-Not (Test-Path $envName)) {
    # Create the virtual environment
    python -m venv $envName
}

# Activate the virtual environment
# Note: Adjust the path if you place this script in a different location relative to your project directory
. "$envName/Scripts/Activate.ps1"

# Install packages from requirements.txt
pip install -r $requirementsPath

# Deactivate the virtual environment (optional, since the script will end)
deactivate
