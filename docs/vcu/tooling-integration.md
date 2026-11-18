# VCU-Werkzeuge in RoverCore

## Herkunft, Stand 2026-11-15

Die Board-Werkzeuge aus `CagriCatik/PCB-Project-Template` (Commit
`65486a57c34182e49e1d76b4ed9779de235f1fb9`, MIT-Lizenz) liegen **direkt in
RoverCore** unter `tools/`; `scripts/kit` ist ein lokaler Launcher. Ein
zweiter Repository-Checkout und `ROVERCORE_KIT_ROOT` werden nicht mehr
benötigt. Übernommen sind KiCad-Diagnose, ERC/DRC mit Schaltplanabgleich,
Bibliotheksprüfung, Fertigungsexport und thermische Analyse samt
Abhängigkeiten, Konfiguration, Fixtures und Tests. Nicht übernommen sind
Projektgenerator, Vorlagen, GUI und Paketierung. Umfang, Lizenz und lokale
Änderungen: [`tools/VENDORED.md`](https://github.com/CagriCatik/RoverCore/blob/main/tools/VENDORED.md).

Historie: `b2d1831` hatte die damals vollständig enthaltenen Kit-Werkzeuge
entfernt, `762bea3` sie durch einen Wrapper auf einen externen Checkout
ersetzt. Dieser Wrapper ist durch den lokalen Launcher abgelöst.

## Lokale Verwendung (KiCad 10.0.7)

```sh
scripts/kit install          # einmalig: .venv aus requirements.txt (pip braucht Netz)
scripts/kit doctor
scripts/kit verify .
scripts/kit export . --revision A1
scripts/kit thermal analyze .
.venv/bin/python -m unittest discover -s qa/tests -t qa/tests
```

Exporte bleiben DRAFT/NO-GO; eine Fertigungsfreigabe ist nicht Bestandteil.
Thermik braucht reales Layout und explizite Verlustleistungen
(`hardware/simulations/thermal/power_sources.csv` oder `--power REF=W`),
Firmware eine tatsächlich vorhandene Anwendung/BSP.

## Ergänzter unabhängiger Spannungsbudget-Check

```sh
python3 hardware/simulations/power/servo_voltage_budget.py \
  --source-min-v 6.69 --shared-ohm 0.007 \
  --branch 5:0.06 --branch 5:0.06 --branch 0.5:0.02 --branch 0.5:0.02
python3 -m unittest discover -s qa/tests -p test_servo_voltage_budget.py -v
python3 hardware/simulations/power/rev1_power_calc.py
```

Das erste Beispiel ist ein **illustratives Szenario**, keine bestätigte
RoverCore-Auslegung. Jeder Zweig ist eine konstante Stromannahme; alle
Widerstände beinhalten Hin- und Rückweg. Die Quelle enthält bereits die
Reglertoleranz. Gemeinsame Widerstände nicht nochmals pro Zweig zählen.
Das Modell endet am externen Servoanschluss, nicht am internen Motor.
Der gemeinsame Shunt liegt außerhalb der Regler-Rückkopplung, wenn sein
Spannungsabfall hier gezählt wird; bei anderer Senseposition Modell anpassen.

Die Ausgabe enthält Gesamtstrom, gemeinsamen Spannungsabfall, Spannungen an
allen Anschlüssen und ohmsche Verluste. Im Beispiel: 6,313 V an beiden
Lenkservoanschlüssen. Der Rechner modelliert keine dynamische Servolast,
Strombegrenzung, Temperatur, TVS oder Sicherung und erzeugt keine Freigabe.
Er ergänzt den vorhandenen `rev1_power_calc.py`, ersetzt ihn nicht.

## Verifikation und Grenzen (Lauf am 2026-11-15, macOS arm64, KiCad 10.0.7)

| Befehl | Ergebnis |
| --- | --- |
| `scripts/kit doctor` | WARN: KiCad 10.0.7 PASS, Bibliotheken 223/155 PASS, Plugins PASS (InteractiveHtmlBom, Freerouting, KiKit installiert, nicht verifiziert); IPC nicht erreichbar (KiCad läuft nicht, API-Server aus) |
| `scripts/kit install --no-plugin-verify` | `.venv` angelegt (numpy 2.5.4, scipy 1.18.1, kicad-python) |
| `scripts/kit verify .` | FAIL, blockierend nur DRC `invalid_outline` (leere Platine ohne Kontur); ERC, Abgleich, Bibliotheken, Footprints, Pin/Pad PASS |
| `scripts/kit export . --revision A0-tooling` | DRAFT / NO-GO erzeugt (Gerber, Bohr, BOM, Positionen, STEP, PDF, Netzliste); Interactive HTML BOM FAILED, weil keine Platinenkontur |
| `scripts/kit thermal analyze .` | Abbruch: keine Verlustleistungen angegeben (erwartet bei leerer Platine) |
| `scripts/kit thermal analyze <Fixture-Kopie> --power R1=0.2 --power R2=0.1` | PASS (Schätzung) |
| Tests | 77 Tests OK, 1 übersprungen (IPC-Live-Test, KiCad nicht gestartet) |

Keine nativen KiCad-Dateien geändert, keine Fertigungsfreigabe. Der
Schaltplan bleibt Hardware-Wahrheit.
