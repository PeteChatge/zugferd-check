# Vendor - 100% Offline

Kein CDN mehr. Diese Dateien werden lokal ausgeliefert und per `build.py` optional inline gebundled.

- `pdf.min.mjs` 323KB - pdf.js 4.6.82
- `pdf.worker.min.mjs` 1.3MB - Worker
- `jszip.min.js` 96KB - ZIP Export

Lizenz: Apache 2.0 (pdf.js), MIT (JSZip)

Update: Dateien manuell ersetzen + `python build.py` neu laufen lassen. Kein Netz beim Run.
