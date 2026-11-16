# RoverCore VCU Rev1 – erste funktionale Platzierung (Stand 2026-11-16)

**Status: vorläufiger Platzierungsvorschlag.**
- Keine Fertigungsfreigabe, kein Routing.
- Kontur, Befestigung und Steckerzugang sind **nicht** mit dem Chassis
  abgestimmt. Sie dienen nur dazu, den Platzbedarf abzuleiten.
- Die Gehäusedaten folgen aus dem selbst gedruckten Fahrzeugaufbau. Diese
  Platzierung liefert dafür den Flächenbedarf.

## 1. Schaltplanstand und Übernahme der Footprints

- **Schaltplanstand:** Commit `c931024` (O-37 Rev C mit korrigierten
  Gültigkeitsbereichen), ERC 0. Keine neue Schaltungsarchitektur.
- **Übernahme:** `hardware/scripts/build_board.py`, ausgeführt mit der Python
  von KiCad 10.0.7 (pcbnew).
  - Das ist das skriptgesteuerte Gegenstück zu „Update PCB from Schematic“.
    Der Befehl selbst wurde nicht über die Oberfläche ausgeführt.
  - Pro Bauteil werden übernommen:
    - Bibliotheks-Footprint, Referenz, Wert und alle Symbolfelder (verdeckt);
    - Blattname und -datei;
    - Symbolpfad `/Blatt-UUID/Symbol-UUID`, damit ein späteres „Update PCB
      from Schematic“ im Editor die Footprints über den Pfad zuordnet;
    - die Netze der Pads.
  - Empfehlung: im PCB-Editor einmal F8 ausführen. Erwartet: keine Änderungen.
- **Prüfung, ob alle Bauteile vorhanden und korrekt zugeordnet sind**
  (`scripts/kit verify .`, KiCad-eigene Prüfungen):

| Prüfung | Ergebnis |
|---|---|
| schematic_parity (KiCad DRC `--schematic-parity`) | **PASS, 0 Befunde**: 253 Footprints, 157 Netze, Felder und Netze stimmen mit dem Schaltplan |
| footprint_assignment, pin_pad_mapping, library_references, portability | PASS |
| ERC | PASS, 0 |
| DRC | FAIL, nur Platzierungsstand: 199 silk_overlap, 199 silk_over_copper (Referenztexte in dicht gepackten Reihen), 17 text_height (Pin-Beschriftung der Projekt-Footprints J115/J116), 3 silk_edge_clearance; **keine** Courtyard-, Abstands- oder Kurzschlussbefunde; 499 nicht verbundene Verbindungen (noch kein Routing) |
| models_3d (Hinweis) | 17 Footprints ohne 3D-Modell bzw. mit fehlender Modelldatei; keine Ersatzgeometrie eingesetzt |

- Beim ersten Lauf traten zwei Werkzeugfehler auf, beide behoben:
  - das Feld `Fuse_Insert` von F101 fehlte;
  - bei 11 nicht beschalteten DevKit-Pins war das Netz falsch geschrieben
    (KiCad schreibt `/` im Pinnamen als `{slash}`).
- Die Prüfung oben ist der Stand nach der Korrektur.

## 2. Funktionale Gruppen (vorläufige Kontur 150 × 100 mm)

| Bereich (x × y in mm) | Gruppe | Inhalt und Begründung |
|---|---|---|
| 0–35 × 0–47 | 1 Eingangsschutz | XT30 J101 an der linken Kante (Steckrichtung von links), Sicherung F101, Verpolschutz Q101 mit D102/R101, TVS D101, Puffer C101/C102 → VBAT_PROT. Kurzer Weg zu Servoregler (rechts) und Logikversorgung (unten) |
| 0–35 × 47–76 | 2 Logikversorgung | TPS54302 U301 mit Eingangs-C direkt an VIN/GND, L301 in Linie mit SW, Ausgangs-C daneben; FB-/EN-Teiler links, abseits von SW |
| 35–92,5 × 0–48 | 3 Servoregler | LTC7803 mit Leistungsstufe (unten Punkt 3), Messung INA240 U402 an RS402; RUN-Gruppe mit Q403/Q404/Q407/Q408 nahe U401 |
| 92,5–121,5 × 0–63 | 4 Aktuatoranschlüsse | Micro-Fit J102/J103 an der oberen Kante, Stiftleisten J104–J106 darunter, Puffer U201/U204 und Ausgangsstufen Q201–Q206 direkt davor. +V_SERVO von RS402 kurz zu den Anschlüssen |
| 121,5–150 × 0–65 | 5 Controller | DevKit-Sockel U501 an der rechten Kante (Punkt 4) |
| 121,5–150 × 65–100 | Controller-Peripherie | Taster SW501–SW503, Wächter U504/U505/U515/U516, Latch U506–U508, O-37-Teile, Messpunkte; nur flache SMD (USB-Steckerzugang) |
| 57–121,5 × 48–100 | 6 Sensoren und Display | Modulsockel J116 (OLED) und J115 (IMU), I²C-Pull-ups R801–R803 |
| 0–57 × 76–100 | 7 Schnittstellen | LED-/UART-Anschlüsse J108–J112 an der unteren Kante, iBUS J107, Summer BZ101, Schutz- und Pegelbauteile |

