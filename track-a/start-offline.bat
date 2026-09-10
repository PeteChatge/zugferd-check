@echo off
REM Startet Track A 100%% offline via localhost - kein Internet
REM Datensicherheit: kein Upload, alles im Browser
echo Starte ZUGFeRD Check offline auf http://localhost:8000/zugferd-check.offline.html
start http://localhost:8000/zugferd-check.offline.html
python -m http.server 8000
