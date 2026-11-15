# Schaltplan-Darstellungsreview 2026-11-15

Ziel: Struktur, Gruppierung, Beschriftung und Lesbarkeit aller Schaltplanblätter
verbessern – **ohne elektrische Änderung** (Bauteile, Werte, Referenzen,
Footprints und Pin-zu-Netz-Verbindungen unverändert). PCB und Firmware sind
nicht betroffen.

## Stände

| Rolle | Commit |
|---|---|
| Basis (elektrische Review-Korrekturen) | `e473ac2` |
| Darstellung, Zwischenstand | `bf68d58` (lokal, Urheber dieses Commits nicht geklärt) |
| Darstellung, Abschluss | `7c3794d` |
| Bilder aus der Git-Verfolgung genommen | `f621f98` |

Werkzeuge: KiCad 10.0.7, `hardware/scripts/relayout_sheet.py` mit den
Layoutvorgaben in `hardware/scripts/sheet_layouts.py`. Die Vorgaben enthalten
nur Positionen, Feldlagen, direkte Verdrahtung lokaler Netze, Gruppenrahmen
und Kommentare. Die Konnektivität übernimmt das Werkzeug aus der Netzliste.

## Ergebnis je Blatt

| Blatt | Wesentliche Änderungen |
|---|---|
| Root | Blöcke ohne Pins (Actuators, Lighting_IO) ausgerichtet; Hinweis zur Hierarchie (nur VBAT_PROT hierarchisch, sonst globale Labels) |
| Power | Signalfluss links → rechts, VBAT_IN/VBAT_FUSED/Gate/VBAT_PROT verdrahtet, drei Gruppen, PWR_FLAGs an den Testpunkten |
| LogicPower | Gruppen Eingang/EN, Buck, Ausgang/Rückkopplung; Teiler, BOOT, SW und +5V-Ausgangsschiene verdrahtet |
| ServoPower | sechs Gruppen; alle passiven Netzwerke verdrahtet; LTC7803-Pins bewusst mit Labels (dichte Pinreihe) |
| Controller | fünf Gruppen; VBAT-Schalter, Teiler, Klemmung und P3V3_OK verdrahtet; Sockel-Labels entflochten |
| Actuators | Pufferblock und fünf gleich aufgebaute Ausgangskanäle, je vollständig verdrahtet |
| Lighting_IO | fünf Gruppen (5-V-Schalter, LED, Buzzer, i-BUS, UART), lokal verdrahtet |

## Nachweise

| Prüfung | Ergebnis |
|---|---|
| `hardware/scripts/compare_schematic_revisions.py e473ac2` – Netze (Name und Pins), Bauteile (Wert, Footprint, alle Felder, Blattpfad), hierarchische/globale Labels und Blattpins je Blatt, in_bom/on_board/dnp/exclude_from_sim, Symbol- und Pin-UUIDs | **identisch** (129 Netze, 211 Bauteile, 7 Blattdateien) |
| Empfindlichkeit dieses Vergleichs (gegen `53fb180`) | 143 Unterschiede erkannt |
| ERC | vorher 3, nachher dieselben 3 Befunde (isolierte Labels IMU_INT1, I2C_SDA, I2C_SCL) |
| `scripts/kit verify` | vorher und nachher gleiche Befundzahlen (erc 3, drc 1, schematic_parity 199, component_metadata 42, bom 191) |
| `check_socket_pinmap.py` | 24 Signal / 7 Versorgung / 13 erwartete No-Connects, unverändert |
| Unit-Tests `qa/tests` | 77, OK (1 übersprungen) |

**Unveränderte Befundzahlen bedeuten keine Freigabe.** ERC, DRC, Parität,
Metadaten und BOM bleiben offen. Ursachen: das fehlende Blatt
Sensors_Display, die noch leere Platine sowie fehlende BOM-Einträge und
MPN-Felder.

## Verbleibende Punkte

- Labels statt Leitungen an dichten Pinreihen (LTC7803, SN74LVC8T245,
  DevKit-Sockel), an den Pull-Widerstandsreihen auf Actuators und an
  Steckerversorgungspins – bewusst so belassen.
- LED_4_5V zwischen U202 und R610 als Label (kein kollisionsfreier Weg).
- Restliche Textkollisionen (u. a. Buzzer) werden im Anschluss bereinigt
  (siehe Nachtrag unten).

## Ablage

Vorher-/Nachher-Bilder und der ausführliche generierte Bericht liegen lokal
unter `qa/generated/schematic-review/2026-11-15_18-23/` und werden nicht
versioniert (`.gitignore`). Erzeugt mit
`python3 hardware/scripts/render_schematic_review.py <Ordner>`; es sind aus
KiCad exportierte, gerenderte Ansichten (SVG → PNG), keine Bildschirmfotos.