- **Packung:**
  - Kritische Teile, Stecker und Module sind einzeln gesetzt.
  - Die übrigen Kleinteile jeder Gruppe sind nach Courtyard-Größe in den
    Gruppenrahmen gepackt (`hardware/scripts/board_layout.py`). Das ist eine
    Gruppenzuordnung, keine Feinplatzierung.
- Die Gruppenrahmen stehen auf Dwgs.User, die vorläufigen Bohrungsmarken
  auf Cmts.User. **Gebohrt wird nichts.**

## 3. Kritische Leistungs- und Rückkopplungsschleifen

**Servoregler (Gruppe 3):**
- **Schleife mit hohem di/dt:**
  - Q401 (HS) und Q402 (LS) liegen nebeneinander. Q401 ist um 270°
    gedreht, Q402 um 90°.
  - Damit liegen Source-Pins Q401 und Drain-Pad Q402 (beide SW) oben.
  - Drain Q401 (VBAT_PROT) und Source Q402 (GND) liegen unten.
  - Eingangskondensatoren direkt darunter:
    - C405 (100 nF) zuerst;
    - C401/C402 auf der Oberseite;
    - C403/C404 auf der **Unterseite** unter C401/C402.
  - VBAT-Pad jeweils unter Q401, GND-Pad unter Q402 (Pads geprüft:
    VBAT_PROT x = 52,5, GND x = 55,5).
- **SW-Knoten:** von den FETs auf kurzem Weg zu L401 (rechts), dann RS401
  und die Ausgangskondensatoren C406–C410.
- **Kelvin-Abgriffe:**
  - NT401/NT402 sitzen an den Pad-Kanten von RS401; NT404/NT405 an RS402.
  - NT403 (Rückkopplungsabgriff vor RS402) sitzt am VSERVO_REG-Pad von RS402.
- **Offen für die Feinplatzierung:**
  - BG-Leitung Q402 → U401 ca. 12 mm. U401 liegt links neben Q401, damit TG
    kurz bleibt.
  - SENSE± von RS401 zu U401 ca. 30 mm, als Paar zu führen; RF401/CF401
    sitzen an U401.
  - GND-Rückweg der Ausgangskondensatoren über eine durchgehende Innenlage.

**Logikversorgung (Gruppe 2):**
- U301 ist um 180° gedreht, damit VIN/GND/SW zur Leistungsseite zeigen.
- C301 liegt quer über VIN/GND; die SW-Leitung führt zwischen seinen Pads zu
  L301. Die Ausgangs-C liegen rechts.
- Der Boot-C C303 liegt an BOOT/SW; FB-Teiler R301–R303 links, abseits von
  L301.

**Eingang (Gruppe 1):**
- Stromweg J101 → F101 → Q101 → D101/C101/C102 ohne Umweg.
- VBAT_PROT geht nach rechts (Servoregler) und nach unten (U301) ab.

## 4. DevKit, Antenne und USB

- U501 sitzt an der rechten Kante. Die Antennen-Sperrfläche des Footprints
  (y −6,3 … 1,0 relativ zur Kontur) liegt fast vollständig **über der oberen
  Kante hinaus**.
- Dort sind auf allen Lagen keine Bauteile oder Leiterbahnen; die
  Sperrzone ist im Footprint enthalten. Die Antennenausrichtung „mittig“ ist
  weiterhin zu bestätigen (O-4).
