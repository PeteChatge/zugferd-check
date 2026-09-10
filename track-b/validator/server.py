#!/usr/bin/env python3
"""
Validator Track B - gepatcht 2026-09-10:
- Echte XML-Extraktion via pypdf Attachments (statt Regex auf Rohbytes;
  Streams sind Flate-komprimiert, Dateiname oktal-escapet -> Regex war blind).
- Keine 5000-Zeichen-Trunkierung mehr (Summen stehen am XML-Ende).
- Rechenprüfung (BT-117, Summenkette, Zeilensumme, Due) + PDF-Sicht vs XML.
- XSD-Formatfehler bleiben ROT; Rechenfehler sind ROT, nie GELB.
API zu /validate und /health bleibt kompatibel. 100% offline, jede Datei isoliert.
Benötigt: pip install flask pypdf
"""
from flask import Flask, request, jsonify
import hashlib, os, re, io, xml.etree.ElementTree as ET

try:
    from pypdf import PdfReader
except ImportError:  # Fallback für alte Umgebungen
    from PyPDF2 import PdfReader  # type: ignore

app = Flask(__name__)
RULES_VERSION = os.environ.get("RULES_VERSION", "ZUGFeRD_2.3_EN16931_2024+calccheck1")
TOL = 0.02  # €-Toleranz (1 Cent Rundung + Float)
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
NS = {"ram": RAM}


def sha256_8(b): return hashlib.sha256(b).hexdigest()[:16]


def _num(t):
    if t is None:
        return None
    try:
        v = float(str(t).strip().replace(",", "."))
        return v if v == v else None  # NaN abfangen
    except (ValueError, AttributeError):
        return None


def _child_text(parent, local):
    if parent is None:
        return None
    for ch in list(parent):
        tag = ch.tag or ""
        if tag == local or tag.endswith("}" + local) or tag.endswith(":" + local):
            return _num(ch.text)
    return None


def _find_all(root, local):
    return [el for el in root.iter() if (el.tag or "").endswith("}" + local) or (el.tag or "").endswith(":" + local) or el.tag == local]


def header_sums(root):
    blocks = _find_all(root, "SpecifiedTradeSettlementHeaderMonetarySummation")
    if not blocks:
        return {}
    b = blocks[0]
    return {
        "line": _child_text(b, "LineTotalAmount"),
        "basis": _child_text(b, "TaxBasisTotalAmount"),
        "tax": _child_text(b, "TaxTotalAmount"),
        "grand": _child_text(b, "GrandTotalAmount"),
        "prepaid": _child_text(b, "TotalPrepaidAmount"),
        "due": _child_text(b, "DuePayableAmount"),
    }


def header_tax_groups(root):
    settlements = _find_all(root, "ApplicableHeaderTradeSettlement")
    scope = settlements[0] if settlements else root
    groups = []
    for t in _find_all(scope, "ApplicableTradeTax"):
        # Nur Header-Steuern (mit BasisAmount) werten, keine Zeilensteuern
        basis = _child_text(t, "BasisAmount")
        calc = _child_text(t, "CalculatedAmount")
        rate = _child_text(t, "RateApplicablePercent")
        if basis is not None or calc is not None:
            groups.append({"basis": basis, "calc": calc, "rate": rate})
    return groups


def line_totals(root):
    out = []
    for item in _find_all(root, "IncludedSupplyChainTradeLineItem"):
        for s in _find_all(item, "SpecifiedTradeSettlementLineMonetarySummation"):
            v = _child_text(s, "LineTotalAmount")
            if v is not None:
                out.append(v)
                break
    return out


def profile_from_xml(xml_text):
    m = re.search(r"<ram:ID>(urn:[^<]+)</ram:ID>", xml_text)
    guide = m.group(1) if m else ""
    if re.search(r"extended", guide, re.I):
        return "EXTENDED"
    if re.search(r"basicwl|basic", guide, re.I):
        return "BASIC"
    if "en16931" in guide.lower() or "factur-x" in xml_text.lower():
        return "EN16931"
    if "BASIC" in xml_text:
        return "BASIC"
    return "ZUGFeRD/Factur-X"


def parse_de(s):
    s = str(s).strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def find_rechnungsbetrag(text):
    m = re.search(r"Rechnungsbetrag[^0-9]{0,30}(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+\.\d{2}|\d+,\d{2})", text, re.I)
    return parse_de(m.group(1)) if m else None


def pdf_contains_amount(text, target):
    for c in re.findall(r"\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+\.\d{2}", text):
        v = parse_de(c)
        if v is not None and abs(v - target) <= TOL:
            return True
    return False


