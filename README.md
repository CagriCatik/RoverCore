# RoverCore

Modulare VCU-Trägerplatine (Rev 1) für einen RC-Rover: steckbares
ESP32-S3-DevKitC-1, IMU (Adafruit 4438), OLED (Adafruit 326), geregelte
Servoschiene, 5-V-Logikversorgung, LED-, Empfänger- und UART-Ausgänge.
KiCad 10.0.7, 4 Lagen, 160 × 85 mm (Variante B, vier M3-Eckbohrungen).

**Stand 2026-11-18: Variante B umgesetzt, DRAFT-Paket A3 (NO-GO). Fertigung gestoppt bis zum Fahrzeugabgleich.**
ERC, DRC und Schaltplan-Parität bestehen im lokalen Lauf. Der
JLCPCB-Regelsatz im DRC prüft Kupfer, Bohrungen und Texte, aber keine
Linienbreiten im Bestückungsdruck (bekannte Abweichung, siehe unten). Das ist ein Werkzeugergebnis; elektrische, thermische und
fertigungstechnische Freigabe stehen aus. Nächster Schritt ist der
prüfbare Prototyp nach dem [Inbetriebnahmeplan](docs/bringup.md).

![RoverCore Rev 1 mit gesteckten Modulen, schräg von vorne](docs/images/populated_iso_front.jpg)

## Ansichten

Review-Ansichten (`hardware/scripts/render_populated_review.py`): Bauteile mit
KiCad-Bibliotheksmodell erscheinen normal. J102/J103 zeigen das Molex-Herstellermodell
(projektlokal, nicht in Git). J101 XT30, BZ101, Q101, Q401/Q402 und D601–D604, D606–D608 zeigen **selbst erzeugte,
vereinfachte Gehäusemodelle nach den Maßzeichnungen der Hersteller** – keine heruntergeladenen Herstellermodelle
(`hardware/scripts/make_package_models.py`, MIT, als STEP und VRML; Maße und Quellen in
`hardware/libraries/3d-models/models.csv`; geschätzt bzw. vereinfacht: XT30-Höhe, Anschlussform BZ101).
**Blau** sind Hüllkörper der gesteckten Module (DevKit, OLED, IMU), Höhen geschätzt. Hüllkörper und eigene Modelle
sind keine verlässlichen mechanischen Modelle; die echten Teile entscheiden beim Passungstest.
Status je Position in `qa/generated/populated/model_status.csv`, Bericht 3g, 3l, 3m.

| Mit Modulen | Ohne Module (Buchsenleisten) |
|---|---|
| ![Mit Modulen, schräg von vorne](docs/images/populated_iso_front.jpg) | ![Ohne Module, schräg von vorne](docs/images/without_modules_iso_front.jpg) |
| ![Mit Modulen, schräg von hinten](docs/images/populated_iso_rear.jpg) | ![Ohne Module, schräg von hinten](docs/images/without_modules_iso_rear.jpg) |
| ![Mit Modulen, oben](docs/images/populated_top.jpg) | ![Ohne Module, oben](docs/images/without_modules_top.jpg) |
| ![Flach von vorne](docs/images/populated_front_low.jpg) | ![Unterseite](docs/images/populated_bottom.jpg) |

Befestigung Variante B ([Bericht](docs/vcu/rev1-befestigung-vorschlag.md)): vier M3-Bohrungen, NPTH 3,2 mm,
(4,5 | 4,5), (4,5 | 80,5), (155,5 | 18,0), (155,5 | 80,5); vorläufig bis zum Fahrzeugabgleich; orange in
den 3D-Ansichten = Hüllkörper für Scheibe, Kopf und 10-mm-Abstandshalter.

![Bemaßte Draufsicht der Befestigungsbohrungen](docs/images/mounting_top.jpg)

