' ============================================================
' autostart.vbs - Silent wrapper for autostart.ps1
' Called by Task Scheduler at logon (no visible window)
' ============================================================
Dim shell, fso, scriptDir, psScript
Set shell = CreateObject("WScript.Shell")
Set fso   = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript  = scriptDir & "\autostart.ps1"

' 0 = hidden window, False = async (don't wait)
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & psScript & """", 0, False

Set shell = Nothing
Set fso   = Nothing
