@echo off
setlocal
chcp 65001 >NUL
python "%~dp0mock_usi.py"
endlocal
