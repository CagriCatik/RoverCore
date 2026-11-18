# Rev 1 / K1: Mechanischer Abgleich am Fahrzeug

Stand 2026-11-18. Die Befestigung H1–H4 ist **vorläufig** (Bericht
[3n](rev1-platzierung.md)). Gefunden wurden die Positionen unter den dort
gewählten Abstandsregeln und ohne Umrouten. Ob sie zur Fahrzeugbefestigung
passen, ist offen. Eine bestandene DRC ersetzt diesen Abgleich nicht.
Lochlage, Schrauben und Abstandshalter werden erst nach diesem Abgleich
festgelegt.

## Vorlage

- `qa/generated/mounting/mounting_print_1to1.pdf` (erzeugt mit
  `hardware/scripts/render_mounting_print.py`, nicht versioniert), A4 quer,
  Maßstab 1:1.
- **Mit 100 % bzw. „Tatsächliche Größe“ drucken**, ohne „An Seite anpassen“.
  Beide Kontrollmaße (waagrecht, senkrecht) mit dem Messschieber nachmessen.
  Bei einer Abweichung über 0,5 mm die Vorlage nicht verwenden.
- Inhalt:
  - Kontur 150 × 85 mm, H1–H4 mit Fadenkreuz, Scheibe Ø 7,0 mm und
    Kupfersperre r 3,8 mm;
  - Kettenmaße vom Bezug (linke obere Konturecke);
  - Steckrichtung der waagrechten Stecker;
  - DevKit-Feld und die freie Auflagefläche auf der Unterseite.

## Prüfungen am Fahrzeug

| Nr. | Prüfung | Kriterium (Vorschlag) | Ergebnis |
|---|---|---|---|
| M1 | Vorlage auf die Montagefläche legen; vorhandene oder mögliche Bohrungen/Gewinde gegen H1–H4 | Lochmitten treffen oder lassen sich bohren; ≥ 4 mm Material um jede Bohrung | OFFEN |
| M2 | Vier Abstandshalter in der geplanten Länge (Annahme 10 mm, SW 5,5) aufsetzen | stehen plan; kein Kontakt zu Chassiskanten, Kabeln, Schrauben | OFFEN |
| M3 | Platz unter der Platine: höchste Teile der Unterseite sind THT-Stifte (Lötseite, ca. 1,5–3 mm Überstand) sowie C403/C404/D401 | ≥ 2 mm Luft zum Chassis bei der gewählten Abstandshalterlänge | OFFEN |
| M4 | J101 XT30 mit Akkukabel stecken (Steckrichtung nach links) | Stecker greifbar, Kabel ohne Knick, kein Zug auf die Lötstellen | OFFEN |
| M5 | J102/J103 Micro-Fit mit Servokabeln (Steckrichtung zur oberen Kante) | Verriegelung bedienbar, Biegeradius der Kabel eingehalten | OFFEN |
| M6 | J104–J112 (senkrecht) mit Kabeln | Kabel kollidieren nicht mit Aufbauten über der Platine | OFFEN |
| M7 | DevKit mit USB-Kabel: Zugang zu beiden USB-Buchsen | Stecker passt; H4-Schraube ist vor dem Kabel gesetzt oder zugänglich | OFFEN |
| M8 | Werkzeugzugang zu H1–H4 mit gesteckten Modulen | Schraubendreher bzw. Innensechskant senkrecht ansetzbar | OFFEN |
| M9 | Durchbiegung beim Einstecken des DevKits ohne und mit Auflage (siehe unten): Messuhr oder Lineal am DevKit-Feld | Vorschlag: ≤ 0,5 mm Durchbiegung, keine Rissgeräusche, kein Lösen von Lötstellen | OFFEN |
| M10 | Antenne: Abstand des WROOM-Moduls zu Metallteilen des Chassis | keine Metallteile im Antennenbereich über der oberen Kante | OFFEN |

## Auflage unter dem DevKit

- **Problem:** Das DevKit-Feld oben rechts hat keine eigene Befestigung. Die
  nächsten Bohrungen sind H4 (unten rechts) und H1/H3 weit links. Die
  Steckkraft beim Einsetzen des DevKits biegt die Platine dort durch.
- **Freie Fläche auf der Unterseite** (Suche auf dem Board):
  - x 128–144, y 1–41 (K1) zwischen den beiden Buchsenreihen;
  - mindestens 1,5 mm Abstand zu Pads und Courtyards der Unterseite, keine
    Vias;
  - dort laufen nur Leitungen unter Lötstopplack.
  - Vorschlag in der Vorlage: Auflagefeld x 129–143, y 4–40 mit zwei
    Stützpunkten bei (136 | 12) und (136 | 34).
- **Ausführung:** eine **isolierende** Auflage ohne Schraube, die nur auf den
  Lötstopplack drückt, etwa Kunststoff-Abstandshalter mit flacher Kappe,
  Gummi- oder Moosgummipuffer. Ihre Höhe entspricht der Länge der
  Abstandshalter; eine leichte Vorspannung ist gewünscht, ein Wölben der
  Platine nicht.
  - Keine Metallteile: Die Leitungen liegen nur unter dem Lötstopplack.
  - Nicht unter die Buchsenreihen: deren THT-Stifte stehen unten über.
- **Alternative:** das DevKit vor dem Einbau stecken und am Fahrzeug nicht
  mehr ziehen.

## Danach festlegen

- Lochlage H1–H4 (Board-Änderung nur, wenn M1 sie verlangt), Schraubentyp,
  Abstandshalterlänge, Auflage.
- Bei geänderter Lage: `hardware/scripts/mounting_holes.py` mit den neuen
  Positionen prüfen und setzen, dann DRC, Parität und das DRAFT-Paket neu
  erzeugen.
