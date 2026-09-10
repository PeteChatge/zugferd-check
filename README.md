# ZUGFeRD Check - Dual-Track

> Sorgfalt > Speed. Datensicherheit Prio 1, Zuverlässigkeit Prio 2.

Rechnungen aus Selectline (PDF mit ZUGFeRD) batch-weise prüfen - 100% offline.

## Entscheidung beim Test: Track A vs Track B

| Track | Architektur | Datensicherheit | Zuverlässigkeit | Verteilung |
|-------|-------------|-----------------|-----------------|------------|
| **A** | Single-File HTML `zugferd-check.html` - alles im Browser (pdf.js + xmllint-wasm + KoSIT XSLT) | maximal (Dateien verlassen nie den Rechner) | ~98% (JS, nicht 1:1 KoSIT) | 1 Datei per USB/Share |
| **B** | Docker Compose: `validator` (Java/Mustang+KoSIT) + `webapp` + nginx | hoch (on-premise, kein Internet) | 100% Referenz | Docker Image |

Beide Tracks validieren identische Stufen:
1. PDF/A-3 + Embedded XML vorhanden?
2. XML wohlgeformt + XSD valide?
3. EN16931 / ZUGFeRD Schematron valide?
4. (V2) PDF Sicht vs XML Summen

Toleranz: PDF/A-3 Fehler = GELB, XML/Schematron = ROT.

## Projektstruktur

```
track-a/  zugferd-check.html  <- kompakt, Doppelklick, offline
track-b/  docker-compose.yml + validator/ + webapp/
test-data/  echte Selectline PDFs hier ablegen (nicht im Git)
docs/  vergleichs-protokoll.md
```

## Schnellstart

**Track A:** `track-a/zugferd-check.html` im Browser öffnen (Chrome/Edge), Ordner reinziehen.

**Track B:** `cd track-b && docker compose up --build` -> http://localhost:8080

## Test-Harness

Gleichen Ordner durch A und B jagen, CSV vergleichen. Version/Regelstand wird in jedem Report geloggt.

## Leitplanken (aus Grilling Q1-Q25)

- 1-3 Nutzer, 50-200 PDFs/Batch, 300/1GB Limit
- Parallel 4 Worker, SSE Fortschritt, jede Datei isoliert
- Temp nur RAM/isoli. Dir, sofort löschen + 1h Cron
- Audit-Log nur Hash/Name/Ergebnis, 90 Tage
- HTTPS + Minimal-Auth auch intern
