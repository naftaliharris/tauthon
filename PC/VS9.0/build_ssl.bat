@echo off
if not defined HOST_PYTHON (
  if %1 EQU Debug (
    set HOST_PYTHON=tauthon_d.exe
    if not exist tauthon28_d.dll exit 1
  ) ELSE (
    set HOST_PYTHON=tauthon.exe
    if not exist tauthon28.dll exit 1
  )
)
%HOST_PYTHON% build_ssl.py %1 %2 %3

