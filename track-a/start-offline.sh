#!/bin/bash
# Startet Track A 100% offline via localhost
echo "Starte ZUGFeRD Check offline auf http://localhost:8000/zugferd-check.offline.html"
python3 -m http.server 8000