def extract_xml_and_text(data):
    """Gibt (xml_bytes, pdf_text, pages, attach_name) zurück oder wirft."""
    reader = PdfReader(io.BytesIO(data))
    atts = getattr(reader, "attachments", None) or {}
    # pypdf: dict name -> list[bytes] oder bytes
    names = list(atts.keys())
    pick = (next((k for k in names if re.search(r"factur-?x\.xml$", k, re.I)), None)
            or next((k for k in names if re.search(r"zugferd.*\.xml$", k, re.I)), None)
            or next((k for k in names if k.lower().endswith(".xml")), None))
    if not pick:
        raise LookupError("Kein eingebettetes XML gefunden (Anhang factur-x.xml / zugferd-invoice.xml fehlt)")
    raw = atts[pick]
    if isinstance(raw, list):
        raw = b"".join(bytes(x) for x in raw)
    xml_bytes = bytes(raw)
    text = "\n".join([(p.extract_text() or "") for p in reader.pages])
    return xml_bytes, text, len(reader.pages), pick


@app.get("/health")
def health(): return {"status": "ok", "version": RULES_VERSION}


@app.post("/validate")
def validate():
    if "file" not in request.files:
        return jsonify(error="no file"), 400
    f = request.files["file"]
    data = f.read()
    name = f.filename
    h = sha256_8(data)
    errors, warnings, profile = [], [], "—"
    xml_text = None
    sums = {}

    try:
        try:
            xml_bytes, pdf_text, pages, attach_name = extract_xml_and_text(data)
        except LookupError as e:
            errors.append(str(e) + " - Stufe 1 ROT")
            return jsonify(filename=name, hash=h, status="ROT", profile=profile,
                           errors=errors, warnings=warnings, version=RULES_VERSION)
        xml_text = xml_bytes.decode("utf-8", errors="replace")
        # Wohlgeformt? (volles XML, keine Trunkierung)
        try:
            root = ET.fromstring(xml_bytes)
        except Exception as e:
            errors.append(f"XML nicht wohlgeformt: {e}")
            return jsonify(filename=name, hash=h, status="ROT", profile=profile,
                           errors=errors, warnings=warnings, version=RULES_VERSION)
        profile = profile_from_xml(xml_text)

        # Pflichtfelder (tolerant -> GELB)
        checks = {
            "Rechnungsnummer (BT-1)": bool(re.search(r"<ram:ID|BuyerReference|InvoiceNumber", xml_text)),
            "Rechnungsdatum (BT-2)": bool(re.search(r"IssueDateTime|BT-2", xml_text)),
            "Verkäufer (BT-27)": bool(re.search(r"SellerTradeParty|BT-27", xml_text)),
            "Summen (BT-106)": bool(re.search(r"GrandTotalAmount|MonetarySummation", xml_text)),
            "USt (BT-117)": bool(re.search(r"ApplicableTradeTax|BT-117", xml_text)),
        }
        for k, v in checks.items():
            if not v:
                warnings.append(f"Pflichtfeld-Hinweis: {k} nicht erkannt")

        # ---- Rechenprüfung (ROT, nie GELB) ----
        sums = header_sums(root)
        groups = header_tax_groups(root)
        lines = line_totals(root)
        if sums.get("grand") is None:
            warnings.append("Kein GrandTotalAmount gefunden")
        for i, g in enumerate(groups, 1):
            if g["basis"] is not None and g["calc"] is not None and g["rate"] is not None:
                erwartet = round(g["basis"] * g["rate"]) / 100
                if abs(erwartet - g["calc"]) > TOL:
                    errors.append(
                        f"MwSt-Rechenfehler (BT-117) Gruppe {i}: Basis {g['basis']:.2f} × {g['rate']}% "
                        f"= erwartet {erwartet:.2f}, gefunden {g['calc']:.2f} - ROT")
        if sums.get("basis") is not None and sums.get("tax") is not None and sums.get("grand") is not None:
            if abs((sums["basis"] + sums["tax"]) - sums["grand"]) > TOL:
                errors.append(
                    f"Summenkette gebrochen (BT-109+BT-110≠BT-112): {sums['basis']:.2f}+{sums['tax']:.2f}"
                    f"={sums['basis']+sums['tax']:.2f}, aber GrandTotal {sums['grand']:.2f} - ROT")
        if lines and sums.get("line") is not None:
            s = sum(lines)
            if abs(s - sums["line"]) > TOL:
                errors.append(f"Zeilensumme ≠ BT-106: Zeilen {s:.2f}, BT-106 {sums['line']:.2f} - ROT")
        if sums.get("grand") is not None and sums.get("due") is not None:
            pre = sums.get("prepaid") or 0.0
            if abs((sums["grand"] - pre) - sums["due"]) > TOL:
                errors.append(
                    f"DuePayable inkonsistent (BT-112-BT-113≠BT-115): Grand {sums['grand']:.2f} - "
                    f"Prepaid {pre:.2f} ≠ Due {sums['due']:.2f} - ROT")
        if len(xml_text) < 500:
            errors.append("XML ungewöhnlich klein (<500 Zeichen)")

        # ---- PDF-Sicht vs XML ----
        if sums.get("grand") is not None and pdf_text:
            pb = find_rechnungsbetrag(pdf_text)
            if pb is not None:
                if abs(pb - sums["grand"]) > TOL:
                    errors.append(
                        f"PDF↔XML-Mismatch: sichtbar {pb:.2f}, XML-GrandTotal {sums['grand']:.2f} - ROT")
            elif not pdf_contains_amount(pdf_text, sums["grand"]):
                warnings.append(
                    f"PDF↔XML-Hinweis: XML-Brutto {sums['grand']:.2f} im Sichttext nicht gefunden - manuell prüfen")
    except Exception as e:
        errors.append(f"PDF Parse Fehler: {e}")
        return jsonify(filename=name, hash=h, status="ROT", profile=profile,
                       errors=errors, warnings=warnings, version=RULES_VERSION)

    status = "GRÜN" if not errors and not warnings else "GELB" if not errors else "ROT"
    return jsonify(filename=name, hash=h, status=status, profile=profile,
                   errors=errors, warnings=warnings,
                   xmlSnippet=xml_text[:3000] if xml_text else None,
                   sums=sums, version=RULES_VERSION)


