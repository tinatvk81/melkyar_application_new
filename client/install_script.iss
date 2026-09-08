; اسکریپت Inno Setup برای ساخت نصب‌کننده‌ی ویندوزی سامانه‌ی مدیریت فایل‌های ملکی
; پیش‌نیاز: Inno Setup را از https://jrsoftware.org/isdl.php نصب کنید (رایگان).
; قبل از اجرای این اسکریپت، حتماً اول pyinstaller build_client.spec را زده باشید
; تا dist\RealEstateApp.exe ساخته شده باشد.
;
; اجرا: این فایل را در Inno Setup Compiler باز کنید و Build > Compile بزنید،
; یا از خط فرمان: ISCC.exe install_script.iss

#define MyAppName "سامانه مدیریت فایل‌های ملکی"
#define MyAppVersion "1.0.0"
#define MyAppExeName "RealEstateApp.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\MelkYar
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=RealEstateApp-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
; برنامه دسکتاپ ساده است؛ نیازی به دسترسی مدیر سیستم ندارد مگر در پوشه‌ی Program Files نصب شود
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "ساخت آیکون روی دسکتاپ"; GroupDescription: "آیکون‌های اضافی:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; اگر config.py یا settings.json پیش‌فرضی می‌خواهید همراه نصب باشد، این‌جا اضافه کنید:
; Source: "settings.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "اجرای برنامه"; Flags: nowait postinstall skipifsilent
