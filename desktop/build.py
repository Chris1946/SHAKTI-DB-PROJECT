import os
import subprocess
import sys

def build():
    """
    Local build script wrapping PyInstaller to create the PulseTrace Desktop App.
    Run this script from the root repository folder:
        python desktop/build.py
    """
    print("Building PulseTrace Desktop App with PyInstaller...")

    # Ensure we are in the repository root
    if not os.path.isdir("desktop") or not os.path.isdir("backend"):
        print("Error: Please run this script from the root repository folder.")
        sys.exit(1)

    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        import PyInstaller.__main__

    # Run PyInstaller
    PyInstaller.__main__.run([
        'desktop/main.py',
        '--name=PulseTrace',
        '--windowed',
        '--onedir',
        '--noconfirm',
        '--clean'
    ])

    print("\nBuild complete!")
    print(f"Executables can be found in the 'dist/PulseTrace' folder.")

if __name__ == '__main__':
    build()
