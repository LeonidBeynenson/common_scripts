FOR /F "tokens=* USEBACKQ" %%F IN (`C:\cygwin64\bin\cygpath.exe -w -a ~/`) DO (SET myhomepath=%%F)
ECHO %myhomepath%
%myhomepath%\bin\run_winlogger.bat
