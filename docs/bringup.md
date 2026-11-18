# Erstinbetriebnahme Rev 1 (Muster A1)

Stand 2026-11-18. Gilt für das DRAFT-Fertigungspaket `rev-A1-DRAFT` (NO-GO).
Alle Sollwerte stammen aus der Auslegung
([Versorgung](vcu/rev1-versorgung-und-boardwahl.md), [Platzierung 3j](vcu/rev1-platzierung.md))
und sind **Rechen- oder Datenblattwerte, keine Messwerte**. Der Plan legt fest,
was gemessen wird, mit welchen Grenzen und wann abgebrochen wird. Die Ergebnisse
gelten nur für die geprüften Muster.

Bis zur Messung vorläufig und hier zu bestätigen: D501 ohne Versetzen (Schritt C),
thermische Belastbarkeit von Servoschiene, Via-Feld und J102/J103 (Schritt E),
Servo-Sollwert 6,8 V (O-19).

## 0. Ausrüstung und Protokoll

- Labornetzgerät 0–15 V, ≥ 15 A, einstellbare Strombegrenzung; für Schritt B ein
  zweites Gerät bzw. der Bereich bis 100 mA mit feiner Auflösung.
- Elektronische Last ≥ 12 A / ≥ 100 W (oder Leistungswiderstände 0,6 Ω / 1,25 Ω).
- Oszilloskop ≥ 4 Kanäle, Tastköpfe mit kurzer Masse; DMM mit 4-Leiter-Messung
  bzw. mV-Bereich.
- Wärmebildkamera und mindestens 2 Thermoelemente (Kapton-Klebeband).
- Protokoll je Schritt: Muster-Nr., Geräte (Typ, Kalibrierstand), Umgebung,
  Firmware-Stand, Einstellungen, Messwerte, Abweichungen. Tabelle am Ende.

Testpunkte: TP101 VBAT_IN, TP102 VBAT_PROT, TP103/TP302/TP402/TP504 GND,
TP301 +5V, TP401 +V_SERVO, TP403 ISERVO_SENSE, TP502 +3V3, TP503 +5V_DEVKIT,
TP505 VBAT_SENSE, TP506 OUT_LOCK, TP501 ACT_ARMED_FB.

## A. Unbestromt

| Nr. | Prüfung | Erwartet | Abbruch |
|---|---|---|---|
| A1 | Sichtprüfung: Polung C101 (Elko), D101 (TVS), D501 (Kathode zu +5V_DEVKIT), D502; Ausrichtung Q101, Q401/Q402, U301, U401, U402; Lötbrücken an U401/U506 (0,5 mm Raster) | wie Bestückungszeichnung (`assembly_refs_top.pdf`) | jede Abweichung |
| A2 | Widerstand gegen GND: VBAT_IN, VBAT_PROT, +5V, +5V_DEVKIT, +3V3, +V_SERVO | kein Kurzschluss (> 100 Ω nach Kondensator-Aufladung; Wert notieren) | < 10 Ω |
| A3 | Widerstand VBAT_PROT ↔ +V_SERVO, +5V ↔ +V_SERVO | kein Kurzschluss | < 1 kΩ |
| A4 | J101 XT30: Pin-Belegung gegen Akku-Stecker (Plus an VBAT_IN) | wie Schaltplan | Abweichung |

## B. Eingang und +5V, ohne DevKit und ohne Servos

Netzgerät an J101, Strombegrenzung **100 mA**.

| Nr. | Stimulus | Erwartet (Auslegung) | Messen | Abbruch |
|---|---|---|---|---|
| B1 | **Verpolung:** −12,6 V, 100 mA | kein Strom (Q101 sperrt); VBAT_PROT ≈ 0 V | Strom, TP102 | Strom > 1 mA |
| B2 | 0 → 9,0 V langsam (≤ 1 V/s) | +5V startet bei EN ein 8,65 V (aus 8,04 V) | Einschaltschwelle an TP102, TP301 | Strombegrenzung spricht an |
| B3 | 9,0 / 11,1 / 12,6 V | TP301 **4,74–5,16 V**; +V_SERVO (TP401) **aus** (kein DevKit → keine Freigabe) | TP301, TP401, Eingangsstrom (Wert notieren, nicht vorab berechnet) | TP401 > 0,5 V |
| B4 | 12,6 V, Oszilloskop an TP301 | kein Schwingen, Welligkeit notieren | Welligkeit, Einschaltverlauf | Schwingen |

## C. DevKit-Versorgung und D501

| Nr. | Stimulus | Erwartet (Auslegung) | Messen | Abbruch |
|---|---|---|---|---|
| C1 | DevKit gesteckt, kein USB, 9,0 V, 500 mA Grenze; Test-Firmware mit WLAN-Sendebetrieb | DevKit startet; +3V3 (TP502) im Datenblattbereich | TP301, TP503, TP502, DevKit-5V-Pin | Reset-Schleifen |
| C2 | wie C1, **kalt** (−20 °C, falls Klimakammer vorhanden) und Raumtemperatur | LDO-Eingang (DevKit-5V-Pin) ≥ **3,77 V** auch im Sendepuls; Rechenwert min. 3,98 V kalt / 4,05 V warm | Minimum am DevKit-5V-Pin mit Oszilloskop (Spitzen-Erfassung), V_F D501 = TP301 − TP503 | Minimum < 3,77 V |
| C3 | DevKit entfernt, elektronische Last 0,55 A an TP503/GND, 12,6 V, 30 min | V_F D501 ≤ 0,52 V (Datenblatt max. bei 0,7 A, 25 °C) | V_F, Gehäusetemperatur D501 (Thermoelement an der Kathode), Platinentemperatur daneben, Umgebung | Gehäuse > 110 °C |
| C4 | Akku stecken bei laufendem USB und umgekehrt | Übernahme durch D501 ohne DevKit-Reset (3.11: Stoßfreiheit zu prüfen) | TP503, TP502, Reset-Leitung | Reset |

