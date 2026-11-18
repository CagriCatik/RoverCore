# Rev 1 / K1: Vorschlag Lochbild (mechanische Überarbeitung)

Stand 2026-11-18. **Vorschlag, das Board ist nicht geändert.** Die
Fertigungsvorbereitung ist gestoppt. H1–H4 (Bericht 3n) gelten als
vorläufiger Entwurf: Sie sitzen dort, wo nach dem Routing noch Platz war,
nicht dort, wo die Platine mechanisch gestützt werden sollte. Lokale
Platzierungs- und Routingänderungen sind für das neue Lochbild erlaubt.

![Vorschlag Variante B](../images/mounting_proposal_B.png)

(`hardware/scripts/render_mounting_proposal.py`; Annahmen für Schrauben
und Abstandshalter wie in 3n: M3, Bohrung 3,2 mm NPTH, Kopf Ø 5,7 mm, Scheibe
Ø 7,0 mm, Sechskant-Abstandshalter SW 5,5 (Ø 6,35 mm), Kupfersperre r 3,8 mm,
Werkzeugfreiraum Ø 11 mm frei von hohen Teilen, Lochmitte 4,5 mm vom Rand.)

## Was an den vier Ecken heute im Weg steht (Kontur 150 × 85)

Gerechnet mit `mounting_holes.py` (Board-Kopie, nur lesend):

| Ecke | Lochmitte | Hindernis | Eingriff |
|---|---|---|---|
| oben links | (4,5 \| 4,5) | Courtyard J101 (XT30) 2,8 mm statt 5,5 mm | J101 mit TP101 und F101 um 3 mm nach unten; VBAT_IN/VBAT_FUSED-Flächen lokal neu. Platz: zwischen F101 und C101 sind heute 4,1 mm frei |
| unten links | (4,5 \| 80,5) | J108 (LED 1) mit +5V_LED und LED_1_DIN | LED-Reihe J108–J112 ab x 10 mit 1 mm Abstand (heute 2 mm), R520 und TP506 versetzen, LED-Leitungen lokal neu |
| unten rechts | (145,5 \| 80,5) | eine Signalleitung VBAT_OK_BUF; liegt unter dem USB-Kabel | Leitung umlegen; Schraube nur ohne USB-Kabel erreichbar |
| oben rechts | (145,5 \| 4,5) | rechte DevKit-Buchsenleiste (Pads bei x 148,4), DevKit-Hülle, Antenne über der Kante | nur mit Versetzen des DevKits um ca. 10 mm. Das ist ein großer Eingriff: 44 Kontakte und der Signalkanal zwischen den Buchsen |

Folgerung: Auf der heutigen Kontur lassen sich drei Ecken mit lokalen
Änderungen erreichen. Die vierte, oben rechts, geht nur mit einer
Neuplatzierung des DevKits.

## Varianten

| | A: Kontur bleibt 150 × 85 | **B: Kontur 160 × 85 (rechts +10 mm), empfohlen** | C: Kontur 170 × 85 (links und rechts +10 mm) |
|---|---|---|---|
| Lochbild | 3 Ecken; oben rechts nur innen links vom DevKit (x 112–122), dort ebenfalls blockiert (Pads J103, +3V3-Leitung) – DevKit-Feld weiter ohne Stütze | **151 × 76 mm**, alle vier Ecken | 161 × 76 mm, alle vier Ecken |
| Eingriffe | J101-Gruppe, LED-Reihe, VBAT_OK_BUF, für das vierte Loch zusätzlich J103-Umfeld | J101-Gruppe, LED-Reihe; rechte Löcher in der Erweiterung ohne Eingriff | keine Bauteilbewegung; J101 und J108–J112 liegen dann 10 mm von der Kante |
| DevKit-Abstützung | fehlt weiter, Auflage nötig | Löcher C/D direkt neben dem DevKit-Feld; Auflage weiter sinnvoll, aber nicht tragend | wie B |
| USB-Zugang | Schraube unten rechts unter dem Kabel | D außerhalb der USB-Kabelhülle | wie B |
| Antenne | – | C ca. 9 mm von der Antennen-Sperrfläche, zu prüfen | wie B |
| Nachteil | keine echte vierte Ecke | Platine 7 % größer | Platine 13 % größer; Stecker sitzen nicht mehr an der Kante |

