# Vergleichsprotokoll - Track A vs B

| Datum | Batch | Track A (HTML) | Track B (Docker) | Abweichung | Entscheidung |
|-------|-------|----------------|------------------|------------|--------------|
| YYYY-MM-DD | 20 PDFs (5 ok, 15 edge) | GRÜN X / ROT Y / GELB Z | GRÜN X / ROT Y / GELB Z | z.B. A GELB, B ROT bei PDF/A-3 |  |
| 2026-09-10 | 5 Kleinbeträge (4 ok, 1 künstl. Fehler: RE-2026-005, MwSt 1,76 statt 0,76 + PDF 4,75 vs XML 5,75) | GRÜN 4 / ROT 1 (v0.1.1 +calccheck) | GRÜN 4 / ROT 1 (+calccheck1) | keine (2 Verfahren je 2x, identisch) | Patch wirkt, beide Tracks fangen beide Fehler |

## Kriterien (Prio 1 Datensicherheit, 2 Zuverlässigkeit)

- [ ] Kein Netz nach Laden (Wireshark)
- [ ] Temp gelöscht nach Batch
- [ ] Hash im Report
- [ ] 200 PDFs <5 Min
- [ ] Jede Datei isoliert (1 kaputte killt nicht Batch)
