# RoverCore VCU Rev 1

Modulare VCU-Trägerplatine für einen RC-Rover: steckbares ESP32-S3-DevKitC-1,
IMU, OLED, geregelte Servoschiene (LTC7803, 6,8 V vorläufig, Auslegung 11,2 A),
5-V-Logikversorgung (TPS54302), LED-, Empfänger- und UART-Ausgänge.
KiCad 10.0.7, 4 Lagen, 150 × 85 mm.

!!! warning "Stand 2026-11-18: DRAFT A1 – NOT FOR FABRICATION"
    Layout geschlossen; ERC, DRC und Parität bestehen im lokalen Lauf. Das
    ist ein Werkzeugergebnis. Offen vor der Fertigung: Linienbreite im
    Bestückungsdruck und mechanische Befestigung (Bericht 3l). Alle Strom-, Spannungs- und
    Temperaturwerte in dieser Dokumentation sind Rechen- oder Datenblattwerte;
    sie werden am Muster nach der [Erstinbetriebnahme](bringup.md) geprüft.

![RoverCore Rev 1 mit gesteckten Modulen](images/populated_iso_front.jpg)

**Magenta** = gekennzeichnete Hüllkörper für Carrier-Teile ohne verfügbares
Modell (XT30 mit dunkler Steckseite, Buzzer, Leistungs-FETs, X2SON-Dioden);
**blau** = Hüllkörper der gesteckten Module (DevKit, OLED, IMU). J102/J103
zeigen das Molex-Herstellermodell.
Hüllkörper sind keine Herstellermodelle.

| Mit Modulen | Ohne Module |
|---|---|
| ![Mit Modulen, schräg von vorne](images/populated_iso_front.jpg) | ![Ohne Module, schräg von vorne](images/without_modules_iso_front.jpg) |
| ![Mit Modulen, schräg von hinten](images/populated_iso_rear.jpg) | ![Ohne Module, schräg von hinten](images/without_modules_iso_rear.jpg) |
| ![Mit Modulen, oben](images/populated_top.jpg) | ![Ohne Module, oben](images/without_modules_top.jpg) |
| ![Flach von vorne](images/populated_front_low.jpg) | ![Unterseite](images/populated_bottom.jpg) |

Aus den exportierten Gerber- und Bohrdateien gezeichnet:

| Oberseite | Unterseite (von unten) | Innenlage In1 (GND) |
|---|---|---|
| ![Gerber oben](images/gerber_top.png) | ![Gerber unten](images/gerber_bottom.png) | ![Gerber In1](images/gerber_in1.png) |

## Einstieg

- [Erstinbetriebnahme](bringup.md): Versorgung, D501, Servostrompfad, Abbruchkriterien
- [Versorgung und Boardwahl](vcu/rev1-versorgung-und-boardwahl.md)
- [Pin- und Anschlussplan](vcu/rev1-pin-und-anschlussplan.md)
- [Platzierung, Routing, Fertigung](vcu/rev1-platzierung.md): Strompfade (3j), Fertigerabgleich und DRAFT-Paket (3k)
- Quellen: [GitHub](https://github.com/CagriCatik/RoverCore)
