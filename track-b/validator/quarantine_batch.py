#!/usr/bin/env python3
"""
Batch-Quarantäne Track B - 100% offline, ohne Docker nötig.

Prüft einen lokalen Ordner mit ZUGFeRD-PDFs. Bei Status ROT wird eine Kopie
der kaputten Datei plus Kommentar gleichen Stamens (.md) in einem extra
Ordner abgelegt (Standard: <src>/fehler/).

Der fehler-Ordner wird LAZY angelegt: nur wenn der erste Fehler abgelegt
werden muss. Bei 0 Fehlern entsteht kein Ordner.

Usage:
  python quarantine_batch.py <src-ordner> [--fehler-name fehler] [--rekursiv]

Benötigt: flask, pypdf (siehe Dockerfile).
"""
import argparse
import io
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import server as S  # noqa: E402 - gleicher Codepfad wie POST /validate


def iter_pdfs(src, rekursiv, fehler_dir):
    src_p = pathlib.Path(src)
    pattern = "**/*.pdf" if rekursiv else "*.pdf"
    fehler_resolved = pathlib.Path(fehler_dir).resolve()
    for p in sorted(src_p.glob(pattern)):
        # Quarantäne-Ordner selbst nie erneut prüfen
        try:
            if fehler_resolved in p.resolve().parents or p.resolve() == fehler_resolved:
                continue
        except OSError:
            continue
        if p.is_file():
            yield p


def main():
    ap = argparse.ArgumentParser(description="ZUGFeRD-Ordner prüfen + kaputte Dateien quarantänisieren")
    ap.add_argument("src", help="Lokaler Ordner mit ZUGFeRD-PDFs")
    ap.add_argument("--fehler-name", default="fehler", help="Name des Extra-Ordners (Default: fehler)")
    ap.add_argument("--rekursiv", action="store_true", help="Unterordner einbeziehen")
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    if not src.is_dir():
        print(f"Fehler: kein Ordner: {src}", file=sys.stderr)
        return 2
    fehler_dir = src / args.fehler_name
    if fehler_dir.exists() and not fehler_dir.is_dir():
        print(f"Fehler: {fehler_dir} existiert und ist kein Ordner", file=sys.stderr)
        return 2

    client = S.app.test_client()
    total = gruen = rot = gelb = 0
    abgelegt = []
    for pdf_path in iter_pdfs(src, args.rekursiv, fehler_dir):
        total += 1
        data = pdf_path.read_bytes()
        r = client.post("/validate", data={"file": (io.BytesIO(data), pdf_path.name)})
        j = r.get_json()
        status = j.get("status", "ROT")
        if status == "GRÜN":
            gruen += 1
        elif status == "GELB":
            gelb += 1
        else:
            rot += 1
        # Lazy: quarantine_if_rot erstellt fehler_dir nur im ROT-Fall
        pdf_out, md_out = S.quarantine_if_rot(
            pdf_bytes=data, filename=pdf_path.name,
            result_json=j, fehler_dir=str(fehler_dir))
        if pdf_out:
            abgelegt.append((pdf_path.name, pdf_out, md_out))
        print(f"{status:4}  {pdf_path.name}")

    print(f"\nGeprüft: {total} | GRÜN {gruen} | GELB {gelb} | ROT {rot}")
    if abgelegt:
        print(f"Quarantäne: {fehler_dir} ({len(abgelegt)} Datei(en) + Kommentar je .md)")
        for name, pp, mm in abgelegt:
            print(f"  - {name}\n      {pp}\n      {mm}")
    else:
        print("Quarantäne: kein Ordner angelegt (kein Fehler).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
