import PyInstaller.__main__
import sys

def build():
    print("Starting build process...")
    try:
        PyInstaller.__main__.run([
            'main.py',
            '--name=%s' % 'PDF Book Reader',
            '--windowed',
            '--onefile',
            '--clean',
            '--noconfirm',
        ])
        print("Build completed successfully. Check the 'dist' folder for the .exe file.")
    except Exception as e:
        print(f"Error during build: {e}")

if __name__ == "__main__":
    build()
