Option Explicit

Dim shell, fso, scriptDir, buildScript, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
buildScript = fso.BuildPath(scriptDir, "build_windows.bat")

If Not fso.FileExists(buildScript) Then
  MsgBox "build_windows.bat wurde nicht gefunden. Bitte ZIP komplett entpacken.", vbCritical, "DATEV Build"
  WScript.Quit 1
End If

cmd = "cmd.exe /d /k """ & buildScript & """"
shell.Run cmd, 1, False
