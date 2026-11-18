# RoverCore VCU Rev1 – erste funktionale Platzierung (Stand 2026-11-16)

**Status: vorläufiger Platzierungsvorschlag mit Probe-Routing des Servoreglers.**
- Keine Fertigungsfreigabe. Geroutet ist nur der Servoregler (3b), die
  übrige Platine nicht.
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
- **Import und Platzierung getrennt (Stand 2026-11-16, nach Owner-Review).**
  Ein normaler Lauf ist ein reiner Abgleich und verändert nichts, was schon auf
  der Platine liegt:
  - Er bewegt keine Positionen, Seiten oder Drehungen.
  - Kontur, Zonen, Leiterbahnen und Zeichnungen bleiben unverändert.
  - Neue Footprints werden rechts außerhalb der Kontur abgelegt und gemeldet.
  - Footprints ohne Symbol werden entfernt, ausgenommen „board only“.
  - Bei geänderter Bibliotheks-ID wird der Footprint getauscht; Lage, Seite,
    Drehung und Sperre bleiben.
  - **Vollständig synchronisiert:**
    - Netze: jedes Pad bekommt genau das Netz der Netzliste; Pads ohne Eintrag
      (z. B. mechanische Pads) bekommen kein Netz.
    - Felder: Symbolfelder werden gesetzt. Felder, die das Symbol nicht mehr
      hat, werden entfernt; die Felder des Bibliotheks-Footprints bleiben.
    - DNP und BOM-Ausschluss werden gesetzt **und** zurückgenommen.
  - **Abbruch vor dem Speichern**, die Datei bleibt dann unverändert:
    - Footprint nicht ladbar;
    - Netzlistenpin ohne Pad;
    - unbekannte Referenz im Layout;
    - Packungsüberlauf;
    - nicht platziertes Bauteil (bei Bootstrap).
  - Die vorläufige Platzierung gibt es nur ausdrücklich mit `--bootstrap`,
    auf ein Blatt begrenzbar mit `--sheet NAME`.
    - Ihre Zeichnungen (Kontur, Gruppenrahmen, Bohrungsmarken, Hinweise)
      liegen in der Gruppe `bootstrap_layout`. Nur diese ersetzt Bootstrap.
    - Bootstrap überschreibt die Positionen der betroffenen Footprints, auch
      eine manuelle Feinplatzierung. Nach Beginn der manuellen Arbeit im
      Editor nur noch gezielt mit `--sheet` verwenden.
  - **Tests** (`qa/tests/test_build_board.py`, auf einer Kopie der Platine):
    - Ein Abgleich erhält eine manuelle Verschiebung, einen Seitenwechsel und
      eine Zeichnung.
    - Er stellt ein falsches Pad-Netz wieder her, entfernt das Netz eines
      mechanischen Pads, nimmt DNP und BOM-Ausschluss zurück und fügt einen
      gelöschten Footprint wieder ein.
    - Ein Layout mit unbekannter Referenz bricht ab, ohne die Datei zu
      verändern.
  - Der Abgleich auf dem aktuellen Stand meldet keine Änderung.
  - Die 22 ungruppierten Zeichnungen des ersten Laufs wurden einmalig durch
    die Gruppe ersetzt. Die Footprint-Positionen sind dabei unverändert
    geblieben (Positionsliste vorher/nachher verglichen).
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
- **Elektrische Feinplatzierung LTC7803 (2026-11-16):** Die Bauteile sitzen
  an ihren Pins. Die Pad-Lagen sind aus der Platine ausgelesen; Abstände sind
  Pad-Mitte zu Pad-Mitte (Schätzung für den späteren Leiterweg).

| Funktion | Bauteile | Lage | Abstand zum Pin |
|---|---|---|---|
| Boost | C411 (BOOST–SW), D401 (INTVCC→BOOST) | C411 rechts oben an U401, SW-Pad zu den Source-Pins von Q401; D401 seit dem Probe-Routing auf der Unterseite (3b) | C411 BOOST ↔ Pin 14 ca. 3,1 mm; C411 SW ↔ Q401-Source ca. 4,0 mm |
| INTVCC | C412 4,7 µF, C413 1 µF | direkt unter den Pins 9/10, GND-Pad zur GND-Seite | ca. 1,7 mm |
| Soft-Start | C414 | links oben an Pin 1 | ca. 3,5 mm |
| Strommessung | CF401 (SENSE+/−), RF401 (SENSE_P_K → SENSE+) | links an Pin 2/3; Filter am IC, lange Leitung vor dem Filter | CF401 ca. 3,0 mm |
| Rückkopplung | R404 (VFB→GND), R403 (VFB_TAP→VFB) | links an Pin 4; GND-Ende neben den GND-Pins 7/8 | R404 ca. 3,0 mm |
| Kompensation | C419 (ITH→GND), R413/C418 (ITH-RC) | unter Pin 5, abseits von SW und den Gate-Leitungen | C419 ca. 3,3 mm |

- **Verbleibende Kompromisse** (aus dem Pinbild von LTC7803 und TDSON-8 mit
  der gewählten SW-oben-Anordnung):
  - **TG kurz:** Q401-Gate ↔ Pin 15 ca. 6,9 mm.
  - **BG lang:** Q402-Gate ↔ Pin 13 ca. 13,8 mm Luftlinie. Die frühere
    Angabe „Innenlage über GND“ passt nicht zum Lagenaufbau (In2 liegt
    1,24 mm unter In1). Ausgeführt ist BG auf B.Cu über In2-GND, siehe 3b.
  - Eine Anordnung mit beiden Gates nahe am IC ergäbe eine größere
    Leistungsschleife (Kondensatoren nicht mehr zwischen VIN-Drain und
    GND-Source). Die Leistungsschleife hat Vorrang.
- **SENSE± von RS401 (Kelvin NT401/NT402) zu U401:** ca. 39 mm Luftlinie;
  geroutet ca. 44 mm, siehe 3b. Filter RF401/CF401 am IC.
- **Rückweg:** Die Luftlinien zeigen nur Verbindungen. Der vorgesehene
  Rückstromweg steht in 3a, die Kupferführung in 3b. Ein Abstand von 5 mm
  zwischen GND-Pads beschreibt nur die Geometrie.

**Logikversorgung (Gruppe 2):**
- U301 ist um 180° gedreht, damit VIN/GND/SW zur Leistungsseite zeigen.
- C301 liegt quer über VIN/GND; die SW-Leitung führt zwischen seinen Pads zu
  L301. Die Ausgangs-C liegen rechts.
- Der Boot-C C303 liegt an BOOT/SW; FB-Teiler R301–R303 links, abseits von
  L301.

**Eingang (Gruppe 1):**
- Stromweg J101 → F101 → Q101 → D101/C101/C102 ohne Umweg.
- VBAT_PROT geht nach rechts (Servoregler) und nach unten (U301) ab.

## 3a. Lagenaufbau und vorgesehene Rückstromwege (2026-11-16)

**Lagenaufbau – Fertigungsvorgabe seit 2026-11-18** (in der Board-Datei eingetragen; noch keine bestätigte
Fertigungseigenschaft – erst die Bestellung bzw. die schriftliche Zusage des Fertigers macht daraus eine):

| Lage | Dicke | Rolle |
|---|---|---|
| F.Cu | 35 µm | Bauteile; Leistungsflächen VBAT_PROT, SW, ISNS_PWR, VSERVO_REG, lokale GND-Flächen; kurze kritische Leitungen (TG/SW-Paar, Bootstrap, IC-Umgebung) |
| Prepreg | 0,1 mm | – |
| In1.Cu | 17,5 µm | **GND, durchgehend, ohne Leitungen**; Bezugs- und Rückstromebene für F.Cu |
| Kern | 1,265 mm | – |
| In2.Cu | 17,5 µm | **GND, durchgehend** (vorerst); Bezugsebene für B.Cu |
| Prepreg | 0,1 mm | – |
| B.Cu | 35 µm | C403/C404, D401; Leitungen BG, Sense-Paar, Rückkopplung, EXTVCC; später weitere Signale und Leistungsflächen parallel zu F |

- **Folgerung aus dem Aufbau:** Eine Leitung ist nur an die Ebene im Abstand
  von 0,1 mm eng gekoppelt, F an In1 und B an In2. In1 und In2 sind
  1,24 mm voneinander entfernt. Eine Leitung auf In2 wäre deshalb schlecht an
  In1 gekoppelt und würde zugleich die In2-Ebene zerschneiden.
- **Fertigerseitig offen:** Ein Aufbau mit ca. 0,1 mm Prepreg ist vor der
  Bestellung zu bestätigen. Bei dickerem Prepreg steigt die
  Leitungsinduktivität etwa proportional (Schätzung).
- **Leistungsinseln auf In2** (z. B. VBAT_PROT- oder +V_SERVO-Verteilung)
  nur außerhalb von Bereichen mit B-Leitungen. Entschieden wird beim Routing
  der übrigen Platine.
- **Festlegung Kupfer und Hülsen (2026-11-18):**
  - Außenlagen 35 µm Endkupfer (1 oz), Innenlagen 17,5 µm (0,5 oz),
    Prepreg 0,1 mm, Kern 1,265 mm, Gesamtdicke ca. 1,6 mm. Das entspricht
    dem veröffentlichten 4-Lagen-Standardaufbau von JLCPCB (Prepreg
    2313/3313); bei der Bestellung als Aufbau auswählen und bestätigen.
  - **Kein 70-µm-Außenkupfer:** Die Platine ist mit 0,15 mm Abstand und
    0,2-mm-Leitungen an den 0,5-mm-Raster-ICs (U401, U506) geroutet; dicke
    Außenlagen verlangen gröbere Mindestabstände und damit ein Neurouting.
    Die Servoschiene ist mit 35 µm gerechnet (3j).
  - **Hülsenkupfer:** Vorgabe IPC-6012 Klasse 2 (Mittel ≥ 20 µm, dünnste
    Stelle ≥ 18 µm). JLCPCB veröffentlicht keinen garantierten Wert; die
    Vorgabe ist bei der Bestellung schriftlich zu bestätigen. Alle
    Rechnungen verwenden 18 µm.
  - **Geltungsbedingung:** Alle Strom- und Thermikrechnungen dieses
    Berichts gelten nur unter der Voraussetzung, dass die Bestellung genau
    diesen Aufbau bzw. vereinbarte Mindestwerte (Endkupfer außen ≥ 35 µm,
    innen ≥ 17,5 µm, Hülse an der dünnsten Stelle ≥ 18 µm) abdeckt.
    Weicht der Auftrag ab, sind die Rechnungen zu wiederholen.

**Vorgesehene Rückstromwege** (die Kupferführung dazu steht in 3b):

| Kreis | Hinweg | Rückweg |
|---|---|---|
| Eingangsschleife | C405/C401/C402 → VBAT-Fläche F → Q401 → SW-Fläche F → Q402 | GND-Fläche F (Source Q402 → GND-Pads der Kondensatoren), In1 direkt darunter |
| Eingangs-C Unterseite | C403/C404 über je 4 VBAT-Vias (0,8/0,4 mm) neben Pad 1 | je 4 GND-Vias neben Pad 2 zu In1/In2 und F |
| TG | Pin 15 → Q401-Gate (Pin 4), F | SW von Pin 16 als Nachbarleitung zur Q401-Source (Pin 3), F |
| BG | Pin 13 → F → Via → B → Via → F → Q402-Gate | In1 unter dem F-Stück, In2 unter dem B-Stück; Ebenenwechsel über GND-Vias direkt neben beiden BG-Vias |
| Bootstrap | Pin 14 → C411 → SW-Steg zur Q401-Source; Nachladen INTVCC → D401 (B) → BOOST | über SW und Q402 zu GND, INTVCC-C C412/C413 mit eigenen GND-Vias |
| Strommessung | Kelvin RS401 → Paar auf B → RF401/CF401 am IC | differenziell; Bezug In2, zwei GND-Ebenen zwischen Paar und SW/L401 |
| Rückkopplung | VFB_TAP (niederohmig, Ausgangsspannung) lang auf B → Teiler R403/R404 am IC | In2; GND-Ende von R404 mit eigenem Via |
| Kleinsignal-GND | C414, R404, C419, C418, C412, C413 | je ein Via zu In1/In2; U401-EP über seine Vias, vollflächig an die Ebenen angebunden |

## 3b. Probe-Routing Servoregler (2026-11-16)

- **Werkzeug:** `hardware/scripts/route_servo_trial.py`, einmalig auf
  `RoverCore.kicad_pcb` angewendet.
  - Alle Leitungen, Vias und Flächen liegen in der Gruppe
    `servo_trial_routing`. Im Editor lassen sie sich als Block auswählen,
    ändern oder löschen.
  - Das Skript bricht ab, wenn die Gruppe schon existiert, wenn Lock-Dateien
    vorliegen oder wenn auf den betroffenen Netzen schon Kupfer liegt. Es
    überschreibt also keine Handarbeit.
  - Ab jetzt wird im Editor weitergearbeitet. **`build_board.py --bootstrap`
    wird nicht mehr angewendet.**
  - Der normale Abgleich erhält das Routing; auf einer Kopie geprüft:
    Leitungen, Flächen, Gruppen, D401-Seite und RS402-Drehung bleiben
    unverändert.
- **Umfang:**
  - Eingangsschleife mit GND-Rückweg;
  - TG und BG mit ihren Rückwegen;
  - Bootstrap;
  - INTVCC und EXTVCC;
  - Kelvin-Sense;
  - Rückkopplung und Kompensation;
  - SW-, ISNS- und VSERVO_REG-Flächen bis zu RS402;
  - GND auf In1 und In2 über die ganze Platine.
- **Nicht geroutet:**
  - VBAT_PROT-Zuleitung von Q101 zur Stufe;
  - +V_SERVO von RS402 zu J102–J105;
  - INA240-Eingänge;
  - RUN-Netz hinter dem Ausbruch-Via;
  - Messteiler;
  - übrige Platine.
- **Platzierungsänderungen, die das Routing erforderte** (keine Schaltungsänderung):
  - **D401 auf die Unterseite** (47,2 | 18,35). Auf der Oberseite lag D401
    mit dem TG-Ausgang in der Schleife Pin 16 (SW) – C411 – Pin 14 (BOOST)
    und hatte keine kreuzungsfreie Verbindung. Jetzt: BOOST-Via → D401 →
    INTVCC-Via → C413.
  - **RS402 um 90° gedreht** (84,5 | 24,5), Pad 1 VSERVO_REG nach Westen,
    Pad 2 +V_SERVO nach Osten zu J102–J105. Vorher lag das Ausgangspad
    zwischen den Ausgangskondensatoren und Pad 1; der Reglerstrom hätte am
    Ausgangspad vorbeigeführt werden müssen.
  - **NT403/NT404/NT405** an die unteren Enden der Shuntpads. Der Strom tritt
    oben ein und aus, die Abgriffe liegen damit abseits des Stromwegs.
  - **C405** 0,65 mm näher an die Drain-Laschen von Q401 und die Source-Pins
    von Q402 (Courtyards gerade frei).

**Gemessene Längen** (aus den Leiterbahnen der Platine):