**Empfehlung: B.** Sie bringt vier echte Eckpunkte und beschränkt die Eingriffe
auf zwei lokale Bereiche. Das DevKit, das Leistungsteil des Servoreglers und
das übrige Routing bleiben, wie sie sind.

Zu prüfen bei B:
- **Antenne:** Abstand der Metallschraube C zur Antenne des WROOM-Moduls
  gegen die Espressif-Hinweise zum Metallabstand. Sonst C nach unten
  versetzen, etwa auf y ≈ 16; der Abstand zur Antenne steigt dann auf
  ca. 17 mm.
- **J101-Verschiebung:** Sie verändert den Eingangspfad (VBAT_IN →
  F101 → Q101). Danach sind Kupferpfade und Ströme neu zu prüfen
  (`current_map.py vbat`).
- **Neues Board:** GND-Flächen in der Erweiterung, Lochbild, Bestückungsdruck,
  DRC, Parität und Export neu.

## Benötigte Chassis- bzw. Montagemaße

Ohne diese Angaben bleibt jedes Lochbild ein Vorschlag:

1. **Befestigungsfläche:**
   - Chassisboden oder eigene Montageplatte;
   - Material (Metall oder Kunststoff, wegen der Antenne und einer
     möglichen GND-Verbindung);
   - Dicke;
   - vorhandene Bohrungen oder Gewinde mit Koordinaten und Toleranz.
2. **Größte zulässige Platinenkontur:** Länge × Breite, Abstand zu Wänden und
   Kanten, Ausschnitte oder Rippen im Bereich.
3. **Schrauben und Abstandshalter:**
   - Gewindegröße (M3 oder M2,5), Kopfform, Unterlegscheibe;
   - Abstandshalter: Länge, Schlüsselweite, Material (Metall oder Nylon);
   - Durchgangsloch oder Gewinde in der Platte;
   - gewünschte Schwingungsdämpfung (Gummitüllen).
4. **Bauhöhe:**
   - frei über der Platine (DevKit mit USB-Stecker ca. 17,4 mm,
     OLED-Modul ca. 14,7 mm, Schätzwerte aus 3g);
   - frei unter der Platine (THT-Stifte, C403/C404/D401).
5. **Zugänge und Richtungen:**
   - Akkukabel (XT30) und Servokabel (Micro-Fit): Seite und Richtung,
     Kabelführung;
   - LED-, Empfänger- und UART-Kabel;
   - USB-Zugang zum DevKit mit eingebautem Gerät (Öffnung im Gehäuse?);
   - Zugang zu RESET, BOOT und ENABLE von oben;
   - Sichtbarkeit des OLED und der Status-LED.
6. **Antenne:** Lage der WROOM-Antenne zum Chassis, Metallteile in ihrer Nähe,
   gewünschte Abstrahlrichtung.
7. **Werkzeugzugang:** Montage von oben (Schraubendreher oder
   Innensechskant) oder von unten; Reihenfolge mit gesteckten Modulen.

## Nächste Schritte

1. Owner wählt die Variante (A, B oder C) und liefert die Maße oben.
2. Danach Kontur und Lochbild gemeinsam festlegen. Lochbild am Chassis
   prüfen (1:1-Vorlage neu erzeugen).
3. Erst dann die lokalen Änderungen am Board:
   - J101-Gruppe, LED-Reihe, gegebenenfalls VBAT_OK_BUF;
   - neue Montage-Footprints, Kontur, GND-Flächen.
4. Danach DRC, Parität, Kupferpfade (`current_map.py`), Fertigungsexport und
   Paketabgleich neu.