**Bewertung D501 (C3):** T_j ≈ T_Gehäuse + P × R_th(j-sp) (60 K/W, Datenblatt;
P = V_F × 0,55 A). Auf 65 °C Umgebung hochgerechnet wird die gemessene
Erwärmung über Umgebung addiert (Schätzung; besser direkt in der Klimakammer).
Liegt T_j dabei über **125 °C**, gilt die vorläufige Entscheidung „nicht
versetzen“ als widerlegt, und D501 bekommt mehr Kathodenkupfer oder wird
versetzt. Die 125 °C sind ein Vorschlag mit 25 K Abstand zu T_j max. 150 °C und
vom Owner zu bestätigen.

## D. Servoschiene ohne Last

Voraussetzung: B und C bestanden. Test-Firmware setzt `SERVO_PWR_EN` (GPIO7);
Freigabe über SW501 (Latch U506, `ACT_ARMED`). Netzgerät 2 A Grenze.

| Nr. | Stimulus | Erwartet (Auslegung) | Messen | Abbruch |
|---|---|---|---|---|
| D1 | ohne SW501-Freigabe, `SERVO_PWR_EN` high | Schiene **aus** (Q403 hält RUN) | TP401 | TP401 > 0,5 V |
| D2 | SW501 drücken | Soft-Start ca. 2,1 ms; TP401 **6,69–6,91 V** | Anlauf und Überschwingen an TP401 (Oszilloskop) | > 7,4 V |
| D3 | `SERVO_PWR_EN` low | Schiene aus | TP401, RUN | bleibt an |
| D4 | Wiederanlaufsperre | Prüfungen 1.1–1.4 aus 3.17 der Versorgungsdokumentation | dort | dort |

## E. Servostrompfad unter Last (blockierte Servos als Ersatzlast)

Last an J102 und J103 (je eine Hälfte), Netzgerät 9,0 V und 12,6 V, Grenze
**12 A** (Eingang bei 11,2 A Ausgang ca. 9–10 A bei 9 V, Schätzung). Nur mit
Aufsicht; Wärmebildkamera auf der Oberseite, Thermoelemente an RS402/Via-Feld
und an einer J102-Lasche.

| Nr. | Stimulus | Erwartet (Rechnung, DC) | Messen | Abbruch |
|---|---|---|---|---|
| E1 | 1 / 2 / 5 / 8 / 11,2 A, je 60 s | TP403 = 0,2 V/A (INA240A3 × 2 mΩ): 11,2 A → **2,24 V** | TP403, TP401, Last-Spannung am J102/J103-Pin | Abweichung TP403 > 5 % |
| E2 | 11,2 A | Abfall TP401 → J102-Pin / J103-Pin **22,5 / 28,2 mV**; GND J102/J103 → J101 **11–12 mV** (Rechnung mit 35/17,5 µm, Hülse 18 µm) | 4-Leiter-mV-Messung direkt an den Pins | Abfall > 2 × Rechenwert (Hinweis auf Fertigungsabweichung oder Lötstelle) |
| E3 | 11,2 A dauernd bis zum Beharrungszustand (ΔT < 1 K in 5 min), 9,0 V und 12,6 V | **kein Rechenwert** – thermischer Nachweis offen | Wärmebild: RS401, RS402, L401, Q401/Q402, Via-Feld an RS402, J102/J103-Laschen, +V_SERVO-Flächen | Oberfläche > 105 °C oder ein Bauteil über seiner Datenblattgrenze |
| E4 | Lastsprung 11 → 0 A und 0 → 11 A | Überschwingen am Servoanschluss ≤ 7,4 V (Schätzung 7,01–7,20 V) | TP401 und J102-Pin, Oszilloskop | > 7,4 V |
| E5 | Last über 11,2 A in Schritten von 0,5 A, je 5 s | Stromgrenze LTC7803 vor 12,2 A (2,2 µH) / 13,1 A (3,3 µH) nutzbar, Spitzengrenze ≤ 18,5 A | Einsetzen der Begrenzung, TP401 | Drossel- oder Shunttemperatur steigt sprunghaft |

Die 105 °C für E3 sind ein Vorschlag (Abstand zur Glasübergangstemperatur
des Standard-FR4 und zu den Steckerkontakten) und vom Owner zu bestätigen.
Erst E2 und E3 zusammen ersetzen die DC-Rechnung in Abschnitt 3j durch
Messwerte; vorher gilt die Servoschiene nur im untersuchten DC-Fall als
unauffällig.

## Protokoll

| Schritt | Stimulus / Grenzen | Erwartet | Gemessen | Bestanden |
|------|------------------------|-----------------|-------------------|------|
| A1 | | | | OFFEN |

Keine Platine bestromen, die nicht nach Schritt A geprüft ist.