| Verbindung | Länge | Lagen / Vias | Bemerkung |
|---|---|---|---|
| TG Pin 15 → Q401-Gate | 9,6 mm | F | Rückleitung SW Pin 16 → Q401-Source ca. 12 mm, auf 5,1 mm Länge im Mittenabstand 0,5 mm daneben |
| BG Pin 13 → Q402-Gate | 15,3 mm | F 5,2 + B 10,1, 2 Vias | Luftlinie war 13,8 mm |
| BOOST Pin 14 → C411 | 4,4 mm | F | C411-SW-Seite über einen 0,4-mm-Steg zwischen Pinreihe und Drain-Pad von Q401 zu Pin 3 |
| SENSE_P_K (RS401 → RF401) | 44,1 mm | B 42,2, 2 Vias | Paar, 0,2 mm Leiter, 0,4 mm Abstand |
| SENSE_N (RS401 → CF401) | ca. 44 mm | B 42,4, 2 Vias | – |
| VFB_TAP (NT403 → R403) | 54,5 mm | B 52,6, 2 Vias | niederohmiger Ausgangsabgriff; Teiler am IC |
| EXTVCC (Pin 11 → VSERVO_REG) | 35,6 mm | B 31,4, 2 Vias | Versorgungsleitung, kein Messsignal |

**Prüfpunkte:**
- **BG (13,8 mm Luftlinie):**
  - Ohne Kreuzung der Eingangsschleife und ohne Vergrößerung der
    Schleife führbar, mit zwei Lagenwechseln.
  - Rückweg definiert: In1 unter dem F-Stück, In2 unter dem B-Stück.
    GND-Vias neben beiden BG-Vias bei (48,2 | 19,6) und (57,9 | 18,6).
    Kein Via, keine Aussparung unterbricht In2 unter der B-Leitung (Ansicht
    der In2-Füllung geprüft).
  - **Schätzung**, keine Messung: Leitungsinduktivität ca. 3–5 nH
    (Plattennäherung, h = 0,1 mm, b = 0,3–0,4 mm, 15 mm).
  - Nachweis erst durch Messung von V_GS an Q402 (Überschwingen,
    Miller-Einbruch beim SW-Anstieg).
  - Bewertung: Die Platzierung funktioniert für BG. Eine kürzere Führung
    gäbe es nur mit einer größeren Leistungsschleife.
- **Sense-Paar (39 mm Luftlinie):**
  - Geroutet ca. 44 mm, durchgehend als Paar auf B über In2-GND.
  - Zwischen dem Paar und der SW-Fläche bzw. L401 liegen zwei GND-Ebenen.
    Das Paar unterquert die SW-Fläche und L401 (geschirmte Bauform). Ein
    Weg abseits davon wäre deutlich länger.
  - Filter RF401/CF401 am IC.
  - Nicht nachgewiesen ist die Störfreiheit. Nachweis durch Messung der
    Stromgrenze und des SENSE-Signals am Prototyp.
  - Bewertung: führbar, mit dem genannten Restrisiko.
- **Eingangsschleife:**
  - Seitlich auf F: Q401-Source-Reihe (y ≈ 11) – SW-Fläche – Q402 –
    GND-Fläche – C405 (y ≈ 18,7) – VBAT-Fläche.
  - Fläche zwischen ca. 15 mm² (innerster Weg, x 53–55) und ca. 45 mm²
    (FET-Mitten). Das ist eine **Schätzung aus der Geometrie**.
  - Die wirksame Induktivität ist ohne Feldberechnung oder Messung des
    SW-Überschwingens nicht bestimmt.
  - In1 liegt 0,1 mm darunter und ist im Bereich der Schleife nicht
    unterbrochen (nur Via-Freistellungen).
- **VBAT_PROT-Zuleitung (noch nicht geroutet):**
  - Möglicher Korridor auf F bei y 27,6–30: ca. 2,4 mm zwischen den
    Stützbauteilen und der RUN-Gruppe. Auf B parallel dazu südlich der
    Rückkopplungsleitung (y > 28,8).
  - Eingangsstrom bei Volllast ca. 9,4 A (Schätzung: 11,2 A × 6,8 V /
    (9,0 V × 0,9)).
  - Bei 35 µm außen und 20 K Erwärmung wären ca. 4,3 mm Breite nötig
    (IPC-2221-Näherung, **Schätzung**). Das geht nur mit F und B parallel,
    oder mit einem breiteren Korridor (RUN-Gruppe bei der Feinplatzierung
    1–2 mm nach unten).
- **DRC nach dem Probe-Routing:**
  - keine Kurzschluss-, Abstands- oder Courtyard-Befunde;
  - ein erwartetes `via_dangling`: RUN-Ausbruch-Via, Weiterführung offen;
  - Silkscreen-Befunde unverändert;
  - nicht geroutete Verbindungen 442, vorher 499.
- **Offen aus dem Probe-Routing:**
  - INA240-Abgriffe: ISERV_P liegt westlich, ISERV_N östlich, Pin 8/1 von
    U402 umgekehrt. Später ein Via oder U402 anders orientieren.
  - RUN-Weiterführung von Pin 6 auf B.
  - Weitere GND-Stitching-Vias im Raster.

## 3c. Elektrische Feinplatzierung Logikversorgung, Ausgangsstufen, Controller-Peripherie (2026-11-16)

- **Werkzeug:** `hardware/scripts/fine_place_rev1.py`, einmal angewendet.
  - Es setzt nur die dort aufgeführten 113 Footprints auf ausdrückliche
    Lagen und Drehungen.
  - Es verweigert das Verschieben eines Footprints, an dem schon Kupfer
    hängt, und bricht bei Lock-Dateien ab.
  - Die Courtyard-Packung war nur der Ausgangspunkt.
- **Prüfung:**
  - Für jedes Satellitenbauteil ist geprüft, dass sein Anschlusspad zum
    vorgesehenen Pin zeigt (Pad-Abstände unten, Mitte zu Mitte, aus der
    Platine).
  - DRC: keine Courtyard-, Abstands- oder Kurzschlussbefunde.

**Logikversorgung TPS54302 (U301):**

| Funktion | Lage | Abstand |
|---|---|---|
| Eingang C301 (10 µF) | quer über VIN (Pin 3) und GND (Pin 1); SW (Pin 2) führt zwischen den Pads zu L301 | je 2,9 mm |
| C302 (100 nF) | am VIN-Pad von C301; GND-Pad mit eigenem Via zu In1 | 1,9 mm zu C301 |
| Boot C303 | direkt unter U301: BOOT (Pin 6) links, SW (Pin 2) über einen schmalen Steg zwischen den Pinreihen | 1,8 / 2,7 mm |
| L301 | 2,7 mm näher an U301 als bisher, kürzerer SW-Knoten | SW-Pad 6,2 mm von Pin 2 |
| Ausgang C304/C305/C307 | direkt hinter L301, +5V-Pads in einer Reihe | – |
| FB-Teiler R302/R303, C306 | links oben an FB (Pin 4); R301 (Messeingang +5V) davor, der Fühlerweg kommt von den Ausgangskondensatoren | R302 1,6 mm |
| EN-Teiler R305/R304 | links an EN (Pin 5); das VBAT-Ende von R304 erhält beim Routing ein Via | R305 1,7 mm |

**Ausgangsstufen (U201, Q201–Q206):**
- **U201 um 90° gedreht:** B-Seite (5 V, Pins 13–24) nach Norden zu den
  Stufen, A-Seite (3,3 V) nach Süden.
  - Abblockung: C202 an VCCB (Pins 23/24) 1,5 mm; C201 an VCCA (Pin 1)
    1,5 mm.
  - A-seitige Pull-ups/-downs R201–R209 in einer Reihe direkt unter ihren
    Pins (2,8–6,6 mm).
  - B-seitige LED-Pull-downs R216–R218: 2,5–3,7 mm.
- **Je Kanal eine Spalte, in der Reihenfolge der Stecker** von West nach Ost:
  AUX1 (J104), FRONT (J102), AUX2 (J105), REAR (J103), ESC (J106).
  - Oben R22x (470 Ω, Ausgangspad zum Stecker);
  - darunter Q20x (Drain nach oben, 2,0 mm zu R22x);
  - dann D20x (+5V → PU);
  - links daneben R24x, R23x und der Gate-Pull-up R21x (2,6 mm zum Gate).
- **Kreuzungen:**
  - Die Kanalreihenfolge von U201 (ESC, FRONT, REAR, AUX1, AUX2) weicht von
    der Steckerreihenfolge ab.
  - Die Gate-Leitungen zwischen U201 und den Stufen brauchen daher beim
    Routing Lagenwechsel.
  - Bewusst gewählt: Die Leitungen zum Stecker (Kabelseite) bleiben direkt.
- **Längere Wege:**
  - R222 → J102 und R223 → J103 ca. 10 mm, weil die AUX-Stiftleisten
    J104–J106 zwischen den Micro-Fit-Steckern und den Stufen liegen.
  - Q206 (OUT_LOCK-Klemme) an ESC_DRV ca. 8 mm.
- **U204 und R501** (Pull-up an ACT_OE_N, Blatt Controller) westlich von
  U201. C203 an VCC (3,3 mm).

**Controller-Peripherie** (unter dem DevKit, nur flache SMD), nach Funktion
gruppiert:

| Block | Bauteile | Abstände |
|---|---|---|
| 5-V-Einspeisung DevKit | D501 und TP503 neben DevKit-Pin 21 (jetzt im Gruppenrahmen 4, westlich der Buchsenleiste) | D501 → Pin 21 3,5 mm |
| 3V3-Wächter | U504, C505 an VDD, R510 an RESET | je 1,8 mm |
| Akkuverlust-Wächter | U505, C507 an VDD, SENSE-Knoten C506/R516/R515 an Pin 5, R517 an Pin 1 | 1,8–4,1 mm |
| Taster → Latch-Takt | U507, C510, Entprellung C511/R502/R518 am Eingang | 1,7 / 2,7 mm |
| VBAT_OK-Puffer, Latch | U508 mit C509; U506 mit C508 an VCC, R519 an Q | 1,7–2,5 mm |
| Ausgangssperre O-37 | seit 3d zwischen OLED und DevKit, nahe ihren Lasten U204/Q206: D507/R520/C512 (LOCK_SUP-Erzeugung), U515/U516 mit C513, Teiler R521/R522 an U516-SENSE, R523 zwischen den RAILS_OK-Pins, Q507/R524/TP506 darunter | 1,6–3,1 mm |
| VBAT-Messung | Q505 mit R508, Q506 mit R509, Teiler R505/R506/C504/R507 als Kette, D506 am Teilerknoten, TP505 | 1,7–5,1 mm |
| 3V3-Puffer, Messpunkte | C501/C502, TP502/TP504 (Status-LED seit 3d an ENABLE) | – |

- **Nicht feinplatziert** (weiter Courtyard-Packung):
  - Eingangsschutz (Gruppe 1);
  - RUN- und Messgruppe des Servoreglers (Q403–Q408, Teiler);
  - Sensoren/Display (Gruppe 6);
  - Schnittstellen (Gruppe 7).

## 3d. Bedienzone, Zugänglichkeit und Beschriftung (2026-11-16, Owner-Review)

Anlass: Die Taster lagen in einer engen Reihe direkt am USB-Ende des DevKits.
Darunter war die Controller-Elektronik bis an die Kante verdichtet, und viele
Referenzen überlagerten sich. Die Leistungsstufe (3b) ist unverändert.

**Bedienzone:**
- **ENABLE (SW501) mit Status-LED (D502, R504)** im freien Streifen über dem
  OLED-Sockel, Mitte (81,5 | 53).
- **Servicegruppe RESET (SW502) und BOOT (SW503)** zwischen OLED und DevKit
  bei (101,5 | 55) und (113,5 | 55).
  - Abstand untereinander 12 mm. Das macht versehentliches gleichzeitiges
    Drücken unwahrscheinlicher; ausschließen lässt es sich damit nicht.
  - 20 mm Abstand zu ENABLE, eigene Beschriftung.
- **Prüfkriterium Fingerzugang** (eigenes Kriterium, Schätzung, keine Norm;
  es ersetzt nicht die Prüfung am Muster):
  - Fingerkuppe ca. 16 mm. Im Umkreis von 10 mm um die Tastermitte steht
    nichts Hohes.
  - Als hoch gelten die Modulhüllen, der USB-Steckerraum und L401, C406,
    C407, C101 sowie die Stecker.
  - Die Taster sind laut KiCad-Modell nur 1,54 mm hoch.
  - Die M3-Marken gelten als niedriges Hindernis (Schraubenkopf): 4 mm
    Freiraum zum Courtyard.

| Taster | nächstes hohes Objekt | Abstand | M3-Marke zum Courtyard |
|---|---|---|---|
| ENABLE | OLED-Modulhülle | 10,4 mm | 33,7 mm |
| RESET | OLED-Modulhülle | 11,4 mm | 15,0 mm |
| BOOT | DevKit-Hülle | 10,7 mm | 6,9 mm |

