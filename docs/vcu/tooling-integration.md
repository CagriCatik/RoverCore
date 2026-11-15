# VCU-Werkzeuge und Übernahme aus PCB-Project-Template

## Herkunft und Integration, Stand 2026-11-15

Geprüfte Quelle: `CagriCatik/PCB-Project-Template`, Commit
`65486a57c34182e49e1d76b4ed9779de235f1fb9`.
RoverCore wurde während dieser Arbeit vom Owner auf `b2d1831` aktualisiert.
Dieser Stand ist ein eigenständiges Boardprojekt; die früher vollständig
enthaltenen Kit-Werkzeuge wurden dabei entfernt. Er enthält jetzt die zwei
VCU-Dokumente, den aktiven Leistungsrechner und das native, noch leere Board.

Wir übernehmen **den Werkzeugzugriff**, nicht erneut das gesamte Template:
`scripts/kit` delegiert an einen explizit angegebenen externen Kit-Checkout.
Dadurch bleiben Generator, GUI, Fixtures und Installer außerhalb des
Fahrzeugprojekts. Kein Download, keine Installation und kein Update erfolgen
automatisch. Das Template-Repository wird nicht geändert.

## Lokale Verwendung auf dem Rechner mit KiCad 10.0.7

```sh
export ROVERCORE_KIT_ROOT="/absoluter/pfad/PCB-Project-Template"
scripts/kit doctor
scripts/kit verify .
scripts/kit thermal analyze . --help
scripts/kit firmware . --help
scripts/kit export . --revision A1
```

Die Befehle laufen aus dem RoverCore-Verzeichnis; relative Projektpfade bleiben
erhalten. Zum Reproduzieren den oben genannten Kit-Commit verwenden. Für andere
Kit-Stände Tests und Kompatibilität erneut prüfen. Exporte bleiben DRAFT/NO-GO;
keine Fertigungsfreigabe ist Bestandteil dieser Änderung. Das Kit liest die
projektlokale `qa/verification.json`. Thermik braucht reales Layout und explizite
Verlustleistungen, Firmware eine tatsächlich vorhandene Anwendung/BSP.

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

## Verifikation und Grenzen

- Fünf neue Budgettests bestanden, einschließlich unabhängiger Zweigströme,
  gemeinsamer Reservelast, unbelastetem Zweig und ungültigen Eingaben.
- Wrapper: Shell-Syntax, Weiterleitung zu Kit-Hilfe sowie Ablehnung eines
  fehlenden oder auf RoverCore zeigenden Kit-Pfads geprüft.
- Vor Integration des Owner-Pushs: Gesamtsuite 210 Tests, 85 übersprungen,
  zwei Umgebungsfehler (PySide6 fehlt; thermischer Gate-Test verlangt
  KiCad 10.0.7, installiert ist 9.0.2). Unverändertes Template: 205 Tests mit
  denselben zwei Fehlern und 85 übersprungenen Tests. Das ist ein Kit-
  Vergleichslauf, keine Hardwarevalidierung des inzwischen neuen Boardprojekts.
- Der delegierte Projekt-Verify-Lauf wird bei KiCad 9.0.2 korrekt abgelehnt.
- Native ERC/DRC unter 10.0.7, Firmware auf ESP32 und physische Prüfungen
  nicht durchgeführt. Keine nativen KiCad-Dateien geändert, keine
  Fertigungsdaten erzeugt.

Nächster Schritt: lokale Kit-Installation mit KiCad 10.0.7 verwenden, aktive
Schaltung erstellen, Pinmap gegen diese abgleichen und die offenen Nachweise
in den VCU-Dokumenten schließen. Der Schaltplan bleibt Hardware-Wahrheit.
