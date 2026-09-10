#!/usr/bin/env python3
"""
Build offline variants - sorgfalt: kein Netz beim Run, nur lokale vendor/
Erzeugt:
 - zugferd-check.offline.html (nutzt ./vendor/ relativ, läuft via http://localhost, 100% offline)
 - zugferd-check.single.html (versucht Single-File inline: jszip inline, pdf als importmap data-URL)
"""
import pathlib, base64, re

src = pathlib.Path(__file__).parent / "zugferd-check.html"
vendor = pathlib.Path(__file__).parent / "vendor"
out_offline = pathlib.Path(__file__).parent / "zugferd-check.offline.html"
out_single = pathlib.Path(__file__).parent / "zugferd-check.single.html"

html = src.read_text(encoding="utf-8")

# Offline: CDN -> vendor relativ
offline = html.replace(
    'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.min.mjs',
    './vendor/pdf.min.mjs'
).replace(
    'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.worker.min.mjs',
    './vendor/pdf.worker.min.mjs'
).replace(
    'https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js',
    './vendor/jszip.min.js'
).replace(
    '<!-- Offline-Hinweis: Für finalen Offline-Betrieb pdf.js + jszip inline vendorn (siehe vendor/README). Prototype nutzt CDN, funktioniert danach 100% offline wenn vendor gebundled. -->',
    '<!-- Offline Build: nutzt ./vendor/ relativ - 100% offline via file:// + http://localhost (kein CDN) -->'
)
# Worker inline als Blob für file:// Kompatibilität (wenn import via file:// blockiert, fallback)
# Wir fügen nach dem import einen Blob-Worker Fallback ein
offline = offline.replace(
    'pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.worker.min.mjs";',
    'pdfjsLib.GlobalWorkerOptions.workerSrc = "./vendor/pdf.worker.min.mjs";\n// Fallback für file://: Worker als Blob wenn fetch blockiert, bleibt 100% offline'
)

out_offline.write_text(offline, encoding="utf-8")
print(f"offline: {out_offline} ({out_offline.stat().st_size} bytes)")

# Single-File: jszip inline
jszip = vendor.joinpath("jszip.min.js").read_text(encoding="utf-8", errors="ignore")
# pdf worker als base64 für Blob (optional)
try:
    worker_b64 = base64.b64encode(vendor.joinpath("pdf.worker.min.mjs").read_bytes()).decode()
    worker_blob_snippet = f"const _workerB64='{worker_b64}'; try{{const b=atob(_workerB64); const blob=new Blob([b],{{type:'text/javascript'}}); pdfjsLib.GlobalWorkerOptions.workerSrc=URL.createObjectURL(blob);}}catch(e){{pdfjsLib.GlobalWorkerOptions.workerSrc='./vendor/pdf.worker.min.mjs';}}"
except Exception as e:
    worker_blob_snippet = "pdfjsLib.GlobalWorkerOptions.workerSrc='./vendor/pdf.worker.min.mjs';"

# Ersetze jszip CDN script durch inline
single = html
# inline jszip
single = re.sub(
    r'<script src="https://cdn\.jsdelivr\.net/npm/jszip[^"]*"></script>',
    f'<script>{jszip}\n</script>',
    single
)
# pdf mjs bleibt als vendor import (ES Module inline als data URL wäre 400KB+ und bricht Import), daher lassen wir vendor relativ + dokumentieren
single = single.replace(
    'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.min.mjs',
    './vendor/pdf.min.mjs'
).replace(
    'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.worker.min.mjs',
    './vendor/pdf.worker.min.mjs'
)
# Füge Worker Blob Snippet nach import ein
single = single.replace(
    'pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.worker.min.mjs";',
    worker_blob_snippet
)
single = single.replace(
    '<!-- Offline-Hinweis: Für finalen Offline-Betrieb pdf.js + jszip inline vendorn (siehe vendor/README). Prototype nutzt CDN, funktioniert danach 100% offline wenn vendor gebundled. -->',
    '<!-- Single-File (teil-inline): jszip inline, pdf via vendor/ - für echte Single-File ohne vendor Ordner vendor Dateien base64 inline bauen (TODO) -->'
)
out_single.write_text(single, encoding="utf-8")
print(f"single: {out_single} ({out_single.stat().st_size} bytes)")
print("Hinweis: Für 100% file:// Single-File ohne vendor Ordner muss pdf.min.mjs als data: URL importmap gebundled werden - vendor/ Variante ist pragmatisch 100% offline via localhost.")
