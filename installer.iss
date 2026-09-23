[Setup]
AppName=Agentica AI Browser
AppVersion=1.0
AppPublisher=Agentica
DefaultDirName={localappdata}\Agentica
DefaultGroupName=Agentica
OutputDir=Output
OutputBaseFilename=Agentica_Setup_v1.0
SetupIconFile=agentica.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
DisableWelcomePage=no
WizardStyle=modern

[Files]
; Only package the lightweight source code and icons. 
; Do NOT package the heavy bin/ or venv/ folders.
Source: "src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "agentica.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "rcedit-x64.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "deep_patch.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup_dependencies.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Creates Desktop and Start Menu Shortcuts pointing directly to agentica.exe
Name: "{autoprograms}\Agentica"; Filename: "{app}\bin\chromium-1234\chrome-win64\agentica.exe"; Parameters: "--user-data-dir=""{app}\data\profiles\human"" --remote-debugging-port=9222 --restore-last-session --no-default-browser-check --start-maximized --disable-session-crashed-bubble --hide-crash-restore-bubble"; WorkingDir: "{app}\bin\chromium-1234\chrome-win64"; IconFilename: "{app}\agentica.ico"
Name: "{autodesktop}\Agentica"; Filename: "{app}\bin\chromium-1234\chrome-win64\agentica.exe"; Parameters: "--user-data-dir=""{app}\data\profiles\human"" --remote-debugging-port=9222 --restore-last-session --no-default-browser-check --start-maximized --disable-session-crashed-bubble --hide-crash-restore-bubble"; WorkingDir: "{app}\bin\chromium-1234\chrome-win64"; IconFilename: "{app}\agentica.ico"

[Run]
; Runs the smart dependency checker after the files are extracted
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\setup_dependencies.ps1"""; Description: "Downloading browser dependencies (skips if already installed)..."; Flags: postinstall waituntilterminated

[UninstallDelete]
; Ensures completely clean uninstallation, removing the downloaded binaries and isolated python environments
Type: filesandordirs; Name: "{app}\bin"
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}\src\__pycache__"
Type: files; Name: "{app}\Agentica.bat"
