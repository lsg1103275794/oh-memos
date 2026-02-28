' ============================================================
' autostart.vbs — 让 autostart.ps1 完全静默运行（无任何窗口）
' 由 Task Scheduler 调用此文件
' ============================================================
Dim shell
Set shell = CreateObject("WScript.Shell")

' 获取脚本所在目录
Dim fso, scriptDir
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Dim psScript
psScript = scriptDir & "\autostart.ps1"

' 0 = 完全隐藏窗口, False = 不等待完成（异步）
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & psScript & """", 0, False

Set shell = Nothing
Set fso = Nothing
