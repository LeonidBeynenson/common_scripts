call C:\ProgramData\Anaconda3\condabin\conda.bat activate p39
FOR /F "tokens=* USEBACKQ" %%F IN (`C:\cygwin64\bin\cygpath.exe -w -a ~/`) DO (SET myhomepath=%%F)
ECHO %myhomepath%
call python %myhomepath%\bin\windows_logger3.py