# ---- Quarantäne (Patch 2026-09-10) ----
# Kopien kaputter Dateien + Kommentar gleichen Namens in extra Ordner.
# Der Ordner wird LAZY angelegt: erst beim ersten abzulegenden Fehler, nie vorher.
def build_comment_md(*, filename, filehash, status, profile, errors, warnings,
                     sums, version, checked_at):
    def f(v):
        return f"{v:.2f} €" if isinstance(v, (int, float)) else "—"
    lines = [
        f"# Prüfkommentar: {filename}",
        "",
        f"- Status: **{status}**",
        f"- Profil: {profile}",
        f"- SHA-256 (8): `{filehash}`",
        f"- Geprüft: {checked_at} (offline, Regeln: {version})",
        "",
        "## Beträge (XML)",
        "",
        f"- Netto (BT-109): {f((sums or {}).get('basis'))}",
        f"- MwSt (BT-110): {f((sums or {}).get('tax'))}",
        f"- Brutto (BT-112): {f((sums or {}).get('grand'))}",
        f"- Fällig (BT-115): {f((sums or {}).get('due'))}",
        "",
        "## Fehler",
        "",
    ]
    lines += [f"- 🔴 {e}" for e in (errors or [])] or ["- (keine)"]
    lines += ["", "## Hinweise", ""]
    lines += [f"- 🟡 {w}" for w in (warnings or [])] or ["- (keine)"]
    lines += ["", "## Maßnahme",
              "",
              "- Maßgeblich ist das XML. Bitte beim Lieferanten klären,",
              "  korrigierte Rechnung anfordern und erneut prüfen.",
              ""]
    return "\n".join(lines)


def quarantine_if_rot(*, pdf_bytes, filename, result_json, fehler_dir):
    """Legt bei Status ROT eine Kopie + .md gleichen Stamens in fehler_dir ab.
    Gibt (pdf_path, md_path) oder (None, None) zurück. Erstellt fehler_dir
    ausschließlich im Fehlerfall (lazy)."""
    import datetime as _dt
    import pathlib as _pl
    if (result_json or {}).get("status") != "ROT":
        return None, None
    _pl.Path(fehler_dir).mkdir(parents=True, exist_ok=True)  # lazy: nur hier
    dest_pdf = _pl.Path(fehler_dir) / filename
    dest_pdf.write_bytes(pdf_bytes)
    stem = _pl.Path(filename).stem
    md_text = build_comment_md(
        filename=filename,
        filehash=(result_json or {}).get("hash", "—"),
        status=result_json.get("status", "ROT"),
        profile=(result_json or {}).get("profile", "—"),
        errors=(result_json or {}).get("errors", []),
        warnings=(result_json or {}).get("warnings", []),
        sums=(result_json or {}).get("sums", {}),
        version=(result_json or {}).get("version", RULES_VERSION),
        checked_at=_dt.datetime.now().isoformat(timespec="seconds"),
    )
    dest_md = _pl.Path(fehler_dir) / f"{stem}.md"
    dest_md.write_text(md_text, encoding="utf-8")
    return str(dest_pdf), str(dest_md)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
