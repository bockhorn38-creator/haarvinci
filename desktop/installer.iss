#define MyAppVersion "0.6.0"
[Setup]
AppId={{F9F17449-8F18-43A9-A062-6932DF0902EF}
AppName=Haarvinci
AppVersion={#MyAppVersion}
AppPublisher=Haarvinci
DefaultDirName={localappdata}\Programs\Haarvinci
DefaultGroupName=Haarvinci
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\dist\installer
OutputBaseFilename=Haarvinci-Windows-Setup-{#MyAppVersion}
SetupIconFile=assets\haarvinci.ico
UninstallDisplayIcon={app}\Haarvinci.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
[Tasks]
Name: "desktopicon"; Description: "Symbol auf dem Desktop erstellen"; GroupDescription: "Verknüpfungen:"
[Files]
Source: "..\dist\Haarvinci\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Haarvinci"; Filename: "{app}\Haarvinci.exe"
Name: "{autodesktop}\Haarvinci"; Filename: "{app}\Haarvinci.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\Haarvinci.exe"; Description: "Haarvinci jetzt starten"; Flags: nowait postinstall skipifsilent
