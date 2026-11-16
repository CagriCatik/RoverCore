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

**Lagenaufbau** (Werte aus der Board-Datei, beim Fertiger noch zu bestätigen):

| Lage | Dicke | Rolle |
|---|---|---|
| F.Cu | 35 µm | Bauteile; Leistungsflächen VBAT_PROT, SW, ISNS_PWR, VSERVO_REG, lokale GND-Flächen; kurze kritische Leitungen (TG/SW-Paar, Bootstrap, IC-Umgebung) |
| Prepreg | 0,1 mm | – |
| In1.Cu | 35 µm | **GND, durchgehend, ohne Leitungen**; Bezugs- und Rückstromebene für F.Cu |
| Kern | 1,24 mm | – |
| In2.Cu | 35 µm | **GND, durchgehend** (vorerst); Bezugsebene für B.Cu |
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
- **Kupferdicke:** 35 µm außen bei bis zu 11,2 A Servostrom ist knapp. Ob
  70 µm außen nötig sind, wird mit der Führung der Servoschiene entschieden
  (offen).

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
- Lagenaufbau: festgelegt in 3a. Offen sind Prepreg-Dicke und
  Außenkupfer (35 / 70 µm) beim Fertiger.
- 3D-Modelle der 17 Footprints ohne Modell (nur echte Herstellerdaten).
- Weiter offen aus dem Schaltplan:
  - O-36 (ESC-Test);
  - O-37-Messungen und A11/A12;
  - Abfragenachweis < 12 ms auf dem ESP32;
  - Unterspannungs-Prüfpunkt V.18.
