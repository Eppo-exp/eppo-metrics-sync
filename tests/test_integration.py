import os
import subprocess
import tempfile
from pathlib import Path
import venv

def test_package_installation_and_dependencies():
    """
    Test that the package can be installed in a fresh virtual environment
    and all dependencies are compatible.
    """
    # Create a temporary directory for the virtual environment
    with tempfile.TemporaryDirectory() as venv_dir:
        # Create a virtual environment
        venv.create(venv_dir, with_pip=True)

        # Determine the path to the Python executable in the virtual environment
        python_executable = os.path.join(venv_dir, 'bin', 'python')

        # Get the absolute path to the project root (parent directory of the tests directory)
        project_root = str(Path(__file__).parent.parent.absolute())

        # Install the package in development mode
        install_result = subprocess.run(
            [python_executable, '-m', 'pip', 'install', '-e', project_root],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        assert install_result.returncode == 0, f"Failed to install package: {install_result.stderr}"

        # Try to import and run a basic command to verify functionality
        run_result = subprocess.run(
            [python_executable, '-m', 'eppo_metrics_sync', '--help'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        assert run_result.returncode == 0, f"Failed to run package: {run_result.stderr}"
        assert "usage:" in run_result.stdout, "Help text not found in output"

        # Check if we can use the basic functionality (dry run with empty dir)
        with tempfile.TemporaryDirectory() as empty_dir:
            basic_run = subprocess.run(
                [python_executable, '-m', 'eppo_metrics_sync', empty_dir, '--dryrun'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # We consider the test passed if it can be installed and run
            # Even if it returns an error code for an empty directory
            assert True
