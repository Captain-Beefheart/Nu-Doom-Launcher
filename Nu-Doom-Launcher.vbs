' Nu-Doom-Launcher.vbs — double-click to open the Nu-Doom Launcher.
' Runs the app with pythonw (no console window appears — just the app window).
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir

pythonw = "C:\msys64\mingw64\bin\pythonw.exe"
If Not fso.FileExists(pythonw) Then pythonw = "pythonw.exe"  ' fall back to PATH

sh.Run """" & pythonw & """ """ & dir & "\nu_doom_launcher.pyw""", 0, False
