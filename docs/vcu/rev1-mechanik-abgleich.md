# Rev 1 / K1: Mechanischer Abgleich am Fahrzeug

> **Überholt durch die mechanische Überarbeitung:** H1–H4 sind nur ein
> vorläufiger Entwurf. Das neue Lochbild steht im
> [Vorschlag](rev1-befestigung-vorschlag.md); die Prüfliste unten gilt
> sinngemäß für das neue Lochbild.

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
| M9 | Durchbiegung beim Einstecken des DevKits ohne und mit Auflage (siehe unten): Messuhr oder Lineal am DevKit-Feld; außerdem Ebenheit nach dem Festschrauben **ohne** gestecktes DevKit | Vorschlag: ≤ 0,5 mm Durchbiegung beim Stecken; Platine nach dem Festschrauben eben (keine Vorspannung durch die Auflage); keine Rissgeräusche, kein Lösen von Lötstellen | OFFEN |
| M10 | Antenne: Abstand des WROOM-Moduls zu Metallteilen des Chassis | keine Metallteile im Antennenbereich über der oberen Kante | OFFEN |

## Auflage unter dem DevKit

- **Problem:** Das DevKit-Feld oben rechts hat keine eigene Befestigung. Die
  nächsten Bohrungen sind H4 (unten rechts) und H1/H3 weit links. Die
  Steckkraft beim Einsetzen des DevKits biegt die Platine dort durch.
- **Freie Fläche auf der Unterseite** (Suche auf dem Board):
  - x 128–144, y 1–41 (K1) zwischen den beiden Buchsenreihen;
  - mindestens 1,5 mm Abstand zu Pads und Courtyards der Unterseite, keine
    Vias;
  - dort laufen Leitungen nur unter Lötstopplack.
- **Antennenfreiraum:** Die Sperrfläche des DevKit-Footprints (alle
  Kupferlagen) reicht auf der Platine bis y 1,0 (x 126,9–146,9); der größte
  Teil liegt über der Oberkante. Die Auflage darf nicht hineinragen.
  Vorschlag in der Vorlage: Auflagefeld x 129–143, y 4–40, mindestens 3 mm
  von der Sperrfläche entfernt, mit Stützpunkten bei (136 | 12) und
  (136 | 34). Die Auflage reicht nicht über die Oberkante hinaus, und im
  Antennenbereich über der Kante darf kein Chassisteil liegen (M10).
- **Ausführung:**
  - **breite, isolierende** Auflage ohne scharfe Kanten: Kunststoffblock mit
    gebrochenen Kanten, Abstandshalter mit großer, flacher Kunststoffkappe
    oder ein Gummi- bzw. Moosgummipuffer;
  - mindestens etwa Ø 8–10 mm Kontaktfläche je Stützpunkt (Vorschlag), damit
    die Last verteilt wird;
  - **kein Metall.** Der Lötstopplack über den Leitungen ist eine
    Isolation, aber **kein mechanischer Scheuerschutz**. Ein Teil, das bei
    Vibration reibt oder punktuell drückt, kann ihn durchscheuern. Eine
    zusätzliche Kapton- oder Isolierfolie auf der Kontaktfläche ist
    sinnvoll;
  - nicht unter die Buchsenreihen: deren THT-Stifte stehen unten über.
- **Höhe:** Die Auflage muss zur **gemessenen** Distanz zwischen Chassis und
  Platinenunterseite passen, also zur tatsächlichen Länge der eingebauten
  Abstandshalter samt Toleranz. Sie darf die Platine **nicht vorspannen**:
  nach dem Festschrauben der vier Schrauben gerade anliegen, ohne die
  Platine anzuheben. Prüfen mit Lineal oder Messuhr am DevKit-Feld: Die
  Platine bleibt eben (M9), ein Spalt von wenigen Zehnteln vor dem
  Einstecken ist zulässig. Eine elastische Auflage (Moosgummi) gleicht
  Toleranzen aus, ohne die Platine zu biegen.
- **Alternative:** das DevKit vor dem Einbau stecken und am Fahrzeug nicht
  mehr ziehen.

## Reihenfolge am Fahrzeug

1. Vorlage mit 100 % drucken und beide Kontrollmaße nachmessen.
2. Vorlage auflegen, Stecker samt Kabeln und Abstandshalter anhalten (M1–M8, M10).
3. Abstand Chassis–Platinenunterseite messen, Auflage danach wählen (M9).
4. Erst dann Lochlage, Schrauben, Abstandshalter und Auflage festlegen.

Lochpositionen werden bis zu diesem Abgleich nicht weiter am Rechner
optimiert; erst der Abgleich bestätigt die vorläufige Mechanik oder nicht.

## Danach festlegen

- Lochlage H1–H4 (Board-Änderung nur, wenn M1 sie verlangt), Schraubentyp,
  Abstandshalterlänge, Auflage.
- Bei geänderter Lage: `hardware/scripts/mounting_holes.py` mit den neuen
  Positionen prüfen und setzen, dann DRC, Parität und das DRAFT-Paket neu
  erzeugen.
