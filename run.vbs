' Firewood Billing — Windows hidden launcher (no console window)
Dim shell
Set shell = CreateObject("WScript.Shell")
shell.Run chr(34) & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\run.bat" & chr(34), 1, True
Set shell = Nothing