- **USB:**
  - Beide Micro-USB-Buchsen sitzen am unteren DevKit-Ende (y ≈ 62) und zeigen
    in die Platine.
  - Der Bereich davor (121,5–150 × 65–100) enthält nur flache SMD-Teile und
    Taster. Der Stecker kommt in DevKit-Höhe (Sockel 8,51 mm) von unten.
  - Ob der Stecker im Fahrzeug zugänglich ist, hängt vom Chassis ab (offen).
- Taster und Messpunkte liegen außerhalb des DevKit-Umrisses, also auch mit
  gestecktem DevKit erreichbar.

## 5. Platzbedarf (Schätzung)

| Gruppe | Courtyard-Fläche |
|---|---|
| Controller (inkl. DevKit-Sockel 26 × 70 mm) | 2342 mm² |
| Sensoren/Display (Modulsockel) | 1469 mm² |
| Servoregler | 872 mm² |
| Aktuatoren | 794 mm² |
| Lighting_IO | 647 mm² |
| Eingang | 625 mm² |
| Logikversorgung | 179 mm² |
| **Summe** | **6928 mm²** |

- **Vorschlag:** 150 × 100 mm = 15 000 mm². Belegung ca. 46 %
  (Courtyard-Summe / Fläche), Reserve für Routing, Kupferflächen und
  Kühlflächen.
- Die Breite bestimmt die obere Reihe: Eingang 35 + Servoregler 57,5 +
  Aktuatoren 29 + DevKit 28,5 mm.
- **Verkleinerung möglich** (Abstimmung mit dem Chassis), z. B.:
  - die Sensor- und Displaymodule an Kabel oder auf eine eigene Ebene;
  - die untere Reihe enger.
  - Abgeschätzt sind ca. 135 × 90 mm möglich, ohne die Leistungsschleifen
    zu verändern. Das ist eine Schätzung, nicht geprüft.
- **Befestigung:** Marken für M3 (3,2 mm) bei (3,5 | 3,5), (3,5 | 96,5),
  (146,5 | 96,5) und (118 | 66).
  - Die Ecke oben rechts ist durch die Antenne belegt.
  - Die Lage folgt dem Chassis.

## 6. Ansichten

Erzeugt mit `hardware/scripts/render_placement_review.py` (pcbnew-Python) und
`kicad-cli pcb render`. Ablage `qa/generated/placement/`; das ist erzeugte
Ausgabe und wird nicht eingecheckt.

| Datei | Inhalt |
|---|---|
| `overview.png/.svg` | ganze Platine: Courtyards, Pads, Gruppenrahmen, Kontur, Bohrungsmarken, Luftlinien (kritische Netze farbig, übrige grau) |
| `detail_input_logic.png` | Eingangsschutz und Logikversorgung |
| `detail_servo_regulator.png` | Leistungsstufe LTC7803, Kelvin-Abgriffe, Messung |
| `detail_devkit_usb.png` | Aktuatoren, DevKit mit Antennenrand, USB-Zugang, Controller-Peripherie |
| `render_3d_top.png`, `render_3d_iso.png` | 3D-Ansicht (Teile ohne Modell fehlen, siehe models_3d) |

Neu erzeugen:

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/scripts/build_board.py
```

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/scripts/render_placement_review.py
```

## 7. Offen (vor Routing bzw. Fertigungsfreigabe)

- Chassis: Kontur, Bohrungen, Steckerzugang (XT30, Micro-Fit, USB), Bauhöhen
  über und unter der Platine.
- Feinplatzierung:
  - BG-Weg, SENSE-Paar, Kühlkupfer Q401/Q402/L401;
  - Lage der Unterseiten-Kondensatoren C403/C404 bestätigen;
  - Referenztexte (Silkscreen).
- Thermik: `scripts/kit thermal analyze` nach der Feinplatzierung. O-16:
  WROOM nur bis 65 °C, also Abstand zu den Reglern prüfen.
- Lagenaufbau: Die Platine ist 4-lagig angelegt (F, In1, In2, B). Die
  Belegung der Innenlagen (GND-Fläche) wird mit dem Routing festgelegt.
- 3D-Modelle der 17 Footprints ohne Modell (nur echte Herstellerdaten).
- Weiter offen aus dem Schaltplan:
  - O-36 (ESC-Test);
  - O-37-Messungen und A11/A12;
  - Abfragenachweis < 12 ms auf dem ESP32;
  - Unterspannungs-Prüfpunkt V.18.
