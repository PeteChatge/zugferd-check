# Test-Daten

Lege hier echte Selectline PDFs ab (nicht ins Git committen!).

```
test-data/
  ok/          <- 5-10 korrekte Rechnungen
  fehler/      <- bewusst fehlerhafte (ohne USt, Rundungsfehler, ohne XML)
  real-batch/  <- 1 echter Tages-Batch (50-200 PDFs)
```

## Vergleich Track A vs B

Beide Tracks mit gleichem Ordner füttern, CSVs vergleichen:

```bash
# Track A: im Browser öffnen, Ordner droppen, CSV speichern -> track-a.csv
# Track B: curl
for f in test-data/real-batch/*.pdf; do curl -s -F file=@$f http://localhost:8081/validate; done | jq
```

Erwarte: Bei 98% gleiche Ampel. Differenzen dokumentieren in `docs/vergleichs-protokoll.md`.
