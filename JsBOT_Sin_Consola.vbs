' ==============================================================================
' Lanzador Silencioso (Sin Ventana CMD) — JsBOT RPA
' ==============================================================================
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Ejecutar pythonw para lanzar la interfaz gráfica sin terminal de fondo
Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")

Dim pyCmd
pyCmd = "pythonw main.py"
WshShell.Run pyCmd, 0, False

Set WshShell = Nothing
Set fso = Nothing
