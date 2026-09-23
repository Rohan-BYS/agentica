import os
import time
from pathlib import Path

def patch_file(file_path: Path):
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
        
    print(f"Patching {file_path.name}...")
    data = file_path.read_bytes()
    orig_len = len(data)
    
    # 1. Wide string replacements (UTF-16LE)
    # "Google Chrome for Testing" (25 chars) -> "Agentica" + 17 spaces
    w_old_1 = "Google Chrome for Testing".encode("utf-16le")
    w_new_1 = "Agentica                 ".encode("utf-16le")
    assert len(w_old_1) == len(w_new_1)
    
    count_w1 = data.count(w_old_1)
    data = data.replace(w_old_1, w_new_1)
    
    # "Chrome for Testing" (18 chars) -> "Agentica" + 10 spaces
    w_old_2 = "Chrome for Testing".encode("utf-16le")
    w_new_2 = "Agentica          ".encode("utf-16le")
    assert len(w_old_2) == len(w_new_2)
    
    count_w2 = data.count(w_old_2)
    data = data.replace(w_old_2, w_new_2)
    
    # 2. ASCII / UTF-8 replacements
    a_old_1 = b"Google Chrome for Testing"
    a_new_1 = b"Agentica                 "
    count_a1 = data.count(a_old_1)
    data = data.replace(a_old_1, a_new_1)
    
    a_old_2 = b"Chrome for Testing"
    a_new_2 = b"Agentica          "
    count_a2 = data.count(a_old_2)
    data = data.replace(a_old_2, a_new_2)
    
    assert len(data) == orig_len, f"File size changed for {file_path.name}!"
    file_path.write_bytes(data)
    print(f"  Patched {file_path.name}: {count_w1} w1, {count_w2} w2, {count_a1} a1, {count_a2} a2")

def main():
    # Kill any running agentica or chrome
    os.system("taskkill /F /IM agentica.exe /T >nul 2>&1")
    os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
    time.sleep(1.5)
    
    # Patch dynamically in local directory, AppData, and workspace
    dirs = [
        Path(__file__).parent / "bin" / "chromium-1234" / "chrome-win64",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Agentica" / "bin" / "chromium-1234" / "chrome-win64",
        Path(r"C:\Users\U1\Desktop\ai-browser-workspace\ai-browser\bin\chromium-1234\chrome-win64")
    ]
    
    for d in dirs:
        if d.exists():
            print(f"\n=== Patching directory: {d} ===")
            patch_file(d / "agentica.exe")
            patch_file(d / "chrome.dll")
            if (d / "locales" / "en-US.pak").exists():
                patch_file(d / "locales" / "en-US.pak")

if __name__ == "__main__":
    main()