- **Hüllen und Annahmen** (in den Ansichten blau, alle Höhen geschätzt):
  - **DevKit:** F.Fab-Umriss des Footprints, ca. 13 mm hoch. Die
    Sockelhöhe ist offen (O-4).
  - **OLED und IMU:** je ca. 11 mm (Sockelkörper 8,51 mm laut
    Footprint-Beschreibung, plus Modul).
  - **USB-Steckerräume (korrigiert):** Die erste Fassung dieses Abschnitts
    nahm USB-C an. Das war falsch.
    - ESP32-S3-DevKitC-1 v1.1 hat zwei **Micro-USB**-Buchsen ("USB-to-UART
      Port: A Micro-USB port", Espressif User Guide v1.1).
    - Lage aus `DXF_ESP32-S3-DevKitC-1_V1.1_20220429.dxf`, ausgewertet in
      `rev1-versorgung-und-boardwahl.md` 2.3: an der unteren Modulkante,
      "UART" x 2,4–9,6 mm und "USB" x 15,8–23,0 mm (DXF-Koordinaten).
    - Auf der Platine: Buchsenmitten x = 130,2 und 143,6, Kante y = 63,84.
    - Je Buchse ein Steckerraum 11 mm breit, 30 mm lang, z 7,9–14,9 mm.
      Steckergröße und Höhe sind **geschätzt** (Sockelhöhe O-4 offen).
    - Verbindlich werden die Maße erst, wenn das gekaufte Board v1.1 mit
      Messschieber nachgemessen ist (O-4). Bis dahin ist der USB-Zugang nur
      vorläufig geprüft.
  - Unter dem Steckerraum liegen nur flache SMD-Teile, keine Taster.
  - Bestätigt ist die Zugänglichkeit damit nicht: Das ist nur am Muster mit
    gestecktem DevKit und Kabel möglich.
- **M3-Marken:** Eine Prüfung aller Courtyards gegen die vorläufigen
  M3-Marken (4 mm) fand zwei Konflikte:
  - D502 lag auf der Marke (146,5 | 96,5);
  - J108 lag 2 mm neben (3,5 | 96,5).

  Behoben: Die LED-/UART-Stecker J108–J112 sitzen 2 mm weiter östlich.

**Befestigungsfreiraum (vorläufige M3-Marken, 2026-11-16):**
- **Kriterien** (eigene Annahmen, Schätzung):
  - M3, Kopf ca. Ø 5,5–5,7 mm (ISO 4762 / ISO 7380), Scheibe ISO 7089
    Ø 7,0 mm.
  - Scheibenauflage r = 3,5 mm frei von Bauteilen.
  - Werkzeug (Innensechskant oder Schraubendreher von oben) und Montage:
    Courtyard ≥ 4,5 mm von der Lochmitte, bei hohen Teilen (Stecker,
    Module) ≥ 5,5 mm.
  - Lochmitte ≥ 4,0 mm vom Platinenrand, damit die Scheibe ganz aufliegt.
- **Gemessen** wird von der Lochmitte zur nächsten Kante des Courtyards
  (Bauteilkörper + 0,25 mm).
  - Die frühere Angabe 3,8 mm für J101 war genau dieser Abstand.
  - Zum Gehäuse von J101 (F.Fab-Umriss) waren es 4,3 mm. Die Scheibenkante
    lag damit nur 0,8 mm vom Steckergehäuse entfernt.

| Marke | nächstes Courtyard | Abstand | Rand | Bewertung |
|---|---|---|---|---|
| alt (3,5 \| 3,5) | J101 XT30 (hoch) | 3,8 mm | 3,5 mm | nicht erfüllt → **verschoben** |
| **neu (21,0 \| 4,0)** | J101 | 5,75 mm | 4,0 mm | erfüllt |
| (3,5 \| 96,5) | J108 JST-PH (hoch) | 4,0 mm | 3,5 mm | nicht erfüllt |
| (146,5 \| 96,5) | TP504 (flach) | 4,75 mm | 3,5 mm | Abstand erfüllt, Rand 0,5 mm zu knapp |
| (118,0 \| 66,0) | U516 (flach) | 4,47 mm | – | knapp (0,03 mm) |

- Die XT30-Marke liegt jetzt 17,5 mm von der Ecke entfernt an der
  Oberkante. Die Eckstütze entfällt dort, bis das Chassis die Lage festlegt.
- Die übrigen drei Marken sind nicht verschoben. Das entscheidet der Owner
  mit dem Chassis.
  - Vorschlag für (3,5 | 96,5): auf (4,0 | 68,0) am linken Rand; dort
    liegt das nächste Courtyard ca. 7,9 mm entfernt.
- Es sind nur Kommentarmarken; gebohrt wird nichts. Sperrflächen auf den
  GND-Ebenen und ein Montagepad folgen mit der endgültigen Lage.

**Controller-Elektronik vom Rand zurückgenommen und entzerrt:**
- Courtyards ≥ 2 mm vom Platinenrand und ≥ 4 mm von der M3-Marke.
- Gruppen nach Verbindung:
  - Wächter 3V3/Akkuverlust;
  - Taster-Puffer mit Entprellung am Eingang;
  - VBAT_OK-Puffer und Latch;
  - VBAT-Messkette.
- Die Ausgangssperre O-37 sitzt jetzt in der freien Fläche zwischen OLED und
  DevKit, nahe U204/Q206, statt in der Ecke.
- **Ausgangsstufen:** Zwischen den Reihen jeder Kanalspalte liegen jetzt
  1,3 mm für Referenzen. U201 und die A-Reihe sitzen entsprechend tiefer.
  Die AUX-/ESC-Stiftleisten liegen 1,5 mm tiefer, damit zwischen Micro-Fit
  und Stiftleisten zwei Beschriftungsreihen Platz haben.
- **Schnittstellengruppe:** Die Reihen sind nur auseinandergezogen, damit
  die Referenzen lesbar sind. Das ist weiter die Courtyard-Packung, keine
  Feinplatzierung.

**Beschriftung** (`hardware/scripts/silk_cleanup.py`):
- **Funktionsnamen** auf F.Silkscreen in der Gruppe `function_labels`:
  - Taster: ENABLE, RESET, BOOT (1,5 mm); STATUS an D502.
  - Anschlüsse: AKKU 3S, SERVO V(orne), SERVO H(inten), AUX1, AUX2, ESC,
    iBUS, LED1–LED4, UART, IMU, OLED (1,2 mm).
- **Referenzen:**
  - 0,8 mm Höhe (Mindestwert der Boardregeln), je am nächsten freien Platz.
  - Kein Pad (+0,2 mm), keine andere Silkscreen-Linie oder -Schrift
    (+0,15 mm), kein fremder Bauteilkörper, 0,5 mm vom Rand.
  - Ergebnis: 219 Referenzen gesetzt, **34 ausgeblendet**, weil kein freier
    Platz ohne Überlagerung bleibt.
  - Betroffen sind vor allem die fünf gleichartigen Kanalspalten der
    Ausgangsstufen (R22x–R24x, Q20x) und Teile der Schnittstellenreihen.
  - Alle ausgeblendeten Referenzen stehen weiter auf der Bestückungslage
    (F.Fab).
  - Ausgeblendet: C201 C511 C604 C606 C607 C610 D205 D602 D607 Q202 Q203 Q205
    Q506 R204 R209 R216 R222 R223 R225 R231 R232 R233 R234 R235 R241 R242
    R243 R245 R412 R414 R506 R606 R608 R609.
- **DRC Silkscreen:** 0 Überlappungen, 0 Silk über Kupfer und 0 Randbefunde
  (vor dieser Etappe 199 Überlappungen, 171–199 über Kupfer, 3–8 am Rand).
  - Die 17 Pinbeschriftungen der Projekt-Footprints J115/J116 (0,6 mm,
    unter Mindesthöhe) sind bereinigt.
    - Jetzt 0,8 mm hoch, abwechselnd außerhalb und innerhalb der Pinreihe,
      weil 0,8-mm-Namen nebeneinander nicht in das 2,54-mm-Raster passen.
    - Die Namen bleiben auf dem Silkscreen, weil sie beim Messen und beim
      Stecken der Module die Anschlüsse zeigen.
    - Reine Detailtexte (Sockeltyp, "no standoff", Modulbezeichnung) standen
      schon auf F.Fab.
  - Geändert sind Generator (`make_sensor_module_sockets.py`), Bibliothek
    und die zwei Platinen-Instanzen, gleich wie die Bibliothek.
    `text_height` ist damit 0.
- **Bestückungszeichnung:** Jedes der 253 Bauteile hat seine Referenz auf
  der Fab-Lage oder dem Silkscreen (geprüft).
  - 248 Footprints tragen eine Fab-Referenz, darunter alle 34 mit
    ausgeblendeter Silk-Referenz.
  - Die fünf Net-Ties NT401–NT405 haben keine Fab-Referenz (KiCad-Bibliothek);
    ihre Silk-Referenzen sind sichtbar.

**Fehlende 3D-Modelle** (in den Ansichten rot gekennzeichnet):
- Kein Modell zugewiesen: BZ101, J115, J116, U501.
- Modelldatei fehlt: D601–D604, D606–D608, J101, J102, J103, Q101, Q401,
  Q402.
- Die KiCad-3D-Renderings zeigen diese Teile nicht. Deshalb gibt es
  zusätzlich die Hüllenansicht.

## 3e. Elektrische Feinplatzierung Eingangsschutz und Schnittstellen (2026-11-16)

Gleiches Werkzeug wie in 3c (`fine_place_rev1.py`, Gruppen `input` und
`interfaces`). Die Servoleistungsstufe ist unverändert. Pad-Abstände sind
Mitte zu Mitte, aus der Platine.

**Eingangsschutz:**
- **Stromweg von links nach rechts:** J101 → F101 → Q101.
  - Q101 ist um 180° gedreht. Seine VBAT_PROT-Pins (1–3) zeigen nach Osten,
    direkt in den Zuleitungskorridor zur Servostufe (y 27,6–29,9, siehe
    3b).
  - Vorher zeigten sie nach Süden, und die Zuleitung hätte den Drain-Bereich
    (VBAT_FUSED) umgehen müssen.

| Verbindung | Abstand |
|---|---|
| J101 Pin 2 → F101 Eingang | 7,9 mm |
| F101 Ausgang → Q101 Drain | 6,9 mm |
| Q101 Source → D101 (TVS) | 4,1 mm |
| Q101 Source → C102 | 8,0 mm |
| D101 → C101 (Puffer, Richtung Logikversorgung) | 10,9 mm |

- **Gate-Beschaltung:** D102 und R101 liegen nördlich von Q101.
  - D102 ist so gedreht, dass Gate- und VBAT-Leitung zum Pinblock nicht
    kreuzen. Das Gate-Pad liegt deshalb auf der abgewandten Seite: 5,1 mm
    zu Pin 4, bewusst.
- TP101 sitzt jetzt am Sicherungseingang, TP102/TP103 am VBAT_PROT-Knoten.

**Schnittstellen:**
- **Je Stecker eine Spalte:** ESD-Diode direkt am Signalpin (4,2 mm),
  darüber der Serienwiderstand (2,6 mm zur Diode). Das gilt für LED1–LED4
  und für UART TX/RX. Der RX-Pull-up R617 sitzt neben R616.
- **Schaltblöcke**, Abblockung je 1,8–2,5 mm am Pin:
  - LED-Versorgung U601 zwischen J108 und J111;
  - LED4-Pegelwandler U202 an J111;
  - UART-Versorgung U602 an J112;
  - iBUS-Versorgung U603 und Puffer U203 an J107.
- **J107 (iBUS) 5 mm nach Norden**, damit die UART-Spalte an J112 Platz hat.
  D606 sitzt an Pin 1.
- **Summerblock** (BZ101, Q601, R611/R612, D605) in der freien Fläche
  darüber. D605 ist leicht verschoben, weil die Plus-Markierung des
  BZ101-Footprints sonst auf seinem Pad lag.
- **DRC:** keine Courtyard-, Abstands- oder Silkscreen-Befunde.
  - Referenzen: 216 gesetzt, 37 ausgeblendet; alle stehen auf F.Fab.

## 3f. Routing Schritt 2: Eingang, VBAT_PROT-Verteilung, Logikversorgung (2026-11-16)

- **Werkzeug:** `hardware/scripts/route_input_logic.py`, einmal angewendet.
  - Alle Teile liegen in der Gruppe `input_logic_routing`.
  - Gleiche Schutzregeln wie in 3b: Abbruch, wenn die Gruppe schon
    existiert oder auf den nur hier gerouteten Netzen Kupfer liegt.
  - Die Servoleistungsstufe ist unverändert.
- **Eingang:**
  - VBAT_IN (J101 → F101) und VBAT_FUSED (F101 → Q101-Drain) als Flächen
    auf F und B, mit 4 bzw. 5 Vias verbunden.
  - Ausgelegt auf ca. 10 A Eingangsstrom bei Volllast. Schätzung:
    Servostrom aus 3b plus Logikversorgung; die Fläche ist ca. 9 mm breit.
- **Q101-Gate:**
  - Gate-Leitung oberhalb des Drain-Bereichs zu Pin 4, 10 mm.
  - VBAT-Seite von D102 östlich von Pin 4 zu Pin 3, ohne Kreuzung.
  - R101 mit eigenem GND-Via.
- **VBAT_PROT:**
  - Knotenfläche an den Source-Pins mit D101 (TVS), C102, C101 und TP102.
  - Zuleitung zur Servostufe:
    - F: Korridor y 26,9–29,9, ca. 2,3 mm nutzbar zwischen den
      Stützbauteilen und der RUN-Gruppe;
    - B: parallele Fläche y 29,1–35,4 (ca. 6 mm), südlich der
      Rückkopplungsleitung;
    - verbunden über je 4 Vias an beiden Enden.
  - Damit ist der in 3b genannte Engpass (4,3 mm bei 35 µm, Schätzung)
    durch F und B zusammen abgedeckt. Die Erwärmung ist nicht gemessen.
  - Zur Logikversorgung: 1-mm-Leitung von C101 zu C302/C301, für ca. 2 A
    Eingangsstrom (Schätzung).
- **TPS54302 lokal:**
  - Eingangsschleife C301/C302 direkt an VIN/GND, GND-Vias an C301 und
    C302.
  - SW zwischen den C301-Pads zu L301, 9,6 mm.
  - Boot-Kondensator: SW-Steg zwischen den Pinreihen, 1,8 mm BOOT-Seite.
  - FB-Teiler am Pin (5,1 mm). Der +5V-Fühler kommt auf B von C307
    (Kelvin am Ausgang, ca. 34 mm über In2-GND).
  - EN-Teiler am Pin; das VBAT-Ende von R304 geht über B zu C302.
  - Ausgangs- und GND-Flächen unter C304–C307 mit Vias; TP301/TP302
    angebunden.
- **DRC:** keine Abstands-, Kurzschluss- oder Silkscreen-Befunde.
  - Nicht geroutete Verbindungen 394, vorher 442.
  - Erwartet bleibt das RUN-Ausbruch-Via.
- **Noch nicht geroutet:**
  - +V_SERVO von RS402 zu J102–J105;
  - +5V- und +3V3-Verteilung;
  - VBAT_PROT zu den übrigen Verbrauchern (RUN- und Messteiler,
    Controller, O-37);
  - alle Signale;
  - GND-Vias der übrigen Bauteile.

## 3g. Bestückte Ansicht, Modellstatus und Lückenanalyse (2026-11-16)

**Werkzeug:** `hardware/scripts/render_populated_review.py`.
- Es rendert mit dem KiCad-3D-Renderer eine **Kopie** der Platine in
  `qa/generated/populated/` (erzeugt, nicht versioniert).
- Ansichten mit Beschriftung:
  - `populated_top`, `populated_bottom`, `populated_iso`: alle bestückten
    Teile plus gestecktes DevKit, OLED und IMU;
  - `without_modules_top`, `without_modules_iso`: Buchsenleisten sichtbar,
    Module entfernt;
  - `gap_map`.
- **Hüllkörper** gibt es nur in dieser Kopie: einfache Quader, magenta für
  Carrier-Teile, blau für die Module. Es sind **keine Herstellermodelle**.
  Sie stehen nie in der Bibliothek oder in `RoverCore.kicad_pcb`.
- **Buchsenleisten von DevKit, OLED und IMU** tragen jetzt das generische
  KiCad-Bibliotheksmodell `PinSocket_1x22/1x09/1x08_P2.54mm_Vertical`
  (nicht das Samtec-Teil).
  - Gesetzt in Generator, Bibliothek und Platine; die Ausrichtung ist im
    Rendering geprüft.

**Status je Position** (`qa/generated/populated/model_status.csv`, alle 253 Footprints):

| Status | Anzahl | Positionen |
|---|---|---|
| Bibliotheksmodell vorhanden | 213 | – |
| generisches Buchsenleisten-Modell + Modul-Hüllkörper | 3 | U501 (DevKit), J116 (OLED), J115 (IMU) |
| Hüllkörper, Bibliotheksdatei fehlt in dieser KiCad-Installation | 13 | J101, J102, J103, Q101, Q401, Q402, D601–D604, D606–D608 |
| Hüllkörper, kein Modell zugewiesen | 1 | BZ101 |
| kein Körper (Testpunkt-Pad, Net-Tie) | 23 | NT401–NT405, TP101–TP103, TP301/TP302, TP401–TP403, TP501–TP506, TP601/TP602, TP801/TP802 |
| fehlt ohne Ersatz | 0 | – |

**Maße der Hüllkörper:**

| Teil | Grundfläche | Höhe | Quelle |
|---|---|---|---|
| DevKit | PCB 25,4 × 62,865 mm; WROOM-1 18 × 25,5 mm mit 6,31 mm Antennenüberstand; 2 × Micro-USB an den DXF-Lagen | PCB-Unterkante 11,0 mm, WROOM-Oberkante 15,7 mm | DXF v1.1; Sockel 8,5 mm (KiCad-Modell) + Stiftleistenkragen 2,5 mm = **Annahme** (O-4) |
| OLED (Adafruit 326) | Umriss aus Adafruit-Boarddatei | 8,51–14,71 mm | Dicke 6,2 mm laut Adafruit-Produktseite; Lage auf der Buchse angenommen |
| IMU (Adafruit 4438) | 25,4 × 17,78 mm | 8,51–13,11 mm | 4,6 mm laut Adafruit-Produktseite |
| J101 XT30PW-M | F.Fab-Umriss (Gehäuse 9,0 × 9,9 mm laut AMASS V1.2) | 5 mm | **Annahme**: Zeichnung ohne Höhenmaß |
| J102/J103 Micro-Fit 43650-0300 | F.Fab-Umriss | 10 mm | **Annahme**: Molex-Zeichnung nicht abrufbar (Zeitüberschreitung) |
| BZ101 CMT-8540S | F.Fab-Umriss | 4,0 mm | aus der Typbezeichnung; Datenblatt nicht abrufbar (HTTP 403), **nicht verifiziert** |
| Q101 / Q401 / Q402 | F.Fab-Umriss | 1,05 mm | **Annahme** |
| D601–D604, D606–D608 | 0,6 × 1,0 mm | 0,4 mm | **Annahme** |

- **Reale Modelle für die 13 Positionen:**
  - Die Footprints verweisen auf Dateien der offiziellen
    KiCad-3D-Bibliothek, die in dieser Installation fehlen:
    - `AMASS_XT30PW-M_1x02_P2.50mm_Horizontal.step`;
    - `Molex_Micro-Fit_3.0_43650-0300_1x03_P3.00mm_Horizontal.step`;
    - `Infineon_PG-TDSON-8_6.15x5.15mm.step`;
    - `PowerPAK_SO-8_Single.step`;
    - `Texas_DPY0002A_0.6x1mm_P0.65mm.step`.
  - Mit der vollständigen KiCad-3D-Bibliothek entfällt dort der Hüllkörper
    ohne Änderung an Footprint oder Platine.
  - Herstellermodelle für DevKit, OLED, IMU und den Summer liegen nicht im
    Projekt.
  - Beides braucht einen Download und ist nicht erfolgt (Freigabe offen).

**Lückenanalyse** (`gap_map.png`):
- Als belegt gelten Courtyards, Modul- und USB-Hüllen, M3-Freiraum r 4 mm und
  die Leistungs-Kupferflächen.
- Frei sind ca. 6 200 mm² von 15 000 mm² (41 %). Darin ist der Platz für das
  noch ausstehende Routing enthalten; frei heißt also nicht verfügbar.
- Größte freie Rechtecke:

| Nr. | Größe | Lage |
|---|---|---|
| 1 | 26 × 24 mm | (34 \| 42), zwischen Servo-RUN-Gruppe und Schnittstellen |
| 2 | 28 × 20 mm | (0 \| 60), links unter der Logikversorgung |
| 3 | 34 × 10 mm | (60 \| 39), über ENABLE |
| 4 | 35 × 8 mm | (26 \| 0), Oberkante |
| 5 | 15 × 18 mm | (0 \| 30) |
| 6 | 38 × 6 mm | (60 \| 56), über dem OLED |

**Bewertung für eine kompaktere Variante** (Schätzung, noch keine Boardkopie):
- **Was die Kontur festlegt:**
  - Die Breite von 150 mm legt die obere Reihe fest: Eingang 37 +
    Servostufe 59 + Ausgangsstufen 29 + DevKit 26 mm. Diese Reihe ist
    bereits dicht und größtenteils geroutet.
  - Die Höhe von 100 mm legen drei Spalten fest:
    - OLED/IMU bis y 99 (unter der Bedienzone);
    - DevKit bis y 64 plus die Controller-Peripherie darunter bis y 98;
    - die Schnittstellen bis y 99.
- **Warum Lücken schließen allein nicht reicht:**
  - Das Zusammenschieben innerhalb der unteren Hälfte schließt Lücken, ändert
    aber keine dieser drei Spalten.
  - Die Kontur wird erst kleiner, wenn die Peripherie aus dem USB-Raum unter
    dem DevKit herausgeht und die Micro-USB-Stecker über die Unterkante
    ragen.
  - Zugleich müssen OLED/IMU mit der Bedienzone in eine gemeinsame, flachere
    Reihe.
- **Dichte:**
  - Die untere Hälfte (ca. 150 × 52 mm) trägt nur 2 600 mm² Courtyards
    (34 %), die obere Hälfte ist deutlich dichter.
  - Bei ca. 55 % Belegung in der unteren Hälfte wären ca. 150 × 85 mm
    erreichbar, 15 % weniger Fläche (**Schätzung**).
- **Vorteil:** Alle bisher gerouteten Blöcke (Servostufe, Eingang,
  Logikversorgung) liegen in der oberen Hälfte. Die Verkleinerung betrifft
  damit nur ungeroutete Gruppen.
- **Konzept K1** für die Boardkopie:
  - Peripherie in die Lücken 1/3;
  - USB über die Unterkante;
  - OLED, IMU, Bedienzone und O-37 in eine Reihe unter der Servostufe;
  - Schnittstellen in einen Block links unten (Lücke 2);
  - Kontur danach auf ca. 150 × 85 mm.
  - Die Fingerkriterien aus 3d und die Befestigung werden dabei neu
    geprüft.
- **Stand:** Noch nicht ausgeführt. Die Freigabe des Owners für K1 auf der
  Boardkopie ist offen.

## 3h. Kompaktvariante K1 auf einer Boardkopie (Versuch, 2026-11-16)

**Werkzeug:** `hardware/scripts/make_compact_variant.py`.
- Es erzeugt aus `RoverCore.kicad_pcb` die Kopie
  `qa/generated/compact/RoverCore_K1.kicad_pcb` (erzeugt, nicht
  versioniert). **Der 150 × 100-mm-Stand bleibt unverändert.**
- Mit `--compare` rendert es beide Varianten mit identischen bestückten
  Ansichten (`render_populated_review.py`) und legt sie als
  `compare_*.png` übereinander.
- **Verschoben** werden nur ungeroutete Blöcke, 91 Footprints:
  Controller-Peripherie, OLED, IMU, Taster, O-37, I²C-Pull-ups und
  Schnittstellen.
  - Teils starr als Block mit erhaltener Feinplatzierung, teils auf
    ausdrückliche Lagen.
  - Das Skript bricht ab, falls an einem verschobenen Teil Kupfer hängt.
- **Unverändert** bleiben die gerouteten Gruppen (Servostufe, Eingang,
  Logikversorgung) mit Kupfer, Vias und Rückwegen, ebenso das DevKit.

**Anordnung K1:**
- OLED direkt unter der Servo-RUN-Reihe (y 41,5–73,8).
- IMU unter den Ausgangsstufen (y 50,8–69,1).
- RESET/BOOT als Servicegruppe links neben der Logikversorgung (x 40,
  12 mm Abstand).
- ENABLE mit Status-LED an der Unterkante zwischen OLED und IMU.
- O-37 in zwei Reihen unter dem OLED, außerhalb des Modulumrisses.
- Schnittstellenblöcke unter der Logikversorgung; LED-/UART-Stecker an der
  Unterkante.
- VBAT-Messung zwischen IMU und ENABLE, Latch in die rechte Spalte.
- Kontur und GND-Ebenen auf 85 mm, M3-Marken neu gesucht.

**Vergleich** (Zahlen aus den Prüfskripten; Höhen und Fingerkriterium wie in 3d/3g
geschätzt):

| Merkmal | 150 × 100 mm (main) | K1 150 × 85 mm (Kopie) |
|---|---|---|
| Fläche | 15 000 mm² | 12 750 mm² (−15 %) |
| DRC | 1 `via_dangling` (RUN-Ausbruch), sonst keine Befunde | gleich |
| nicht geroutete Verbindungen | 394, Luftlinien gesamt 4 511 mm | 394, Luftlinien gesamt 4 471 mm |
| ENABLE: nächstes hohes Objekt | OLED 10,4 mm | IMU 11,1 mm |
| RESET: nächstes hohes Objekt | OLED 11,4 mm | C101 11,5 mm |
| BOOT: nächstes hohes Objekt | DevKit 10,7 mm | J107 (iBUS-Stiftleiste) 12,6 mm |
| Abstand RESET–BOOT / Service–ENABLE | 12 / 20 mm | 12 / 60 mm |
| Micro-USB-Stecker | ganz über der Platine (30 mm) | 21,2 mm über der Platine, ragt ca. 8,8 mm über die Unterkante (Steckerlänge geschätzt) |
| unter dem Steckerraum | flache SMD der Peripherie | 22 flache SMD (Wächter, Latch, Puffer, Testpunkte); höchste ca. 1,2 mm gegen Steckerunterkante ca. 10,4 mm (geschätzt) |
| Antennen-Sperrfläche | über der Oberkante | unverändert (DevKit nicht verschoben) |
| M3-Marken | 4, davon 3 außerhalb der Kriterien (3d) | 5, alle ≥ 4,5 mm zu Courtyards und ≥ 4 mm vom Rand |
| ausgeblendete Silk-Referenzen | 38 | 42 |

**Prüfpunkte:**
- **USB:** Die **Buchse bleibt auf dem DevKit**. Nur der eingesteckte
  Stecker mit Kabel ragt über die Unterkante.
  - Die Buchse an die Kante zu bringen hieße, das DevKit um ca. 21 mm nach
    unten zu schieben.
  - Dann läge der Antennenüberstand über der Platine statt über der
    Oberkante. Das wurde deshalb nicht gemacht.
- **M3-Marken K1:** (28 | 4), (54 | 4), (4 | 36), (91 | 81) und (145 | 81),
  Abstand zum nächsten Courtyard 5,4–12,1 mm.
  - Die Ecke unten links ist durch die Steckerreihe belegt und bleibt ohne
    Marke.
  - Ob fünf Punkte und diese Lagen zum Chassis passen, ist offen.
- **Steckrichtungen** unverändert:
  - XT30 links aus der Kante;
  - Micro-Fit oben;
  - Stiftleisten und JST-PH senkrecht.

  J107 (iBUS) steht jetzt mitten auf der Platine neben dem OLED. Der
  senkrechte Servostecker hat dort ca. 4 mm Seitenabstand zur OLED-Hülle
  (Schätzung).
- **Routingkorridore:**
  - Auf F werden die Gassen schmal: zwischen den Ausgangsstufen und der IMU
    ca. 1,3 mm, zwischen OLED und IMU ca. 1,7 mm.
  - Signale vom DevKit nach links (I²C, LED, UART, iBUS, Summer, Taster)
    laufen deshalb in K1 überwiegend auf B. B ist außerhalb des
    Servobereichs frei; die Module blockieren B nicht.
  - Das ist bis zum Routing eine **Annahme**. Die Luftliniensumme ist
    praktisch gleich.
- **Bauteile unter Modulen:** keine. O-37 liegt unter, nicht im
  OLED-Umriss; die IMU-Fläche ist frei.

**Übernahme (2026-11-16, Owner-Entscheid):**
- K1 ist seit Commit „Adopt K1“ die Arbeitsvariante in `RoverCore.kicad_pcb`,
  angewendet mit `make_compact_variant.py --main`.
- Der 150 × 100-mm-Stand ist reproduzierbar aus Commit `0b50567`
  (`git show 0b50567:RoverCore.kicad_pcb`).
- `fine_place_rev1.py` verweigert seitdem die Anwendung, weil seine Lagen zum
  150 × 100-Layout gehören.
- Die Abschnitte 3c–3e beschreiben die Feinplatzierung im 150 × 100-Layout.
  Ihre Lagen sind für die verschobenen Blöcke durch 3h ersetzt.

**Bewertung:**
- K1 funktioniert auf Platzierungsebene: DRC wie im Ausgangsstand, alle
  Taster nach dem eigenen Kriterium zugänglich, Befestigungsmarken besser
  als im Ausgangsstand.
- Nachweise fehlen noch:
  - das Routing der unteren Hälfte, besonders die schmalen F-Gassen;
  - die Steckerlängen (Micro-USB, iBUS) am realen Teil;
  - die Lage der Befestigung am Chassis.
- Bei Übernahme in `RoverCore.kicad_pcb`:
  - 91 Footprints neu setzen (Skript);
  - Kontur und GND-Ebenen;
  - M3-Marken;
  - Silkscreen neu;
  - Bericht 3c/3d/3e an die neuen Lagen anpassen.

  Die gerouteten Gruppen bleiben unberührt. Die Übernahme entscheidet der
  Owner.

**3D-Modelle (Nachtrag):**
- Die fünf Dateien, auf die die Footprints von J101, J102/J103, Q101,
  Q401/Q402 und D601–D608 zeigen, gibt es auch in der offiziellen
  KiCad-3D-Bibliothek nicht. Geprüft wurde `kicad-packages3D`, Zweig
  master; Tags 10.0.x gibt es, einen Zweig 9/10 nicht.
- Das Adafruit-CAD-Repository hat keine Modelle für die Produkte 326 und
  4438; die nächstliegenden Ordner sind andere Boards.
- Espressif bietet für das DevKitC-1 v1.1 kein 3D-Modell an.
- Es wurde daher nichts installiert. Die Hüllkörper bleiben gekennzeichnet.
- Die generischen Buchsenleisten-Modelle bestätigen weder die
  Samtec-Geometrie noch die Einsteckhöhe.

## 3i. Routing K1 (Stand 2026-11-16)

**Status (2026-11-16):** Platzierungsprüfungen bestanden, Routing
unvollständig. **Nachtrag 2026-11-18:** Alle Verbindungen sind geschlossen,
die DRC ist bestanden; Stand und Strompfadprüfung siehe 3j.

**Schritt 3 – Servoschiene +V_SERVO** (`route_servo_rail.py`, Gruppe
`servo_rail_routing`):
- Bis zu 11,2 A.
- Auf F belegen die VSERVO_REG-Flächen den Bereich nördlich von RS402.
  Die Schiene verlässt RS402 Pad 2 deshalb über ein Feld aus 12 Vias
  (0,8/0,4 mm) nach B.
- Sie läuft auf B zum 5,6 mm breiten Band zwischen den Micro-Fit-Steckern
  und den AUX-/ESC-Stiftleisten.
- Dort liegen F und B parallel, mit 7 Vias vernäht, bis zu den Pins von
  J102–J105.
- Die Signalpins J102/J103 Pin 1 laufen vorher auf F durch das Band; die
  Flächen sind um sie herum gefüllt.
- Breite und Erwärmung sind nur geschätzt (IPC-Näherung, 2 × 5,6 mm bei
  35 µm), nicht gemessen.

**Netzklasse Power** (`RoverCore.kicad_pro`):
- Gilt für +3V3, +5V, +5V_LED, +5V_EXT, +5V_RX, +5V_DEVKIT, +V_SERVO,
  VBAT_PROT und LOCK_SUP.
- 0,4 mm Leiterbreite, Via 0,6/0,3 mm.
- Der Abstand bleibt 0,15 mm, weil 0,2 mm zwischen den Pins der
  0,5-mm-Raster-ICs (U401, U506) nicht einzuhalten ist.

**Unterseite vor dem Autorouting** (aus dem B-Kupfer der Platine, nicht aus
der Luftlinienzahl):
- **Belegt:**
  - VBAT_IN/VBAT_FUSED-Flächen (x 10–35, y 15–30);
  - VBAT_PROT-Parallelfläche (x 33–53, y 29–35);
  - Servoschiene (x 85–123, y 8–27);
  - C403/C404 mit ihren Via-Reihen, D401.
- **Querriegel:** Durch den Servobereich (x 34–81) laufen auf B
  ost-westlich das Sense-Paar (y 15,0/15,6), BG (y 17,75), EXTVCC (y 19,6)
  und die Rückkopplung (y 28,4).
  - Nord-Süd-Verbindungen kreuzen dort nur auf F oder außen herum.
  - Diese Leitungen haben In2-GND als Bezug. Kreuzende B-Leitungen würden
    sie nicht stören, sind aber auf derselben Lage nicht möglich.
- **Durchsteckpins** auf B:
  - DevKit-Buchsen (2 × 22);
  - OLED- und IMU-Buchsen;
  - XT30, Micro-Fit, Stiftleisten, JST-PH;
  - J101-Haltestifte.
- Die Antennen-Sperrfläche liegt über der Oberkante, außerhalb der
  Platine.
- **Frei** ist B im Wesentlichen in der unteren Hälfte (y > 36) und unter
  den Ausgangsstufen außerhalb der Schiene. Dort liegen die meisten der
  engen F-Gassen aus 3h.

**Schritte 4–5 – übrige Verbindungen** (`autoroute_k1.py`, reproduzierbar):
1. Zuerst ausdrückliche Verbindungen für die Engpässe (`route_k1_links.py`):
   - RUN-Ausbruch von U401 Pin 6 über eine kurze B-Strecke zu einer freien
     F-Spalte bei x 43, dann durch die VBAT-Korridorfläche zu Q403 Pin 3;
   - VBAT_PROT zum RUN-Teiler über ein Via in die B-Fläche.
2. Specctra-Export mit festgesetztem Bestandskupfer. Im DSN sind In1/In2
   **Versorgungsebenen**, also kein Signalrouting auf den GND-Ebenen, und
   alle Außenlagen-Flächen **Sperrflächen**, damit Signale sie nicht
   zerteilen.
3. Freerouting 2.4.1 (Jar des installierten KiCad-Plugins), ohne Oberfläche.
4. Import nur des neuen Kupfers in die Gruppe `autoroute_k1`; die
   vorhandenen Gruppen bleiben unverändert.
5. Restlücken mit kurzen B-Verbindungen (`close_gaps.py`, Gruppe
   `gap_links_k1`), dann je GND-Pad ein eigenes Via zu den GND-Ebenen
   (`stitch_gnd_vias.py`, Gruppe `gnd_stitch_k1`).
   - Beide prüfen 0,2 mm Abstand zu fremdem Kupfer und den Lochabstand zu
     allen Bohrungen.

**Warum so:** Ein erster Lauf mit allen vier Lagen schloss alle
Verbindungen. Er legte aber ca. 3,5 m Leitung auf In1/In2 und zerschnitt
damit beide GND-Ebenen; verworfen. Ein zweiter Lauf nur mit F/B zerteilte
die Leistungsflächen; deshalb die Sperrflächen.

**Ergebnis** (KiCad-DRC, `scripts/kit verify`):
- ERC und Parität PASS.
- Geroutet: F 3 298 mm, B 1 933 mm, 287 Vias. In1/In2 enthalten nur die
  GND-Flächen.
- **Offen: 5 Verbindungen, 1 Abstandsbefund, 2 lose Vias.** Die Gesamt-DRC
  ist damit **nicht bestanden**.

| Nr. | Offene Stelle | Ursache | Vorgesehene lokale Lösung |
|---|---|---|---|
| 1 | RUN_SERVO: Q403 Pin 3 ↔ RUN-Netz um Q408 (x 38,9, y 31,7–35,8) | Die autoroutete SERVO_RUN_INH-Leitung von Q403 Pin 1 umschließt Pin 3 | diese zwei Segmente neu führen (Q403/Q408 liegen 4 mm auseinander) |
| 2 | +V_SERVO-Abzweig: R418/Q405/TP401 ↔ NT405 | Durchgang zwischen U402 und den VSERVO-Flächen auf F zu, auf B die Rückkopplungsleitung (y 28,4) | Anschluss an die B-Schiene südlich von RS402 oder eine eigene Abgriff-Leitung von der Schienenfläche |
| 3 | VBAT_PROT: die Verbraucher der unteren Hälfte (R520/O-37, Q505/VBAT-Messung, Controller-Teiler) ↔ Quelle | ca. 40 mm durch die dichte untere Hälfte, kein freier Weg gefunden | eigene Leitung entlang der linken Unterkante vom C101-Zweig aus |
| 4 | SERVO_PWR_EN: DevKit Pin 7 ↔ Freigabe der Servo-RUN-Gruppe | ca. 77 mm quer über die Platine; Schiene, Ausgangsstufen und Servo-Riegel auf B im Weg | Führung unter der IMU auf B und durch die 1,3-mm-F-Gasse; sonst eine Lageänderung im Aktuatorblock |
| 5 | GND von R407 Pad 2 (46,5 \| 34,9) | Pad liegt über der VBAT-B-Fläche, kein Via-Platz | F-Stich zu einem Via außerhalb der Fläche |
| – | Abstand: autoroutete IMU_INT1-Leitung auf B zu DevKit Pin 12 | Leitung zwischen zwei Buchsenpins | neu führen; ein Ersatz unter dem DevKit scheiterte an Nachbarleitungen |
| – | zwei lose VBAT-Vias (41,2 \| 35,9), (39,6 \| 37,3) aus Lückenversuchen | – | entfernen |

**Bewertung:**
- Die engen Übergänge aus 3h (Ausgangsstufen–IMU, OLED–IMU) sind geroutet.
  Die offenen Stellen liegen bei **langen Querverbindungen** und an zwei
  lokalen Knoten im Servo-Steuerbereich.
- Eine Vergrößerung der Kontur ist daraus **nicht** begründet. Alle fünf
  Stellen haben eine lokale Lösung, die noch auszuführen und zu prüfen ist.
- Das Autorouter-Kupfer ist **nicht optimiert**: lange parallele Bündel
  auf F in der unteren Hälfte, Umwege. Vor einer Freigabe ist es zu
  sichten und nachzuarbeiten.
- Die Rückwege der Signale entsprechen der Festlegung in 3a: F über In1, B
  über In2, GND-Ebenen ohne Signalschlitze.
- Die Breite der Versorgungsleitungen (0,4 mm) und deren Erwärmung sind
  nicht nachgewiesen.

## 3j. K1 geschlossen und Strompfade geprüft (Stand 2026-11-18)

**Status: Routing geschlossen, ERC/DRC/Parität bestanden (0 offen, 0
Befunde). Das ist eine elektrische Layoutprüfung, keine
Fertigungsfreigabe.**

Koordinaten in diesem Abschnitt sind K1-Koordinaten (Konturecke bei
−0,05/−0,05). Die Platine wurde am 2026-11-17 im Editor als Ganzes um
+62,25/+50,5 mm verschoben (reine Verschiebung, Kupfer geprüft). Die
Skripte rechnen den Versatz aus der Kontur (`k1_fixups.board_offset`).

**Lokale Korrekturen** (`k1_fixups.py`, je Schritt Zonen neu gefüllt und
DRC ausgeführt; Gruppen `servo_trial_routing`, `input_logic_routing`,
`servo_rail_routing` unverändert außer dem Via-Feld unten):

| Schritt | Änderung |
|---|---|
| `vbat_r405`, `vbat_r414` | drei überzählige VBAT-Vias samt Stichen entfernt (eines saß im SMD-Pad von R414, eines endete außerhalb der Fläche); R405 über ein Via an R414 Pad 1 |
| `run_q403` | RUN von Q403 Pin 3 mit kurzer B-Strecke zur RUN-Leitung an Q408 |
| `gnd_r407` | GND-Via für R407 Pad 2 / Q407 Pin 2 |
| `imu_int1` | Abstand IMU_INT1 an DevKit Pin 12: rechter Winkel statt Diagonale, ACT_ARMED_FB dafür gerade nach Osten |
| `vservo_branch` | +V_SERVO-Abzweig (Q405/R418/TP401, nur mA, 0,25 mm) auf B in die Schienenfläche südlich von RS402, nicht über NT405 |
| `vbat_lower` | VBAT_PROT zur unteren Hälfte (R520, R508/Q505, R515; mA), 0,4 mm, 3 Vias |
| `servo_pwr_en` | DevKit Pin 7 → Q404/R415, 0,2 mm, 2 Vias |
| `run_unroute`, `run_reroute` | Die RUN-Vorverlegung aus `route_k1_links.py` lief 4 mm **innerhalb** der F-VBAT-Fläche und teilte sie in zwei Inseln (113 → 72 + 36 mm²). Neu: B unter der Servo-VBAT-Säule, F-Sprung über VFB_TAP östlich des Bands, B entlang der Ostkante der B-Fläche zu C420; 3 Vias. VFB_TAP liegt auf B unter dem ganzen Band, ein kürzerer Weg ohne Flächentrennung existiert nicht. |
| `vbat_stitch` | 6 VBAT-Vias 0,8/0,4 am Südrand des F-Bands (siehe Strompfade) |
| `5v_trunk`, `5v_devkit_branch` | +5V-Stamm 1,0 mm mit Doppel-Vias; DevKit-Zweig auf 0,5–0,8 mm verbreitert |

Weitere Skripte: `power_pad_connections.py` (massive Ebenenanbindung
J101.1, J102.3, J103.3), `d501_cathode_pour.py` (Kathodenkupfer D501),
`servo_via_field.py` (sechs Vias am Shunt 1,0/0,5 mm).

**Flächenprüfung:** Inselzahl und Fläche je Zone vor/nach jeder Änderung,
dazu ein Erosionstest (Engstellenbreite). Alle Leistungsflächen sind je ein
Stück; `rail_band_f` bleibt planmäßig dreiteilig (von den Signalpins J102/
J103 Pin 1 getrennt, jedes Teil vernäht). Die F-VBAT-Fläche hat einen
0,5–0,6 mm-Hals an Q101 (schon vor dem Routing vorhanden), der nach
`vbat_stitch` nur noch wenig Strom trägt. Eine Randzunge der B-VBAT-Fläche
(x 41–46) ist ≥ 1,0 mm breit; sie liegt nicht im Hauptstrompfad.

**Strompfade** (`current_map.py`: Gleichstrom-Netzwerkrechnung auf dem
gerasterten Ist-Kupfer, 20 °C, ohne Erwärmung, ohne Steckerübergänge –
**alles Schätzungen**; Berichte und Stromdichtekarten unter
`qa/generated/current/`). Die Tabelle ist der Stand vom 2026-11-18 vor der
Festlegung des Aufbaus (35 µm auf allen Lagen, 20 µm Hülse); die
aktualisierten Werte mit festgelegtem Aufbau stehen im Abschluss unten.

| Pfad | Last (Annahme) | Ergebnis |
|---|---|---|
| +V_SERVO RS402 → J102/J103 | 11,2 A (2 × 5,1 A blockiert, 2 × 0,5 A) | Abfall 22 / 28 mV; Verlust 0,26 W. Die B-Fläche trägt fast alles, die F-Bandteile wenig (nur 2–3 Vias je Teil). Via-Feld: ungleich, 0,4–1,9 A je Via; die Spalte am Shunt am stärksten. Örtliche Spitzen ca. 6–7 A/mm an der B-Lasche von J102 und an der Innenecke der B-Fläche. |
| VBAT_PROT Q101 → Q401/U301 | 9,35 + 0,75 A (10,1 A bei 9 V) | Abfall 24 mV. Vorher wurde die B-Fläche nur über den 0,5-mm-Hals an Q101 gespeist (ca. 9 A/mm); mit `vbat_stitch` max. 4,3 A/mm dort, Vias ≤ 1,3 A. Verbleibende Spitze ca. 6,7 A/mm an der Innenecke Band/Servo-Säule (F). |
| GND-Rückstrom Servo → J101/Q402 | 11,2 A | Läuft fast ganz über In1/In2. Vorher: Engstelle Wärmefallen der THT-GND-Pins (J101.1: 9,35 A über 2 × 4 Stege à 0,5 mm, ca. 2,75 A/mm). Mit massiver Anbindung max. 0,7 A/mm, Abfall 6 mV. Folge: beim Löten mehr Wärme nötig. |
| +5V L301 → Verbraucher | 1,53 A (Schaltergrenzen max.) | Vorher 3,5–4,8 A/mm im 0,4-mm-Stamm, Stamm-Vias 1,06 A. Nach `5v_trunk` max. 2,7 A/mm, Vias ≤ 0,6 A. |
| +5V → D501 (DevKit) | 0,55 A | 108 → 83 mV nach Verbreiterung. **Über der Annahme 50 mV (Versorgungsdokument 3.11)**; Reserve LDO-Eingang sinkt von 0,24 V auf ca. 0,21 V. Ursache: 130 mm Autorouter-Weg mit 7 Lagenwechseln. |
| +5V_DEVKIT, +5V_LED/_EXT/_RX, +3V3, LOCK_SUP | 0,55 / 0,32 / 0,30 / 0,21 A, 50 mA, < 1 mA | ≤ 1,5 A/mm, Abfall ≤ 10 mV – im untersuchten Gleichstromfall ohne Auffälligkeit (kein thermischer Nachweis). |

Vergleichswert (IPC-2221, Schätzung, 35 µm außen): 1 mm Breite trägt bei
20 K Erwärmung ca. 3 A; ein Via 0,4 mm (20 µm) nach der konservativen
Innenlagenformel ca. 1,3 A. Flächen und kurze Laschen sind thermisch
besser angebunden als diese Näherung annimmt; der Nachweis bleibt eine
Messung am Muster.

**Offen aus dieser Prüfung:**
- *(überholt, siehe Abschluss unten)* **D501-Kathodenkupfer:** gefordert ≥ 1 cm² (3.11), erreicht 63 mm²
  (F 14 + B 49, 4 Vias). Um D501 ist F dicht geroutet. Lösung: D501 an
  eine freie Stelle versetzen oder Signale um D501 neu führen; sonst T_j
  zwischen den Schätzwerten 106 und 155 °C.
- *(überholt, siehe Abschluss unten)* **DevKit-Zweig +5V:** 83 mV statt 50 mV; kürzere Neuführung (ca. 70 mm
  statt 130 mm) beim Aufräumen.
- **Servoschiene bei 11,2 A:** Via-Feld und J102-Lasche an der Grenze der
  konservativen Näherung; bei 6 A Fahrbetrieb unkritisch. Entscheidung
  35/70 µm Außenkupfer (3a) bleibt offen und ist der wirksamste Hebel.
- Rückstromwege der Regler- und Treiberschleifen wurden nicht neu
  gerechnet; die handgerouteten Schleifen (3b) sind unverändert.
- Aufräumen der Autorouter-Umwege und Lagenwechsel steht noch aus.

Kupferansichten (nicht versioniert): `render_copper_views.py`, Ausgabe
`qa/generated/copper/` (ganze Platine F/B/überlagert; Ausschnitte
+V_SERVO, VBAT_PROT, +5V, D501).


**Abschluss Versorgung und Thermik (2026-11-18, nach Festlegung des
Aufbaus).** Die Aussagen gelten für den untersuchten **Gleichstromfall**:
Stromverteilung und Spannungsabfall. Eine zulässige Dauertemperatur ist
damit nicht nachgewiesen – besonders nicht für Servoschiene und Via-Feld.

*DevKit-Zweig neu geführt* (`k1_fixups.py 5v_devkit_direct`): D501 hing
über die Nordschleife (bis y 33 und auf B zurück nach y 53, 2 Vias). Neu:
direkte Verbindung vom Via (95,5 | 55,8) auf B, ein Via, F bis zur Anode,
0,8 mm (0,6 mm an der J115-Befestigungsbohrung). Die Nordschleife versorgt
weiter D201–D205, R211–R215 und U201. Kupferabfall L301 → D501 bei 0,55 A:
108 → 83 → **56 mV**.

*Spannungsbudget LDO-Eingang (Akku allein, 0,55 A, Schätzung)*:

| Größe | kalt (−20 °C) | warm (Platine 85 °C) |
|---|---|---|
| +5V statisch min. | 4,74 V | 4,74 V |
| Lastsprung-Reserve +5V (3.11) | −0,10 V | −0,10 V |
| Kupfer L301 → D501 (`current_map.py 5v`, Cu-Temperaturbeiwert 0,39 %/K) | −0,05 V | −0,07 V |
| V_F D501 (Datenblatt max. 25 °C: 0,498 V interpoliert; −20 °C ca. +0,09 V nach Fig. 1) | −0,59 V | −0,50 V |
| Buchsenkontakt + DevKit-Leitung bis LDO (Annahme, nicht gemessen) | −0,025 V | −0,025 V |
| **LDO-Eingang min.** | **3,98 V** | **4,05 V** |
| benötigt: 3,349 V + Dropout 0,418 V bei 0,55 A (max. über Temperatur) | 3,77 V | 3,77 V |
| **Reserve** | **ca. 0,21 V** | **ca. 0,28 V** |

Die Reserve ist ein Rechenwert aus Grenz- und Annahmewerten; Messung am
Muster (LDO-Eingang bei Funklast, kalt).

*D501 thermisch*: Die „1 cm²“ im Datenblatt (PMEG4010CEH v.3, Tab. 6,
Fußnote 3) sind die **Prüfbedingung** für R_th(j-a) = 150 K/W
(einseitiges FR4, Kathodenpad 1 cm²), keine Anwendungsvorgabe; Standard-
Footprint 330 K/W, R_th(j-sp) 60 K/W. Bewertung mit `scripts/kit thermal`
(Eintrag `hardware/simulations/thermal/power_sources.csv`: 0,274 W Dauer,
Umgebung 65 °C, nur D501 als Quelle):
- Werkzeug ohne Innenlagen (konservativ): Platine 108 °C → T_j ≈ 125 °C.
- Innenlagen als gleichwertige Flächenleitfähigkeit (In1 liegt 0,1 mm unter
  F): Platine 77 °C → T_j ≈ 93 °C.
- Zwei Modellfälle ergeben etwa 93 beziehungsweise 125 °C. Eine
  belastbare Temperaturbegrenzung ist daraus nicht abgeleitet; Messung am
  Muster erforderlich. Weil andere Wärmequellen im Modell fehlen, ist
  insbesondere 125 °C keine gesicherte Obergrenze. (Im Mittel 90 mW statt
  274 mW.)
  Das F-Kupfer (14 mm²) und das B-Kupfer (49 mm², 4 Vias) sind nicht einer
  zusammenhängenden 1-cm²-Fläche gleichwertig; der Vergleich geht über das
  Platinenmodell, nicht über die Fläche.
- **D501 bleibt vorläufig, wo er ist.** Die Entscheidung wird durch die
  Messung bei der Erstinbetriebnahme überprüft (docs/bringup.md, Schritt D).
  Offen bleiben Wärme anderer Quellen am Ort
  von D501 (Regler ca. 70 mm entfernt, nicht im Modell) und die Messung.

*Strompfade mit festgelegtem Aufbau* (35/17,5/17,5/35 µm, Hülse 18 µm; feinstes
Raster):

| Pfad | Abfall | Vias / Bemerkung |
|---|---|---|
| +V_SERVO RS402 → J102 / J103 (11,2 A) | 22,5 / 28,2 mV | Via am Shunt max. 1,8 A (1,0/0,5 mm), Feld ungleich |
| VBAT_PROT Q101 → Q401 (9,35 A) | 24,4 mV | Vias ≤ 1,3 A |
| GND-Rückstrom Servo → J101 (11,2 A), ganze Platine | 11,3 / 12,0 mV | über In1/In2; mit 17,5 µm Innenlagen etwa doppelt so viel wie mit 35 µm |
| +5V L301 → D501 (0,55 A) | 56 mV | Stamm-Vias ≤ 0,6 A |

*Modellgrenzen (GND-Rechnung und allgemein)*:
- **Ausschnitt:** Kupfer außerhalb des Rechenbereichs fehlt. Weglassen von
  Leitern kann den Widerstand nur erhöhen (Monotonie). Das gilt aber nur,
  solange Einspeise- und Senkenanschlüsse sowie die Randbedingungen im
  Ausschnitt unverändert und passend bleiben; schneidet der Ausschnitt
  Anschlüsse ab oder verschiebt er sie, gilt die Aussage nicht. Der
  Vergleich GND-Rückstrom im Ausschnitt 130 × 45 mm 14,3 mV gegen ganze
  Platine 11,4 mV (Raster 0,25 mm) ist eine Plausibilitätsprüfung, kein
  Ersatz für diese Bedingungen. Für den Bericht gilt die ganze Platine.
- **Raster:** Abfälle und Via-Ströme ändern sich zwischen 0,25 und 0,15 mm
  (GND) bzw. 0,1 und 0,05 mm (Servo, VBAT) um ≤ 4 %. **Punktspitzen** der
  Stromdichte an Via-Ringen und Innenecken steigen mit feinerem Raster
  weiter (Servo-B-Fläche 6,9 → 8,6 A/mm, VBAT-F 6,7 → 8,4 A/mm, GND
  In1 0,7 → 0,8 A/mm): Sie konvergieren nicht und sind nur Hinweise auf
  Stromverdrängung, keine Belastbarkeitswerte.
- Nicht modelliert: Erwärmung und temperaturabhängiger Widerstand,
  Toleranz der Hülsen, Lotfüllung der Bohrungen, Wechselanteile,
  Steckerübergänge, Einspeisung über Pads als Äquipotential.

*Verbleibend offen:* thermischer Nachweis der Servoschiene, des Via-Felds
und der J102/J103-Laschen bei 11,2 A (Messung am Muster mit blockierten
Servos oder Ersatzlast); Bestätigung von Aufbau und Hülsenklasse beim
Fertiger; Muster-Messungen LDO-Eingang und D501.

## 3k. Fertigerabgleich und DRAFT-Fertigungspaket (Stand 2026-11-18)

Layout unverändert (keine Baugruppe verschoben, kein Routing geändert); nur
Beschriftung und Exportwerkzeug angepasst. Vorlage: JLCPCB
[PCB-Capabilities](https://jlcpcb.com/capabilities/pcb-capabilities), Abruf
2026-11-18, Mehrlagenwerte.

*Fertigerregeln im DRC*: `RoverCore.kicad_dru` enthält die JLCPCB-Grenzen
(Leiterbahn ≥ 0,09 mm, Via-Bohrung ≥ 0,15 mm, Via-Restring ≥ 0,05 mm,
PTH-Restring ≥ 0,15 mm, NPTH ≥ 0,5 mm, PTH-Bohrung zu Kupfer ≥ 0,28 mm bzw.
innen ≥ 0,3 mm, Via-Bohrung zu Kupfer ≥ 0,2 mm, Pad-Bohrabstand ≥ 0,45 mm,
Pad-Pad ≥ 0,15 mm, Rand ≥ 0,2 mm, Bestückungsdruck ≥ 1,0 mm / 0,15 mm,
Druck-Abstand ≥ 0,15 mm). Kupfer und Bohrungen erfüllten alle Werte schon
vorher; DRC mit Regelsatz: 0 Verstöße, 0 offene Verbindungen. **Grenze der
Aussage:** KiCads DRC kennt keine Mindest-Linienbreite für den
Bestückungsdruck; der Regelsatz prüft dort nur Texte und Abstände. Die
Linienbreite ist damit **nicht** abgedeckt (3l).

*Bestückungsdruck* (`hardware/scripts/silk_jlc.py`):
- 230 Texte unter dem Minimum (Referenzen 0,8/0,12 mm, Modul-Pinbeschriftungen
  0,8 mm) auf 1,0 mm Höhe / 0,15 mm Strich vergrößert; Ankerpunkte unverändert.
- 38 Referenzen kollidierten danach mit Druck oder Pads; sie stehen nur noch
  auf der Bestückungszeichnung (Fab-Lage), z. B. C408–C417, R415–R419, TP401,
  TP402. Die U501-Pinmarke „J3-1“ liegt auf F.Fab.
- **Bekannte Abweichung:** Umrisslinien der Bibliotheks-Footprints haben
  0,12 mm Strich und liegen unter den 0,15 mm von JLCPCB; Auswertung des
  exportierten Gerbers in 3l. Nicht geändert; Owner-Entscheid.

*Hülsenkupfer – Einschränkung*: JLCPCB nennt nur eine **mittlere**
Hülsendicke von 18 µm. Die Rechnungen setzen 18 µm an der **dünnsten** Stelle
voraus (IPC-6012 Kl. 2). Das ist mit dem Standardangebot nicht abgedeckt:
entweder Klasse 2 bzw. ≥ 18 µm Mindestwert ausdrücklich bestellen oder die
Via-Anteile der Rechnungen mit dem vereinbarten Wert wiederholen (3a,
Geltungsbedingung).

*DRAFT-Paket* (`scripts/kit export . --revision A1` →
`manufacturing/releases/generated/rev-A1-DRAFT`, NO-GO, nicht versioniert):
- Quality Gate PASS (ERC, DRC, Parität, Bibliotheken, Footprints,
  Pin-Pad-Zuordnung). Hinweise: Datenblattfeld fehlt bei 44 Teilen, 14
  Teile ohne 3D-Modell, keine Bauteilakten (`components/`).
- **Fehler im Exportwerkzeug gefunden und behoben:** Die BOM gruppierte nicht
  nach DNP. R616 (bestückt) stand in einer Zeile mit R801/R802 (DNP) und war
  dort als DNP markiert, während die Bestückungsdatei R616 platzierte.
  `tools/release/exports.py` gruppiert jetzt auch nach `${DNP}`
  (`tools/VENDORED.md`).
- Abgleich Paket ↔ Board (`hardware/scripts/fab_package_check.py`): BOM 230
  Referenzen in 92 Zeilen, DNP-Kennungen stimmen; Bestückungsdatei 228 Teile
  (225 oben, 3 unten), Lage, Seite und Drehung gleich dem Board; Bohrwerkzeuge
  0,25–1,90 mm PTH, 2,70/3,00 mm NPTH; Gerber-Jobdatei 4 Lagen, 1,6 mm,
  Aufbau wie 3a. **Offener Fehler:** D502 (Status-LED) ohne Hersteller und
  Teilenummer – Typ offen (O-28), vor der Bestellung festlegen.
- Sichtprüfung der Gerber- und Bohrdateien mit einem eigenen Renderer
  (`hardware/scripts/gerber_preview.py`, zeichnet die exportierten Dateien,
  nicht das Board): Kupfer, Innenlagen mit Antennenaussparung, Maske,
  Bestückungsdruck, Paste und Bohrungen ohne Auffälligkeiten.
- Hinweise für die Bestellung:
  - Nur F/B_Cu, In1/In2_Cu, F/B_Mask, F/B_Paste, F/B_Silkscreen, Edge_Cuts und
    die Bohrdatei hochladen; das Paket enthält zusätzlich Fab-, Courtyard- und
    User-Lagen.
  - Bestückungsdatei im KiCad-Format, Ursprung = Seitenursprung (kein
    Hilfsursprung gesetzt), Y nach oben; für JLCPCB Spalten umbenennen und
    Drehwinkel in deren Vorschau prüfen.
  - 16 THT-Teile stehen in der Bestückungsdatei (J101–J112, J115, J116, F101,
    U501-Buchsen): entweder THT-Bestückung bestellen oder von Hand löten.
  - U401 hat 0,25-mm-Bohrungen im Footprint (Wärmevias im Pad); kleiner als
    die JLCPCB-Empfehlung 0,5 mm für Bauteilbohrungen, aber zulässig.
  - Die Bestückungszeichnung aus `kit export` ist auf A4 1:1 kaum lesbar;
    ergänzend `qa/generated/fab/assembly_refs_top.pdf` / `_bottom.pdf`
    (nur Referenzen, skaliert).
- Befestigung: seit 3n vier M3-NPTH-Bohrungen H1–H4, Lage vorläufig.

- **D502 festgelegt (2026-11-18, schließt den BOM-Teil von O-28):** Würth
  Elektronik 150060RS75000 (WL-SMCW, 0603, rot, AlInGaP). Werte aus dem
  [Herstellerdatenblatt](https://www.we-online.com/components/products/datasheet/150060RS75000.pdf):
  - V_F typ. 2,0 V / max. 2,4 V bei 20 mA, I_F max. 30 mA, λ_dom 625 nm;
  - Pin 1 = Kathode mit Polaritätsmarke. Das passt zu Device:LED und
    LED_0603_1608Metric (Pad 1 an GND).
  - Strom über R504 1 kΩ: (3,3 V − 2,0 V) / 1 kΩ ≈ 1,3 mA (Schätzung mit
    V_F typ.). Der tatsächliche Strom hängt von der GPIO-Ausgangsspannung
    unter Last und von der LED-Kennlinie bei kleinem Strom ab; beides ist
    nicht abgelesen. Eine frühere Angabe von 1,5 mA war falsch.
  - Eine LCSC-Nummer und der JLCPCB-Bestand sind nicht geprüft; das Feld
    LCSC ist leer.
  - Der Paketabgleich meldet 0 Fehler.

Erstinbetriebnahme: [docs/bringup.md](../bringup.md) (Versorgung, D501,
Servostrompfad, Abbruchkriterien).

## 3l. 3D-Vollständigkeit, Bestückungsdruck-Linien, Befestigung (Stand 2026-11-18)

Schaltung, Routing und Board-Datei unverändert. Diese Klärung ändert nur
Review-Bilder, Skripte und Dokumentation.

*3D-Ansichten* (`hardware/scripts/render_populated_review.py`, Ausgabe
`qa/generated/populated/`, nicht versioniert; Auswahl in `docs/images/`):
- Die README-Bilder vom Stand `b8ed540` waren direkt aus der Board-Datei
  gerendert. Teile ohne Modell fehlten, die Module waren nur als
  Buchsenleisten zu sehen. Ersetzt durch Review-Ansichten mit und ohne
  gesteckte Module (oben, unten, schräg vorne, schräg hinten, flach von vorne),
  Renderqualität „high“.
- **Hüllkörper** entstehen nur in einer Kopie der Board-Datei, nie in der
  Bibliothek oder in `RoverCore.kicad_pcb`, und gehen nicht in den STEP-Export
  ein. Kennzeichnung: magenta = Carrier-Teil, blau = Modul; jede Bildunterschrift
  nennt die betroffenen Referenzen. Status je Position in `model_status.csv`:
  213 Bibliotheksmodelle, 14 Hüllkörper, 3 Buchsenleisten mit Modulhülle,
  23 ohne Körper (Testpunkte, Net-Ties), 0 fehlend.
- **Warum Hüllkörper:**
  - Die KiCad-Bibliotheksdateien für XT30PW-M, Micro-Fit 43650-0300,
    PowerPAK SO-8, PG-TDSON-8 und DPY0002A sind in dieser KiCad-Installation
    nicht vorhanden (`Connector_Molex.3dshapes` fehlt ganz).
  - Für DevKit, OLED, IMU und BZ101 liegt kein Herstellermodell im Projekt.
  - Die Dateien nachzuladen braucht eine Freigabe zum Herunterladen und einen
    Lizenzabgleich.
- **Steckrichtung:** XT30 und Micro-Fit haben eine dunkle Stirnfläche auf der
  Steckseite. Das ist die Seite der Fab-Kontur, auf der das Gehäuse über die
  Pads hinausragt (lokal y min).
- **Ausrichtung im Render geprüft:** Draufsicht 6000 × 3600 px, in Ausschnitten
  verglichen:
  - Polung von C101, C406 und C407 (dunkle Markierung gegenüber „+“), Ring
    von D101 und D501;
  - Pin-1-Punkt gegen Druckmarke bei U201, U301, U401, U402 (bei SOT-23/-5
    ist im Modell keine Pin-1-Marke erkennbar, dort nicht beurteilbar);
  - Buchsenleisten J115, J116 und U501 über den Pad-Reihen.
  Alle Bibliotheksmodelle haben Versatz und Drehung 0. Eine Drehung von ±90°
  haben nur die Buchsenmodelle von J115/J116, einen Versatz von 22,86 mm nur
  das zweite U501-Modell; beides stimmt im Render mit den Pads überein. Das
  war eine Stichprobe, keine Prüfung jedes Bauteils.

*Bestückungsdruck-Linien* (Auswertung der exportierten Dateien
`RoverCore-F_Silkscreen.gto` / `B_Silkscreen.gbo`, Stand `rev-A1-DRAFT`):
- F: 1 204 Striche mit 0,12 mm (ca. 1,66 m), B: 7 (D401, C403, C404). Laut
  Gerber-Attribut `TO.C` gehören sie zu 241 Footprints (Umrisse, Pin-1-Marken
  von C, R, D, Q, U, J, SW, TP, L, F, BZ). Keine Brett-Grafik, keine Texte; alle
  Zeichen haben 0,15 mm.
- Exportoption „Maske vom Bestückungsdruck abziehen“ ist **aus**; DRC meldet
  keinen Druck über offenem Kupfer.
- **Abweichung zu JLCPCB** (≥ 0,15 mm). Risiko: dünne oder lückenhafte
  Umrisse; Bestückung und Beschriftung sind nicht betroffen.
- **Probelauf auf einer Kopie:** Werden alle 926 Footprint-Linien unter
  0,15 mm auf 0,15 mm gesetzt, meldet die DRC 13 neue Abstandswarnungen
  (Druck zu Druck 0,13–0,149 mm statt 0,15 mm):
  - Q505/Q506 (Umrisse berühren sich);
  - J116-Rahmen zu den Pinbeschriftungen;
  - Q101-Pin-1-Marke zur Referenz von Q403;
  - U501-Rahmen 0,145 mm zur Platinenkante.
  Kein Kupfer betroffen. **Nicht übernommen:** Owner-Entscheid zwischen
  (a) verbreitern und die 13 Stellen lokal bei 0,12 mm lassen oder kürzen,
  (b) 0,12 mm als bekannte Abweichung mit dem Fertiger abstimmen.

*Befestigung*:
- Die „fünf Montagepositionen“ aus 3h sind **Kommentarkreise auf Cmts.User**
  (Ø 3,2 mm) bei (28 | 4), (54 | 4), (4 | 36), (91 | 81), (145 | 81)
  (K1-Koordinaten). Sie erzeugen keine Bohrung und stehen in keinem Gerber.
  Die frühere Prüfung galt nur dem Freiraum zu Courtyards.
- **Kupfercheck auf dem gerouteten Stand:** Im Radius 1,8 mm (Bohrung + 0,2 mm)
  und im Radius 3,5 mm (Unterlegscheibe) liegt an allen fünf Stellen auf keiner
  Lage Kupfer eines anderen Netzes als GND. Nächster Courtyard 5,4–12,2 mm,
  Rand je 4,0 mm. Bohrungen ließen sich also ohne Umrouten setzen; nur die
  GND-Flächen werden neu gefüllt.
- **Einschränkung:** (145 | 81) liegt unter der Hülle des gesteckten
  USB-Steckers (10,4–17,4 mm hoch). Der Schraubenkopf kollidiert nicht, aber
  das Werkzeug kommt nur bei abgezogenem USB-Kabel heran. (91 | 81) liegt
  7,5 mm neben der OLED-Hülle.
- **Umgesetzt in 3n** (H1–H4, Lage vorläufig). Ursprüngliche Bewertung:
- **Notwendige mechanische Änderung (separat, vor dem nächsten Paket):**
  Befestigungsbohrungen setzen. Offene Entscheidungen des Owners:
  - Lage, abgestimmt mit dem Chassis;
  - NPTH oder mit GND verbundene Hülse;
  - Abstandshöhe unten (THT-Stifte, C403/C404/D401).
  Bis dahin bleibt das Paket DRAFT/NO-GO.

## 3m. Herstellermodelle (Stand 2026-11-18)

Auftrag: magenta Hüllkörper durch Herstellermodelle ersetzen. Es ändern sich
nur die 3D-Einträge in `RoverCore.kicad_pcb`. Pads, Positionen und Routing
bleiben, wie sie sind.

| Position | Bauteil | Quelle | Ergebnis |
|---|---|---|---|
| J102, J103 | Molex 43650-0300 | [molex.com](https://www.molex.com/en-us/products/part-detail/436500300), STEP AP242 über TraceParts, ohne Anmeldung | **übernommen** |
| J101 | AMASS XT30PW-M | [Ultra Librarian](https://app.ultralibrarian.com/details/25c08cfe-12d2-11ec-9033-0a34d6323d74/Amass/XT30PW-M) | dort **kein 3D-Modell** („No 3D Model Available“), nur Symbol und Footprint. Ein GrabCAD-Modell eines Nutzers ist kein Herstellermodell und braucht eine Anmeldung; nicht geladen |
| BZ101 | Same Sky CMT-8540S-SMT-TR | [sameskydevices.com](https://www.sameskydevices.com/product/audio/buzzers/audio-transducers/cmt-8540s-smt-tr) | **blockiert:** Download nur nach Eingabe einer E-Mail-Adresse und Zustimmung zu den „CAD Model Terms“; nicht ohne Owner |
| Q101 | Vishay SiRA99DP-T1-GE3 | [Vishay-Portal (Ultra Librarian)](https://vendor.ultralibrarian.com/vishay/embedded?q=library/ecad/&vdrSearch=SIRA99DP-T1-GE3&docId=71023) | dort **kein 3D-Format**, nur Symbol und Footprint; Export verlangt außerdem Zustimmung zu den UL-Bedingungen |
| Q401, Q402 | Infineon BSC026N04LS, PG-TDSON-8-6 | [Infineon-Gehäuseseite](https://www.infineon.com/package/PG-TDSON-8-6), [Produktseite](https://www.infineon.com/part/BSC026N04LS) | **kein STEP** angeboten: nur interaktives 3D-PDF, Gehäusezeichnung, Footprint-PDF |
| D601–D604, D606–D608 | TI TPD1E05U06DPYR | [Ultra Librarian](https://app.ultralibrarian.com/details/16990488-103f-11e9-ab3a-0a3560a4cccc/Texas-Instruments/TPD1E05U06DPYR) | 3D-Modell vorhanden, **blockiert:** „Login to Download“ (kostenloses Konto) |
| (Molex J102/J103) | – | [Ultra Librarian](https://app.ultralibrarian.com/details/e86e5139-a2fd-11eb-9033-0a34d6323d74/Molex/436500300) | dort ebenfalls „Login to Download“; nicht nötig, weil Molex direkt liefert |

*Molex 43650-0300* (`hardware/libraries/3d-models/models.csv`):
- **Datei:** `vendor/Molex_436500300.stp`, SHA-256 `0b5b19a1…7d30`,
  TraceParts-Teil 33-12012026-074690, Version 1.1.7. Laut Begleitdatei die
  Variante „Right-Angle Header, 3.00mm Pitch, Single Row, 3 Circuits, with
  Snap-in Plastic Peg PCB Lock, Black“; das ist die bestellte Teilenummer.
- **Ausrichtung:** Drehung (−90°, 0°, 180°), Versatz 0. Prüfung mit
  `hardware/scripts/model_fit_check.py` (Footprint allein, Ansichten oben,
  vorne, seitlich, schräg):
  - Gehäuse = Bestückungsdruck-Umriss einschließlich Fasen;
  - Stifte 1–3 in den Pads bei x 0 / 3 / 6;
  - Rastzapfen in der NPTH-Bohrung (3 | −4,32);
  - Gehäuse liegt auf der Platine auf, Steckseite zur Platinenkante
    (lokal y min).
  Im Gesamtrender geprüft (Draufsicht, schräg von hinten).
- **Lizenz:** Die Molex-Nutzungsbedingungen erlauben die Nutzung
  heruntergeladener Inhalte zur Bewertung der Produkte, keine Weitergabe.
  Das Repository ist öffentlich, deshalb ist die STEP-Datei **nicht in Git**
  (`.gitignore`). Versioniert sind Quelle, Datum, Prüfsumme und Ausrichtung;
  `hardware/scripts/assign_vendor_models.py` trägt sie ein. Ohne die Datei
  fehlt der Körper, und `kit verify` meldet ihn unter `models_3d`.
  Gerenderte Bilder des Modells stehen im README.
- **Stand `models_3d`:** 12 statt 14 Meldungen. ERC, DRC und Parität bestehen.

*Nachtrag 2026-11-18:* Weitere Suche nach Herstellerquellen ohne Konto ohne
Ergebnis:
- **Vishay:** Die Produktseiten zu PowerPAK SO-8 verweisen nur auf das
  Ultra-Librarian-Portal.
- **Same Sky:** Das Modell gibt es weiterhin nur mit E-Mail und Zustimmung
  zu den CAD-Bedingungen.
- **Drittportale** (SnapMagic, Octopart-Partner): Sie verlangen ebenfalls ein
  Konto oder eine Anfrage und liefern keine Herstellermodelle.
- **D502:** Für das jetzt festgelegte Teil 150060RS75000 bleibt das passende
  KiCad-Bibliotheksmodell LED_0603 im Einsatz.

*Nachtrag 2026-11-18 (eigene Gehäusemodelle, Owner-Freigabe: frei lizenzierte, maßlich geprüfte Modelle
erlaubt):*
- **Quellen geprüft, ohne Ergebnis:**
  - Die KiCad-Bibliothek enthält die von den Footprints referenzierten Modelle für PowerPAK SO-8,
    PG-TDSON-8, DPY0002A und XT30PW-M nicht, weder auf master noch im Tag 10.0.7; in
    `Connector_AMASS` gibt es nur XT60.
  - EasyEDA/LCSC sperrt automatisierte Abrufe (HTTP 403).
  - Flux.ai hat für XT30PW-M keine Dateien.
- **Gehäuse bestätigt:**
  - SiRA99DP = PowerPAK SO-8 Single (Vishay-Datenblatt 71023, Zeichnung 71655);
  - BSC026N04LS = PG-TDSON-8-6 (Infineon-Produktseite);
  - TPD1E05U06DPYR = DPY0002A X1SON (TI SLVSBO7O);
  - XT30PW-M = AMASS-Spezifikation V1.2.
- **Eigene Modelle:** `hardware/scripts/make_package_models.py` erzeugt VRML-Modelle aus diesen
  Zeichnungen, mit Nennmaßen. Die XT30-Höhe von 5,2 mm ist in der Zeichnung nicht bemaßt und aus der
  Ansicht abgegriffen (Schätzung). Die Modelle liegen in Git (`hardware/libraries/3d-models/project/`,
  MIT); Werte und Prüfung je Zeile in `models.csv`.
- **Prüfung im Render:** `model_fit_check.py` und die Gesamtansicht. Gehäuse und Anschlüsse liegen auf
  Umriss und Pads, die Pin-1-Marke liegt an Pad 1, J101 steckt mit den Kontakten in den Pads und mit den
  Zapfen in den Ohrbohrungen.
- **Fehler im Generator gefunden und behoben:** Die y-Spiegelung kehrt die Flächenorientierung um. Im
  ersten Render waren die Gehäuse hohl und zeigten die Pads.
- **Grenze:** VRML erscheint nicht im STEP-Export der Platine.
- **Stand `models_3d`:** BZ101 hat keinen Körper. Die Module DevKit, OLED und IMU erscheinen in der
  Platine nur als Buchsenleisten; als ganze Module sind sie nur in den Review-Ansichten zu sehen, als
  Hüllkörper.

*Für die blockierten Teile braucht es den Owner:*
- **Ultra Librarian (TPD1E05U06):** im Browser-Bereich anmelden; dann lade ich
  das Modell und prüfe es wie oben.
- **Same Sky (BZ101):** Freigabe, dort die E-Mail-Adresse einzutragen und den
  CAD Model Terms zuzustimmen, oder die Datei selbst laden.
- **XT30PW-M, SiRA99DP, PG-TDSON-8:** bei den genannten Quellen gibt es kein
  STEP. Möglich wären Anfragen bei AMASS, Vishay und Infineon oder die
  KiCad-Bibliotheksmodelle derselben Footprints (CC-BY-SA, generiert, keine
  Herstellermodelle); dafür ist ein Download aus dem KiCad-GitLab nötig.

## 3n. Befestigungsbohrungen H1–H4 (Stand 2026-11-18, Lage vorläufig)

> **Ersetzt 2026-11-18 durch Variante B** (160 × 85 mm, vier Eckbohrungen, [Umsetzung und Prüfung](rev1-befestigung-vorschlag.md)). Der folgende Abschnitt beschreibt den überholten ersten Entwurf.
>
> Stand nach Owner-Review 2026-11-18: H1–H4 waren ein vorläufiger Entwurf.
> Sie wurden nachträglich in freie Stellen gesetzt; das ist kein
> Befestigungskonzept. Die Fertigungsvorbereitung ist gestoppt. Ein neues
> Lochbild nahe den vier Ecken, mit lokalen Platzierungs- und
> Routingänderungen, steht als Vorschlag in
> [rev1-befestigung-vorschlag.md](rev1-befestigung-vorschlag.md). Das Board
> ist noch nicht geändert.

**Vorgaben:** Im Repository gibt es keine Chassis- oder Gehäusemaße
(`hardware/mechanical/` enthält nur die Vorlage). Die Lage ist deshalb ein
**vorläufiger Vorschlag** und vor der Fertigung an der Fahrzeugbefestigung zu
bestätigen. Vier freie Stellen auf der Platine allein reichen dafür nicht.

*Annahmen* (eigene Wahl, Schätzung):
- **Schraube und Bohrung:** M3, Durchgangsbohrung 3,2 mm NPTH (ISO 273 fein).
- **Oberseite:** Kopf ISO 7380 Ø 5,7 × 1,65 mm auf Scheibe ISO 7089
  Ø 7,0 × 0,5 mm.
- **Unterseite:** Sechskant-Abstandshalter SW 5,5, über Ecken Ø 6,35 mm,
  10 mm lang.
- **Kupfersperre (Sperrfläche im Footprint):**
  - F.Cu/B.Cu r 3,8 mm (Scheibe bzw. Abstandshalter + 0,3 mm);
  - In1/In2 r 2,0 mm;
  - keine Leitungen, Vias oder Flächen.
- **Courtyard:** r 3,8 mm auf beiden Seiten.
- **Werkzeugzugang:** nächster Courtyard ≥ 4,5 mm, bei hohen Teilen ≥ 5,5 mm;
  ≥ 5,5 mm zu den Modulhüllen.
- **Rand:** Lochmitte ≥ 4,0 mm vom Rand.
- **Leistungspfade:** kein Kupfer von Regler- oder Hochstromnetzen
  (VBAT_*, SW_*, ISNS_PWR, VSERVO_REG, +V_SERVO, BOOT_5V, SENSE_P/N, +5V)
  näher als 5,0 mm. Damit liegt keine Sperrfläche auf einem kritischen Pfad.
  Signalkupfer muss nur außerhalb der Sperrfläche bleiben.

*Suche* (`hardware/scripts/mounting_holes.py search`, Raster 0,5 mm, ganze
Platine):
- Unter den oben gewählten Abstandsregeln und ohne Umrouten fand die Suche
  vier zulässige Bereiche: oben links, linke Kante Mitte, untere Kante Mitte,
  untere rechte Ecke. Andere Regeln, etwa kleinere Abstände zu niedrigen
  Bauteilen, eine andere Schraubengröße oder lokales Umrouten, können
  weitere Stellen ergeben. Das ist eine Folge der Annahmen, keine
  Eigenschaft der Platine.
- **Oben rechts ist keine Bohrung möglich:** DevKit-Hülle samt Antenne bis
  zur Kante. Zwischen den DevKit-Buchsenleisten liegt ein dichter
  Signalkanal.
- **Unten links:** LED-Stecker J108–J112 und die Logikversorgung.
- Mit denselben Regeln, aber erlaubtem Umrouten von Signalleitungen, findet
  die Suche in der rechten Hälfte nur (90…91 | 81).

| Bohrung | Lage (K1) | nächstes Kupfer F/B | nächstes Leistungskupfer | Bemerkung |
|---|---|---|---|---|
| H1 | (21,0 \| 4,0) | 9,3 mm (J101-Pad) | > 9 mm | neben XT30, Ecke oben links 21 mm entfernt |
| H2 | (4,0 \| 43,0) | 5,2 mm (+5V) | 5,2 mm | linke Kante Mitte |
| H3 | (91,0 \| 81,0) | 5,8 mm (VBAT_SW_DRV) / 5,9 mm (VBAT_PROT) | 5,9 mm | links von SW501 |
| H4 | (146,0 \| 81,0) | 3,81 mm (VBAT_OK_BUF, Signal) | > 5 mm | liegt unter der geschätzten USB-Stecker-/Kabelhülle (10,4–17,4 mm hoch). Der Kopf kollidiert nicht, die Schraube muss aber **vor** dem USB-Kabel gesetzt werden |

Abstände der Lochmitten:
- H1–H2 42,5 mm, H2–H3 94,9 mm, H3–H4 55,0 mm;
- H1–H4 146,8 mm, H2–H4 147,0 mm.

**Mechanische Schwäche:** Das DevKit-Feld oben rechts (ca. 25 × 62 mm) hat
keine eigene Stütze. Steckkräfte beim Einsetzen des DevKits wirken auf eine
Kragzone. Am Chassis ist dort eine Auflage ohne Schraube vorzusehen, oder
das DevKit wird vor dem Einbau gesteckt.

*Umsetzung*:
- **Footprint:** `ProjectFootprints:MountingHole_3.2mm_M3_NPTH_Keepout`
  (`make_mounting_hole.py`). Grundlage ist KiCads MountingHole_3.2mm_M3,
  ergänzt um die Sperrflächen, die Courtyards beider Seiten und die Umrisse von
  Kopf, Scheibe und Abstandshalter.
- **Schaltplan:** Symbole Mechanical:MountingHole H1–H4 im Hauptblatt, nicht
  in der BOM, mit dem Hinweis „vorläufig“ (`add_mounting_symbols.py`).
- **Board:** übernommen mit `build_board.py`, gesetzt und gesperrt mit
  `mounting_holes.py place`. Die fünf alten Kommentarmarken sind entfernt.
- **Bestückungsdruck** (`mounting_silk.py`):
  - Referenzen H1–H4 nur auf F.Fab (H1 hätte über der Kante gestanden);
  - Platinentext „ENABLE“ lag über H3: Ein Platz in 1,5 mm Höhe fand sich
    in 15 mm Umkreis von SW501 nicht. Er steht jetzt senkrecht links neben
    SW501, 1,2 mm hoch, 0,2 mm Strich (JLCPCB ≥ 1,0 / 0,15 mm);
  - Referenz R301 lag unter der H2-Scheibe und steht jetzt rechts von R301.
- **Nicht verändert:** Schaltung, Routing und Bauteillagen. Geändert sind nur
  die GND-Flächen, die um die Sperrflächen neu gefüllt sind.

*Prüfung*:
- ERC 0, DRC (alle Schweregrade, mit JLCPCB-Regelsatz) 0 Verstöße und 0 offene
  Verbindungen, Schaltplan-Parität PASS.
- DRAFT-Paket neu erzeugt. Die Bohrdatei enthält Werkzeug T13 Ø 3,200 mm mit
  Attribut `NonPlated,NPTH` und vier Treffern an den Sollpositionen.
- **Grenze dieser Prüfung:** Der Export von `kit export` schreibt PTH und
  NPTH in **eine** Excellon-Datei (KiCad „MixedPlating“). Ob ein Loch
  metallisiert wird, steht dort nur in Kommentarzeilen (X2-Attribute
  `; #@! TA.AperFunction,NonPlated`). Ein CAM-System, das diese Zeilen nicht
  auswertet, metallisiert alle Löcher. Die vier Treffer bestätigen also nur
  Lage und Durchmesser, nicht die Erkennung als unmetallisiert. JLCPCB
  veröffentlicht dazu keine verbindliche Aussage.
- **Vergleich mit getrennten Dateien**
  (`kicad-cli pcb export drill --excellon-separate-th`, Ausgabe
  `qa/generated/fab/drill_separate/`): `RoverCore-NPTH.drl`
  (FileFunction `NonPlated,1,4,NPTH`) enthält genau 10 Löcher:
  - 4 × 3,2 mm H1–H4;
  - 2 × 3,0 mm Rastzapfen J102/J103;
  - 4 × 2,7 mm Modulbefestigung J115/J116.
  `RoverCore-PTH.drl` enthält keines davon.
- **Umgestellt (Owner-Entscheid 2026-11-18):** `kit export` schreibt jetzt
  getrennte Dateien `RoverCore-PTH.drl` und `RoverCore-NPTH.drl` (mit je
  einer Bohrkarte), **keine** gemeinsame Datei mehr. Damit lassen sich keine
  Bohrungen doppelt hochladen. Geändert ist `tools/release/exports.py`
  (`--excellon-separate-th`, vermerkt in `tools/VENDORED.md`).
  `fab_package_check.py` meldet eine gemeinsame Datei als Fehler.
- **DRAFT-Paket neu erzeugt und geprüft** (`fab_package_check.py`, Vergleich
  mit dem vorherigen Paket):
  - NPTH: 10 Löcher, deckungsgleich mit dem Board innerhalb 0,0005 mm:
    - Die Datei ist Excellon „absolute / metric / decimal“ mit höchstens 3
      Nachkommastellen, also 0,001 mm Auflösung. Die Toleranz ist eine halbe
      Einheit der letzten Stelle und wird aus der Datei abgeleitet.
    - Der Vergleich rundet nicht.
    - Die zuvor gemeldeten Abweichungen von 0,01 mm kamen aus meiner eigenen
      Rundung beider Seiten auf 2 Stellen, nicht aus der Datei.
    - Gegenprobe: Ein um 0,001 mm verschobenes Loch wird als Fehler
      gemeldet.
    Die Löcher im Einzelnen:
    - H1 (83,25 | −54,50), H2 (66,25 | −93,50), H3 (153,25 | −131,50) und
      H4 (208,25 | −131,50), je Ø 3,2 mm;
    - J102/J103 je Ø 3,0 mm;
    - J115/J116 je 2 × Ø 2,7 mm.
    Angegeben sind Bohrdatei-Koordinaten (Seitenursprung, Y nach oben).
  - PTH: 416 Löcher = Board:
    - Vias und Bauteile: 0,25 × 196, 0,3 × 42, 0,4 × 69, 0,5 × 6,
      0,75 × 16;
    - THT: 1,0 × 75, 1,02 × 6, 1,78 × 4, 1,9 × 2.
  - Alle 426 Treffer sind nach Art, Durchmesser und Koordinate identisch mit
    der vorherigen gemeinsamen Datei. Der Bestand ist also unverändert.
- **Für die Bestellung:** beide Dateien hochladen, in der Datei-Vorschau des
  Fertigers prüfen, dass die 10 NPTH-Löcher ohne Hülse dargestellt sind, und
  im Bestellhinweis „4 × Ø 3,2 mm, 2 × Ø 3,0 mm, 4 × Ø 2,7 mm NPTH“
  vermerken.
- Abgleich Paket ↔ Board unverändert, einziger offener Fehler D502 ohne
  Teilenummer.
- **Bilder:**
  - bemaßte Draufsicht `docs/images/mounting_top.jpg`
    (`render_mounting_drawing.py`);
  - 3D-Ansichten mit orangen Hüllkörpern für Scheibe, Kopf und
    Abstandshalter (`render_populated_review.py`).

*Mechanischer Abgleich*: Prüfliste, 1:1-Druckvorlage und Vorschlag für die
Auflage unter dem DevKit in [rev1-mechanik-abgleich.md](rev1-mechanik-abgleich.md).
Die Auflage hält mindestens 3 mm Abstand zum Antennenfreiraum. Sie muss
breit, isolierend und ohne scharfe Kanten sein, denn der Lötstopplack ist
kein Scheuerschutz. Ihre Höhe richtet sich nach dem gemessenen Abstand,
ohne die Platine vorzuspannen.

*Offen*: Lage gegen Chassis bzw. Fahrzeugbefestigung bestätigen,
Abstandshalterlänge, Schraubentyp (Linsen- oder Zylinderkopf), Auflage unter dem
DevKit-Feld. Bis dahin bleibt das Paket DRAFT/NO-GO.

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

- **Vorschlag:** 150 × 100 mm = 15 000 mm², **vorerst beibehalten**
  (Owner-Review).
  - Die Courtyard-Belegung von ca. 46 % ist nur eine Kennzahl. Sie belegt
    weder eine Routingreserve noch, dass sich die Platine verkleinern lässt.
  - Über eine kleinere Fläche wird erst nach Ausarbeitung der kritischen
    Verbindungen entschieden.
- Die Breite bestimmt die obere Reihe: Eingang 35 + Servoregler 57,5 +
  Aktuatoren 29 + DevKit 28,5 mm.
- Mögliche spätere Verkleinerung (nicht geprüft, keine Aussage über die
  Größe): Sensor- und Displaymodule an Kabel oder auf eine eigene Ebene, die
  untere Reihe enger.
- **Befestigung:** Marken für M3 (3,2 mm) bei (3,5 | 3,5), (3,5 | 96,5),
  (146,5 | 96,5) und (118 | 66).
  - Die Ecke oben rechts ist durch die Antenne belegt.
  - Die Lage folgt dem Chassis.

## 6. Ansichten

Erzeugt mit `hardware/scripts/render_placement_review.py` (pcbnew-Python) und
`kicad-cli pcb render` in `qa/generated/placement/`. Das ist erzeugte Ausgabe
und nicht versioniert (`.gitignore`); die Bilder sind kein Freigabenachweis.

- **Luftlinien:** KiCads eigener Ratsnest, also die `unconnected_items` aus
  `kicad-cli pcb drc` (dieselben Linien wie im Editor), **einschließlich
  GND** in Schwarz. Nicht mehr selbst berechnet.
- **Seiten:** Ober- und Unterseite getrennt. Die Unterseite ist von unten
  gesehen (gespiegelt); Teile der anderen Seite sind blass.
- **Kupfer:**
  - Leitungen, Vias und Füllungen der Außenlage der Ansicht; F rot, B blau.
  - Die andere Außenlage ist blass; die GND-Innenlagen sind nicht
    gezeichnet.
- Stand der Bilder: nach Probe-Routing (3b), Feinplatzierung (3c) und Bedienzone (3d).

| Datei (je `_top` und `_bottom`, `.png`/`.svg`) | Inhalt |
|---|---|
| `overview` | ganze Platine: Courtyards, Pads, Gruppenrahmen, Kontur, Bohrungsmarken, Ratsnest |
| `detail_input_logic` | Eingangsschutz und Logikversorgung |
| `detail_servo_regulator` | Leistungsstufe LTC7803 mit Feinplatzierung, Kelvin-Abgriffe, C403/C404 auf der Unterseite |
| `detail_devkit_usb` | Aktuatoren, DevKit mit Antennenrand, USB-Zugang, Controller-Peripherie |
| `detail_logic_supply` | TPS54302 mit Feinplatzierung (3c) |
| `detail_output_stages` | U201, Kanalspalten, Stecker J102–J106 (3c) |
| `detail_controller_periphery` | Wächter, Latch, VBAT-Messung (3c, 3d) |
| `operator_zone` | Bedienzone: Modul- und USB-Hüllen (blau), Fingerzonen r = 10 mm (grün frei / rot verletzt), Teile ohne 3D-Modell rot gestrichelt (3d) |
| `oblique_envelopes.png` | schräge (isometrische) Hüllenansicht ohne 3D-Modelle: Modul- und Steckerhüllen mit geschätzten Höhen, Taster, Fingerzonen, Teile ohne Modell rot (3d) |
| `render_3d_top.png`, `render_3d_bottom.png`, `render_3d_iso.png` | 3D-Ansichten nach Probe-Routing und Feinplatzierung (Teile ohne Modell fehlen, siehe models_3d) |

- Die Dateien ohne `_top`/`_bottom` (`overview.png` usw.) stammen vom ersten
  Renderer (GND ausgeblendet, Luftlinien selbst berechnet) und sind veraltet.
  Sie wurden mit `a8ba76a` eingecheckt und sind auf Owner-Entscheid wieder aus
  Git entfernt (lokal behalten).

Abgleich (normal, verändert keine Platzierung):

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/scripts/build_board.py
```

Vorläufige Platzierung eines Blatts erneut anwenden (überschreibt dessen Positionen):

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/scripts/build_board.py --bootstrap --sheet ServoPower
```

Ansichten:

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/scripts/render_placement_review.py
```

## 7. Offen (vor Routing bzw. Fertigungsfreigabe)

- Chassis: Kontur, Bohrungen, Steckerzugang (XT30, Micro-Fit, USB), Bauhöhen
  über und unter der Platine.
- Feinplatzierung und Routing:
  - Feinplatzierung der Servo-RUN/Messgruppe und der Sensorgruppe
    (Eingangsschutz und Schnittstellen: 3e);
  - Routing der übrigen Platine (Stand 3f): als Nächstes Servoschiene
    +V_SERVO zu J102–J105, dann +5V/+3V3 und die Signale;
  - Kühlkupfer Q401/Q402/L401;
  - Referenztexte (Silkscreen), darunter Referenzfelder nahe der
    Platinenkante.
- Nach dem Beginn von Feinplatzierung und Routing wird
  `build_board.py --bootstrap` nicht mehr angewendet. Der normale Abgleich
  bleibt erlaubt.
- Thermik: `scripts/kit thermal analyze` nach der Feinplatzierung. O-16:
  WROOM nur bis 65 °C, also Abstand zu den Reglern prüfen.
- Lagenaufbau: Fertigungsvorgabe in 3a (35/17,5/17,5/35 µm, Prepreg
  0,1 mm, Hülse IPC-6012 Kl. 2); beim Fertiger zu bestätigen. Bis dahin
  gelten die Rechnungen nur unter dieser Voraussetzung.
- 3D-Modelle der 17 Footprints ohne Modell (nur echte Herstellerdaten).
- Weiter offen aus dem Schaltplan:
  - O-36 (ESC-Test);
  - O-37-Messungen und A11/A12;
  - Abfragenachweis < 12 ms auf dem ESP32;
  - Unterspannungs-Prüfpunkt V.18.