**Im Browser ansehen:** [drehbares 3D-Modell und interaktive Stückliste (iBOM)](https://cagricatik.github.io/RoverCore/vcu/ansicht/)
(DRAFT A3.1; ohne die Herstellermodelle von J102/J103, siehe dort).

Aus den exportierten Gerber- und Bohrdateien gezeichnet
(`scripts/kit fab preview`), also so, wie der Fertiger sie erhält:

| Oberseite (Gerber) | Unterseite (Gerber, von unten) | Innenlage In1 (GND) |
|---|---|---|
| ![Gerber oben](docs/images/gerber_top.png) | ![Gerber unten](docs/images/gerber_bottom.png) | ![Gerber In1](docs/images/gerber_in1.png) |

## Eckdaten (Auslegung, nicht gemessen)

| Größe | Wert |
|---|---|
| Eingang | 3S-LiPo, 9,0–12,6 V, XT30, Sicherung 15 A, Verpolschutz Q101, TVS D101 |
| Servoschiene | LTC7803, Sollwert 6,8 V (vorläufig, O-19), Auslegung 11,2 A (zwei blockierte Lenkservos), Strommessung INA240A3 an 2 mΩ |
| Logik | TPS54302, +5V 4,74–5,16 V; DevKit über D501 (PMEG4010CEH), +3V3 aus dem DevKit-LDO |
| Freigabe | `SERVO_PWR_EN` und Freigabe-Latch (SW501, Wiederanlaufsperre 9,62–10,40 V) |
| Lagenaufbau | Fertigungsvorgabe 35 / 17,5 / 17,5 / 35 µm, Prepreg 0,1 mm, 1,6 mm, Hülse IPC-6012 Kl. 2 – beim Fertiger zu bestätigen |

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [Erstinbetriebnahme](docs/bringup.md) | Schrittfolge Versorgung, D501, Servostrompfad, Grenzwerte und Abbruchkriterien |
| [Versorgung und Boardwahl](docs/vcu/rev1-versorgung-und-boardwahl.md) | Auslegung aller Versorgungen, Schutz, Wiederanlaufsperre |
| [Pin- und Anschlussplan](docs/vcu/rev1-pin-und-anschlussplan.md) | GPIO-Belegung, Stecker (maschinenlesbar: `hardware/interfaces/pinmap.csv`) |
| [Platzierung, Routing, Fertigung](docs/vcu/rev1-platzierung.md) | Platzierung, Routing K1, Strompfade (3j), Fertigerabgleich und DRAFT-Paket (3k) |
| [Mechanischer Abgleich](docs/vcu/rev1-mechanik-abgleich.md) | Prüfliste am Fahrzeug, 1:1-Vorlage, Auflage unter dem DevKit |
| [Review 2026-11-15](docs/vcu/rev1-review-2026-11-15.md) · [Werkzeuge](docs/vcu/tooling-integration.md) | Schaltplan-Review, lokale Werkzeuge |
| [Engineering-Richtlinien](docs/engineering/README.md) | allgemeine Regeln aus dem Template |

Online: <https://cagricatik.github.io/RoverCore/>

## Offen vor einer Bestellung

- Lagenaufbau und **Mindest**-Hülsendicke 18 µm schriftlich beim Fertiger
  bestellen (JLCPCB nennt nur einen Mittelwert von 18 µm).
- D502 festgelegt (Würth 150060RS75000); LCSC-Nummer und JLCPCB-Bestand prüfen.
- Datenblattfelder (44 Teile), 3D-Modelle (14), Bauteilakten.
- Bestückungsdruck: 1 211 Umrissstriche mit 0,12 mm im exportierten Gerber
  (JLCPCB verlangt 0,15 mm); Entscheidung offen (Bericht 3l).
- **Befestigung Variante B umgesetzt** (Kontur 160 × 85, vier Eckbohrungen); offen ist der
  Abgleich am Fahrzeug mit der 1:1-Vorlage ([Prüfliste](docs/vcu/rev1-mechanik-abgleich.md)) und der
  Stecktest am DevKit (ob die Auflage unter dem DevKit nötig ist). Ergebnisse der Prüfung des Umbaus
  in [rev1-befestigung-vorschlag.md](docs/vcu/rev1-befestigung-vorschlag.md).
- Bohrdateien: `kit export` liefert getrennt `RoverCore-PTH.drl` und
  `RoverCore-NPTH.drl`; beide hochladen und die 10 NPTH-Löcher in der
  Fertiger-Vorschau prüfen (Bericht 3n).
- 3D / STEP: Alle Carrier-Teile haben ein Modell (`models_3d` 0 Funde). Der Board-STEP (`kit export`,
  `mechanical/board.step`) enthält die eigenen Modelle, ist für Gehäusekonstruktion und Kollisionsprüfung aber
  **unvollständig**: Die gesteckten Module DevKit, OLED und IMU fehlen darin (nur ihre Buchsenleisten; die blauen
  Hüllen gibt es nur in den Review-Bildern), und das Molex-Modell J102/J103 fehlt in einem frischen Checkout,
  solange `vendor/` nicht geladen ist. Eigene Modelle sind vereinfacht (XT30-Höhe geschätzt).
- GO-Freigabe nur mit signierter Freigabe (`manufacturing/approval.example.json`)
  und `--authorize`.

## Repository

| Pfad | Inhalt |
| --- | --- |
| `RoverCore.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` | KiCad-Projekt (Hardware-Wahrheit), Fertiger-Regelsatz |
| `hardware/` | Eigene Bibliotheken (`${KIPRJMOD}`), Schnittstellen, Simulation, Board-Skripte |
| `firmware/` | Firmware, BSP und Treiber (optional) |
| `components/` | Bauteilakten, Datenblätter, SPICE-Modelle |
| `manufacturing/` | Freigabe-Checkliste, Freigaben, erzeugte Exporte (nicht versioniert) |
| `docs/` | Anforderungen, Architektur, Schnittstellen, Inbetriebnahme, Berichte |
| `qa/` | Prüfkonfiguration, Reviews, Berichte |

## Befehle

```sh
scripts/kit install                       # einmalig: lokale .venv (kicad-python, numpy, scipy)
scripts/kit doctor                        # Umgebungsdiagnose, nur lesend
scripts/kit verify .                      # ERC, DRC, Parität, Bibliotheken, Metadaten, 3D, BOM
scripts/kit export . --revision A1        # DRAFT-Fertigungspaket (NO-GO)
scripts/kit thermal analyze .             # stationäre Thermik-Schätzung
scripts/kit power paths .                 # Gleichstrom-Pfade im Kupfer (Schätzung), Fälle in current-paths.json
```

Prüfwerkzeuge für Layout und Fertigungspaket (nur lesend, Ergebnisse unter `qa/generated/`):

```sh
scripts/kit fab check . manufacturing/releases/generated/rev-A3-DRAFT     # Paket gegen Board
scripts/kit fab preview . manufacturing/releases/generated/rev-A3-DRAFT   # Gerber-/Bohrbilder
scripts/kit board diff ALT.kicad_pcb RoverCore.kicad_pcb --project .      # Kupfer-/Bauteilvergleich
scripts/kit models fit . BZ101 hardware/libraries/3d-models/project/SameSky_CMT-8540S-SMT_8.5x8.5x4.0mm.step  # 3D-Sitz
scripts/kit mounting print . --washer 7 --body J101 --body U501           # 1:1-Bohrbild (allgemein)
```

Die Lastfälle für `power paths` stehen in
[`hardware/simulations/power/current-paths.json`](hardware/simulations/power/current-paths.json),
alle Ströme und die Hülsendicke mit Quelle in
[`hardware/interfaces/assumptions.json`](hardware/interfaces/assumptions.json). Die früheren Skripte
`current_map.py`, `board_copper_diff.py`, `fab_package_check.py`, `gerber_preview.py` und
`model_fit_check.py` (in älteren Berichtsabschnitten noch genannt) sind durch diese Befehle ersetzt und
nur noch in der Git-Historie (bis `53f6d7f`). Die RoverCore-spezifischen Montagebilder
(`render_mounting_print.py` mit SUPPORT-Zone und Steckrichtungen, `render_mounting_drawing.py`,
`render_mounting_proposal.py`) bleiben in `hardware/scripts`.

Die Werkzeuge sind aus PCB-Project-Template 2.0.0 übernommen; Herkunft,
Lizenz und lokale Änderungen stehen in [`tools/VENDORED.md`](tools/VENDORED.md).
Regeln für automatisierte Änderungen: [`AGENTS.md`](AGENTS.md).
