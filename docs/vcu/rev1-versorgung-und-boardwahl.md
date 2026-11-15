# VCU Rev 1 – Versorgungsauslegung und ESP32-Boardwahl

Status: **Entwurf zur Review**, Stand 2026-11-15, **3S-Entwurfsbasis**. Alle
Strom-, Spannungs- und Verlustwerte sind **Schätzungen** und ersetzen keine
Messung am Prototyp. „(Q)" = Herstellerquelle, „(S)" = Annahme oder
Schätzung, die durch Datenblatt oder Messung ersetzt werden muss.

Dieses Dokument deckt Arbeitsschritt 1 und 2 des Projektplans ab. GPIOs und
Footprints werden erst eingefroren, wenn die offenen Punkte in Abschnitt 6
geschlossen sind. Die frühere 2S-Rechnung steht im historischen Anhang A.

## 1. Bestandsaufnahme

- Im Repository `RoverCore` liegt ein natives KiCad-Projekt mit noch leerem
  Schaltplan und PCB. Es gibt **keine ESP32-Anwendungsfirmware**. Die im Plan genannte
  „vorhandene Firmware" muss noch benannt werden (Abschnitt 6, O-1).
- Die Vorgängerprojekte `~/Desktop/pcb/rc-vcu-v2` und `rc-control-shield` sind
  STM32-basiert. Lehre aus `rc-vcu-v2`: Buck-Boost-Servostufe (LM5176, vier
  Schalter, Strom-Shunts, LTC4365-Guard) hat die Revision stark verkompliziert
  und ist weiterhin NO-GO. Für Rev 1 wird deshalb bewusst die einfachste
  Topologie gewählt, die die Anforderungen nachweisbar erfüllt (Abschnitt 3).

## 2. ESP32-Boardwahl

### 2.1 Festlegung

| Merkmal | Festlegung | Quelle |
|---|---|---|
| Board | **ESP32-S3-DevKitC-1-N16R8**, Boardrevision **v1.1** | (Q) Espressif User Guide v1.1 |
| Modul | ESP32-S3-WROOM-1-N16R8, 16 MB Flash, 8 MB PSRAM, PCB-Antenne | (Q) ebd. |
| Bezug | nur Original-Espressif-Board, kein Nachbau | Projektregel |

Begründung: N8/N8R2-Varianten sind laut Espressif **EOL**; N32R16V nutzt
1,8-V-SPI (laut v1.0-Tabelle) und bringt keinen Vorteil. Die U-Variante
(externe Antenne) ist im Fahrzeug nicht nötig.

Bestellnummern bei Distributoren (Mouser/DigiKey) sind **noch nicht geprüft**.

### 2.2 Konsequenzen für die Pinbelegung

| Pins | Einschränkung | Quelle |
|---|---|---|
| GPIO35, 36, 37 | durch Octal-PSRAM belegt, nicht nutzbar | (Q) Espressif; WROOM-1 DS v1.8: N16R8 = Quad-Flash + Octal-PSRAM |
| GPIO19, 20 | USB D-/D+ (nativer USB-Port) | (Q) |
| GPIO43, 44 | UART0, mit dem USB-UART-Wandler CP2102N verbunden (U0RXD über 0-Ω-R7) | (Q) Schaltplan v1.1 |
| GPIO38 | onboard RGB-LED (nur v1.1; v1.0: GPIO48) | (Q) |
| GPIO0, 3, 45, 46 | Strapping-Pins, nur mit definiertem Pegel beim Reset | (Q) ESP32-S3 DS v2.2 Tab. 3-1 |
| ADC | Akkumessung auf ADC1 (GPIO1–10); ADC2 kollidiert mit WLAN | (Q) ESP32-S3 DS v2.2 Tab. 2-8 und Hinweis |

Frei nutzbar bleiben damit 24 GPIOs (1, 2, 4–18, 21, 39–42, 47, 48); GPIO18
scheidet wegen seines High-Glitches beim Einschalten für Ausgänge aus.
Belegt sind 23 GPIOs – Zuordnung im
[GPIO- und Anschlussplan](rev1-pin-und-anschlussplan.md).

Hinweis: Die Revision v1.0 ist noch im Handel. Weil sich die RGB-LED-Pins
unterscheiden, ist v1.0 **nicht** austauschbar; Wareneingang prüft den
Boardaufdruck.

### 2.3 Mechanik

Ausgewertet aus `DXF_ESP32-S3-DevKitC-1_V1.1_20220429.dxf` (Espressif,
Rev 1.1, 2022-04-29), Koordinaten in mm, Ursprung untere linke Boardecke
(USB-Seite):

| Merkmal | Wert | Herleitung |
|---|---|---|
| Platine | 25,40 × 62,865 mm, Eckradius 0,5 mm | Layer `BOARD_OUTLINE` |
| Stiftleisten | 2 × 22 Pins, Raster 2,54 mm | Layer `PADLAYER_TOP`, 22 Pads je Reihe |
| Reihenabstand J1–J3 | 22,86 mm (x = 1,27 / 24,13) | Padmitten |
| Pin-Lage | Pin 1 bei y = 61,30 (Antennenseite), Pin 22 bei y = 7,96 (USB-Seite) | Padmitten, Beschriftung `3V3`/`G` |
| Modul-/Antennenüberstand | 18,0 × 6,31 mm über die Boardkante hinaus (y = 62,84 … 69,15) | Layer `TOP`, Rechteck an der Antennenseite |
| USB-Buchsen | zwei Micro-USB an der Kante y = 0: „UART" links (x ≈ 2,4–9,6), „USB" rechts (x ≈ 15,8–23,0) | Layer `DRILLHOLE` (Schlitze), Beschriftung |
| Befestigungslöcher | **keine** | keine weiteren Bohrungen in der DXF |
| Taster | BOOT und RESET in Boardmitte nahe USB-Ende (y ≈ 16,4) | Beschriftung |

Konsequenzen für den Footprint: zwei 1×22-Buchsenleisten im Abstand 22,86 mm;
unter dem Antennenüberstand (mind. 18 × 6,3 mm plus Abstand) kein Kupfer
auf allen Lagen und keine Bauteile – idealerweise ragt die Antenne über den
Carrier-Rand hinaus. Ohne Befestigungslöcher braucht das DevKit eine
mechanische Sicherung (Halteklammer oder Kabelbinder-Schlitze am Carrier).
Die Werte sind am realen Board mit Messschieber zu bestätigen (O-4),
insbesondere die Bauhöhe für Buchsenleisten und USB-Stecker-Freigang.

## 3. Versorgungsplan (3S-Entwurfsbasis)

**Festlegung Owner, 2026-11-15:** 3S-LiPo ist die Entwurfsbasis (O-19). Der
Abwärtswandler der Servoschiene hat damit in jedem Akkuzustand Regelreserve.
Die höhere Motordrehzahl wird zunächst über den Fahrbefehl begrenzt; das
ersetzt nicht die Prüfung des Antriebs. Die frühere 2S-Rechnung steht nur noch
im historischen [Anhang A](#anhang-a--historische-2s-rechnung-ersetzt-am-2026-11-15).

Alle Zahlen dieses Abschnitts sind **Schätzungen und Kandidaten**. Sie gelten
erst nach Prüfung von Schaltplan, Rechenskript und Prototyp. Rechenweg:
[`hardware/simulations/power/rev1_power_calc.py`](../../hardware/simulations/power/rev1_power_calc.py)
(ohne Argument = 3S-Stand).

### 3.1 Annahmen

| Größe | Wert | Art |
|---|---|---|
| Akku | 3S LiPo: 12,6 V voll, 11,1 V nominal, 9,0 V bei 3,0 V/Zelle | Festlegung |
| Kurzzeitiger Einbruch unter Motorlast | unbekannt | Messung O-3 |
| Wirkungsgrad Servo-Wandler | 90 % | (S) |
| Wirkungsgrad 5-V-Wandler | 85 % | (S) |
| Umgebungstemperatur Elektronik | bis 60 °C für Bauteil-Derating; ESP32-Modul nur bis 65 °C spezifiziert | (S), O-16 |

Der Motor hängt über die Y-Verteilung am selben Akku; sein Strom (Fusion Pro:
60 A dauernd, 200 A Spitze laut Hobbywing) erzeugt am Innenwiderstand einen
Einbruch, den die VCU sieht (O-3).

### 3.2 Strombilanz

**5-V-Netz** (TPS54302 aus dem geschützten Akkueingang)

| Verbraucher | Strom | Art |
|---|---:|---|
| DevKit (ESP32-S3 inkl. WLAN-Spitzen, über DevKit-LDO) | 0,50 A | (S) |
| FS-iA6B Empfänger | 0,10 A | (S); Hersteller nennt nur 4,0–8,4 V |
| 4 × WS2812, je 60 mA weiß | 0,24 A | (S) |
| Buzzer | 0,03 A | (S) |
| Status-LED, Puffer, INA240 | 0,03 A | (S) |
| IMU + OLED (über DevKit-3V3) | 0,03 A | (S); OLED ca. 20 mA (Adafruit) |
| UART-Erweiterung (Budget, Grenzwert) | 0,20 A | Festlegung |
| **Summe / Reglerauslegung** | **1,13 A / ≥ 2 A** | |

**Servoschiene** (LTC7803)

Lenkservos: 2 × **Savöx SW-0231MG+** (Auswahl Owner). Datenblatt (CML
Distribution, Distributor; Hauptwerte von der Savöx-Produktseite bestätigt):
Versorgung **6,0–7,4 V** (HV), Blockierstrom **4,8 A bei 6,0 V / 5,9 A bei
7,4 V**, Leerlauf 5 mA, Betriebsstrom ohne Last 120 mA bei 6 V, Puls
1000–2000 µs (Neutral 1500 µs), 50–360 Hz, 22-AWG-Leitung 450 mm mit
JR-Stecker, IP67, Betriebstemperatur −10 … 50 °C.

| Anschluss | Fahrbetrieb | blockiert | Art |
|---|---:|---:|---|
| Lenkservo vorne | 2,5 A | ca. 5,1 A bei 6,8 V | (S) / Lastabschätzung 3.4 |
| Lenkservo hinten | 2,5 A | ca. 5,1 A | (S) |
| Reserve 1, Reserve 2 | je 0,5 A | je 0,5 A | Festlegung |
| **Summe** | **6,0 A** | **ca. 11,2 A** | |

**Auslegungsziel: 11 A kontinuierlicher Ausgangsstrom** (rechnerisch 11,2 A
bei 6,8 V). Rechnerisch untersucht; thermischer Nachweis von MOSFETs,
Drossel, Shunt, Steckern und Leiterplatte unter festgelegten
Umgebungsbedingungen sowie Messung stehen aus. Das Auslegungsziel ist
**keine Freigabe**, Servos dauerhaft blockiert zu betreiben (Firmware-Reaktion
siehe 3.7, O-20).

Reserveanschlüsse sind auf je 0,5 A begrenzt und nur für Geräte freigegeben,
deren zulässiger Versorgungsbereich die **gesamte tatsächliche
Schienenspannung** abdeckt: 6,69–6,91 V im Regelbereich plus Überschwingen
bei Laständerung (3.4) und plus die Überspannungsschwelle des Reglers im
Fehlerfall (bis 7,81 V). Zwei weitere SW-0231MG+ an den Reserven sind mit
dieser Auslegung nicht möglich (zusammen > 20 A).

**Akkueingang** (P_Servo / 0,90 + 5,65 W / 0,85; Pfadverluste nicht enthalten)

| Fall | Leistung | 12,6 V | 11,1 V | 10,5 V | 9,0 V |
|---|---:|---:|---:|---:|---:|
| Fahrbetrieb (6 A) | 52 W | 4,1 A | 4,7 A | 5,0 A | 5,8 A |
| Worst Case (11,2 A) | 91 W | 7,2 A | 8,2 A | 8,7 A | 10,1 A |

### 3.3 Reglerauswahl

Freigegeben vom Owner am 2026-11-14 (unter 2S); unter 3S weiter gültig, weil
beide Bausteine den Eingangsbereich abdecken.

| Schiene | Baustein | Kennwerte (Datenblatt) | Bemerkung |
|---|---|---|---|
| Servo | ADI **LTC7803** (Controller, externe FETs), MSOP-16-EP, LCSC C1016554 | 4,5–40 V Eingang, 100 % Tastverhältnis („PassThru"), V_FB 0,788–0,812 V, V_SENSE(MAX) 45/50/55 mV, Festfrequenz 340–375–410 kHz, RUN 1,15–1,25 V / 100 mV Hysterese (Rev A) | Kein PGOOD → Schiene über VSERVO_SENSE und ISERVO_SENSE überwacht; JLC-Bestand nur 25; Rev B gegenlesen |
| 5 V | TI **TPS54302**, TSOT-23-6, LCSC C311983 | 4,5–28 V, 3 A, 400 kHz, V_REF 0,596 V ±2,5 %, EN abs. max. 7 V (SLVSDG6C) | Kein PGOOD; EN nie direkt an VIN |

Verworfen bzw. verglichen: TI LM61495 (98 %, Stromgrenze sinkt bei hohem
Tastverhältnis), TI LM5148 (ca. 99 %), Pololu D42V110F6 (fester Ausgang 6 V
±3 %, 11 A nur typisch bei 42 V ohne Kühlkörper). Bausteine von MPS,
Richtek, Silergy, Diodes nicht aus Datenblättern verifiziert.

### 3.4 Servoschiene: Sollwert und Spannung am Servoanschluss

**Bewertungskriterium:** die Versorgungsspezifikation des kompletten Servos
(6,0–7,4 V) **am Servoanschluss**, also am JR-Stecker des Servos. Die eigene
Leitung des Servos gehört zum Servo.

**Kandidat: 6,8 V** (vorläufig, Festlegung Owner 2026-11-15) –
R_B = 75,0 kΩ, R_A = 10,0 kΩ, 0,1 %: **6,69–6,91 V** mit V_FB ±1,5 %.

Strompfad je Lenkservo (Schätzung):

| Abschnitt | Widerstand | trägt |
|---|---:|---|
| Ausgangs-Messshunt (3.6) + gemeinsame Leiterbahn + und GND | 2 + 3 mΩ | **Gesamtstrom** der Schiene |
| Leiterbahnzweig zu J102 bzw. J103 | 2 mΩ | Strom eines Servos |
| Micro-Fit, 2 Kontakte | 20 mΩ neu / 40 mΩ gealtert (Molex: 10 / 20 mΩ max. je Kontakt) | Strom eines Servos |
| Adapterkabel 20 AWG, 2 × 0,2 m | 13 mΩ | Strom eines Servos |
| JR-Steckverbindung, 2 Kontakte | ca. 20 mΩ (nicht belegt) | Strom eines Servos |

Lastfall: beide Lenkservos gleichzeitig blockiert, Reserven je 0,5 A. Als
**vereinfachte Lastabschätzung** wird der blockierte Servo als Widerstand
gerechnet (6,0 V / 4,8 A = 1,250 Ω; 7,4 V / 5,9 A = 1,254 Ω). Ein digital
geregelter Servo ist kein konstanter Widerstand; das Modell belegt weder die
Stromaufnahme noch das dynamische Verhalten.

| Regler | Kontakte | Schiene | je Servo | am Servoanschluss |
|---|---|---:|---:|---:|
| 6,69 V (Bandunterkante) | neu | 11,2 A | 5,1 A | 6,35 V |
| 6,69 V | gealtert | 11,0 A | 5,0 A | **6,25 V** |
| 6,80 V (nominal) | gealtert | 11,2 A | 5,1 A | 6,36 V |
| Fahrbetrieb 2 × 2,5 A, 6,69 V | gealtert | 6,0 A | 2,5 A | 6,47 V |
| Leerlauf, Bandoberkante | – | – | – | 6,91 V |

Obere Grenze 7,4 V:

| Fall | Spannung | Bewertung |
|---|---|---|
| Regelbereich | ≤ 6,91 V | eingehalten |
| Überschwingen bei Lastabwurf 11 A → 0 | ca. 0,10–0,29 V bei angenommener Durchtrittsfrequenz 30–10 kHz und 606 µF → 7,01–7,20 V | Schätzung; Regelkreis nicht ausgelegt, **messen** |
| Einschaltüberschwingen | Soft-Start 2,1 ms; Wert unbekannt | **messen** |
| Überspannungsschwelle LTC7803 (V_FB +7 … 13 %) | bis 7,81 V | nur Fehlerfall; schützt die Servos **nicht** vor Reglerfehlern |

Der Sollwert wird erst nach Messung des Schleifenwiderstands und der
Überschwinger am Prototyp festgeschrieben; die Lastspannung wird dazu **am
Servostecker** gemessen.

### 3.5 Dimensionierung LTC7803 (3S)

Grundlage LTC7803-Datenblatt Rev A (*Electrical Characteristics*,
*Applications Information*).

| Größe | Wahl | Rechnung / Begründung |
|---|---|---|
| Schaltfrequenz | 375 kHz, FREQ an GND | Festfrequenz 340–375–410 kHz |
| Betriebsart | Forced Continuous, MODE an INTVCC | Konstanter Rippel; Rückspeisung siehe unten |
| Drossel | **2,2 µH oder 3,3 µH – zu prüfen**, I_sat ≥ 20 A, DCR ≤ 5 mΩ | Rippel bei 12,6 V: 3,8 A (2,2 µH) / 2,5 A (3,3 µH), worst case (f_min, L −20 %) 5,2 / 3,5 A. Nutzbarer Ausgangsstrom 12,2 A / 13,1 A. Sense-Rippel 11,4 mV / 7,6 mV (Datenblatt empfiehlt 10–20 mV). Für 3,3 µH Sättigung, Temperatur, DCR, Stromgrenze und Regelkreis prüfen |
| Strom-Shunt | **3 mΩ, 1 %, ≥ 2 W, breite Bauform** | Der LTC7803 begrenzt den **Spitzenwert des Drosselstroms**. Nutzbar = V_SENSE,min / (R × 1,01) − ½ ΔI_L,worst. Spitzengrenze max. 55 mV / 2,97 mΩ = 18,5 A → I_sat der Drossel. Verlust 0,38 W bei 11,2 A. Nicht enthalten: mögliche Abhängigkeit der Schwelle vom Tastverhältnis (Rev A ohne Kurve) |
| FETs oben/unten | Infineon BSC026N04LS, 40 V, R_DS(on) max 3,6 mΩ bei 4,5 V | Leitverluste bei 11,2 A (R_DS × 1,4): 9,0 V 0,48 / 0,15 W, 12,6 V 0,34 / 0,29 W; Schaltverluste nicht enthalten |
| Ausgangsspannung | R_B 75,0 kΩ / R_A 10,0 kΩ, 0,1 % | 6,80 V (6,69–6,91 V), 3.4 |
| Unterspannung (RUN) | R_B 140 kΩ (VIN → RUN) / R_A 20 kΩ | ein 9,60 V (9,20–10,00 V), aus 8,80 V; RUN bei 21,5 V = 2,7 V (abs. max. 40 V) |
| Soft-Start | C_SS 33 nF | 2,1 ms; Ladestrom in ca. 606 µF ≈ 2,0 A |
| Eingangskondensatoren | MLCC ≥ 35 V direkt am Leistungsteil + Eingangs-Bulk ≥ 35 V | I_RMS bei 12,6 V und 11,2 A ≈ 5,6 A – mehr MLCC als unter 2S nötig (O-17) |
| Ausgangskondensatoren | 2 × 270 µF / 16 V Polymer (16SVPG270MX) + 3 × 22 µF / 16 V X7R | – |
| Kompensation (ITH) | Startwerte aus Datenblatt-Typschaltung | Durchtrittsfrequenz und Phasenreserve im Labor bestimmen; davon hängt das Überschwingen in 3.4 ab |
| Abschaltung | `SERVO_PWR_DIS` (GPIO7) → Transistor zieht RUN auf GND | **Reglerabschaltung**, keine Leistungstrennung, siehe unten |

**Rückspeisung und Abschaltung (nicht bestätigt):** Im Forced-Continuous-Modus
kann der Wandler Energie vom Ausgang zum Eingang zurückführen; über den
eingeschalteten Verpol-P-FET kann sie in den Akku gelangen. Bei RUN low sind
beide FETs aus; die Body-Diode des High-Side-FETs sperrt in Richtung
Akku → Schiene. Ob und wohin Rückspeisung eines bewegten Servos dann fließt,
wie lange die Ausgangsladung (ca. 606 µF bei 6,8 V ≈ 14 mJ) ansteht und
welche Entladepfade es gibt, wird anhand der tatsächlichen Schaltung geprüft
und am Prototyp gemessen.

### 3.6 Strommessung der Servoschiene (O-18)

Gesamtstrom-Überlastindikator, keine Erkennung eines einzelnen blockierten
Servos.

| Größe | Wahl | Begründung |
|---|---|---|
| Messstelle | eigener **2-mΩ-Shunt im Ausgang** (nach den Ausgangskondensatoren, vor J102–J105) | INA240-Eingangsstrom 90 µA je Eingang (SBOS662C, Tab. 7.5) würde am LTC7803-Shunt über dessen RC-Filter die Stromgrenze verfälschen; der Ausgangsshunt misst den Servostrom statt des Drosselstroms |
| Verstärker | **TI INA240A3** (Verstärkung 100), Versorgung 3,3 V | Gleichtakt −4 … 80 V, Verstärkungsfehler ≤ 0,2 %, Offset ≤ 25 µV, Ausgang bis V_S − 0,2 V |
| REF1/REF2 | an GND (unidirektional) | Datenblatt 8.4.2 |
| Eingangsfilter | keines; Serienwiderstände ≤ 10 Ω | Datenblatt 9.1.1 |
| ADC | GPIO1 = ADC1_CH0 (`ISERVO_SENSE`), ATTEN3 0–2,9 V | 11,2 A → 2,24 V, Endwert 2,9 V ≈ 14,5 A |
| Genauigkeit | vorläufig ±0,25 A **nur aus dem ADC-Fehler** (±50 mV, ESP32-S3 DS Tab. 5-6) | Gesamtbudget aus Shunt-Toleranz und TCR, Verstärker, ADC, Temperatur und Kalibrierung **nachzuweisen** |
| ADC-Filterung, Kalibrierung | RC am Ausgang, Mittelung in Firmware; Kalibrierung mit Referenzlast | Werte im Schaltplan / Bring-up |

### 3.7 Akku-Schwellen und Fehlerreaktion

Die VCU misst nur die **Gesamt-Akkuspannung**. Das ist keine Zellüberwachung
und keine vollständige LiPo-Entladeüberwachung; ungleich entladene Zellen
werden nicht erkannt.

| Schwelle | Wert (Vorschlag) | Art |
|---|---|---|
| Firmware Warnung | 10,8 V (3,6 V/Zelle) | gefiltert unter Last, Vorschlag |
| Firmware Fehler → Antrieb gesperrt | 10,5 V (3,5 V/Zelle) | Vorschlag; Messfehler ca. ±0,35 V (3.9) |
| ESC-LiPo-Abschaltung | 3,25 V/Zelle = 9,75 V | Rückfallebene, im ESC einstellen (Zellenzahl 3S/Auto) |
| Hardware: Servoschiene aus (RUN) | 8,80 V | Reglergrenze, keine Akkuüberwachung |
| Hardware: Logik aus (EN TPS54302) | 8,0 V | Reglergrenze, keine Akkuüberwachung |

Ein versehentlich gesteckter 2S-Akku (≤ 8,4 V) liegt unter beiden
Einschaltschwellen (9,60 V und 8,6 V); die Platine bleibt aus.

Fehlerreaktion (O-20, offen): Antrieb sperren. Die Lenkversorgung wird
**nicht** pauschal bei jeder Stromspitze abgeschaltet; zeitabhängige
Schwellen, Hysterese und das Lenkverhalten im Fehlerfall werden in der
Firmware-Spezifikation festgelegt. PWM abzuschalten ist keine garantierte
Leistungsabschaltung eines digitalen Servos.

### 3.8 Dimensionierung TPS54302 (3S)

| Größe | Wahl | Rechnung / Begründung |
|---|---|---|
| Drossel | 10 µH, I_sat ≥ 6 A, DCR ≤ 30 mΩ (Würth 74439346100) | ΔI_L worst bei 12,6 V 1,3 A, I_pk 2,7 A bei 2 A |
| Ausgangsspannung | R2 100 kΩ / R3 13,3 kΩ, 1 % | 5,08 V (4,86–5,30 V) |
| Ausgangskondensatoren | 2 × 22 µF / 16 V X7R + C_FF 75 pF | TI-Referenz Abb. 7-1 |
| Eingangskondensatoren | 10 µF ≥ 35 V X7R + 0,1 µF | Spannungsfestigkeit für 3S und TVS |
| BOOT | 0,1 µF X7R | Datenblatt 7.2.3.2 |
| Unterspannung (EN) | R4 69,8 kΩ / R5 11,5 kΩ | Gleichungen 1/2: ein 8,6 V, aus 8,0 V; EN bei 21,5 V ≈ 3,0 V < 7 V abs. max. |

### 3.9 Eingangsschutz und Messeingänge (3S)

Pfad: **J101 XT30 → F101 Sicherung → Q101 Verpol-P-FET → D101 TVS →
Eingangs-Bulk → Regler**.

| Ref | Funktion | Kandidat | Kennwerte (Quelle) |
|---|---|---|---|
| J101 | Akkustecker | Amass XT30PW-M30.G.Y, LCSC C431092 | 20 A (16 AWG, ΔT ≤ 85 K), 80 V DC, ≤ 1,2 mΩ (Amass 2025V0) |
| F101 / X101 | Sicherung / Halter | Mini-Flachsicherung **15 A** (Kandidat, O-17) / Keystone 3568 (30 A, JLC-Bestand 0) | Serie 32 V, 1 kA, ISO 8820-3; Auslösezeiten 135 % 0,75–600 s, 200 % 0,15–5 s (Eaton TD 2048, Drittspiegel) |
| Q101 | Verpolschutz | Vishay SiRA99DP, LCSC C3289459 | −30 V, R_DS(on) max 2,65 mΩ bei −4,5 V, V_GS +16/−20 V (S23-1023 Rev B) |
| D102 + R | Gate-Schutz Q101 | Zener zwischen Gate und Source, Vorwiderstand Gate → GND | siehe unten |
| D101 | Überspannung | **SMBJ13A** (Kandidat) | V_RWM 13 V, V_BR 14,4–15,9 V, I_R 1 µA, **V_C 21,5 V bei I_PP 27,9 A, 10/1000 µs** (Vishay 88392) |

**Schutzspannungsnachweis (offen, O-17):** 21,5 V ist die Klemmspannung unter
den Datenblatt-Prüfbedingungen. Die tatsächliche Spannung hinter der TVS
hängt von Impulsstrom, Exemplartoleranz, Temperatur und Überschwingen durch
Leitungsinduktivität ab und muss gegen alle Bauteile dahinter geprüft
werden: TPS54302 (28 V), LTC7803 (40 V), FETs (40 V), P-FET (−30 V),
Eingangskondensatoren (Kandidat ≥ 35 V), Spannungsteiler und INA240.
SMBJ15A (V_C 24,4 V) nur, wenn dieser Nachweis mit allen Bauteilen gelingt.

**Gatebeschaltung Q101 (Auslegung offen):** Im Normalbetrieb liegt
V_GS ≈ −V_Akku (bis −12,6 V). Die Zenerspannung muss mit ihrer **unteren**
Toleranzgrenze über 12,6 V liegen, damit sie nicht leitet, und mit ihrer
oberen Grenze plus dynamischem Widerstand bei TVS-Klemmung unter |V_GS max|
= 20 V bleiben. Beispiel (nicht ausgewählt): BZT52C15 mit 13,8–15,6 V und
10 kΩ Vorwiderstand → bei 21,5 V ca. 0,6 mA Zenerstrom, |V_GS| ≈ 15,6 V
plus I_Z·R_Z. Zenertyp, Toleranz und Vorwiderstand werden im Schaltplan mit
Datenblatt festgelegt.

**Akkuspannungsmessung (VBAT_SENSE, Auslegung offen):** Kandidat Teiler
120 kΩ / 20 kΩ, 1 %: 12,6 V → 1,80 V (max. 1,83 V), 21,5 V → 3,07 V
(max. 3,12 V). Noch kein vollständiger Eingangsschutz, offen sind:

- Transienten über die TVS-Klemmspannung hinaus → Serienwiderstand und
  Klemmung zum ADC-Pin.
- **Akku angeschlossen, ESP32 ausgeschaltet** (JP101 offen ohne USB, oder
  DevKit nicht gesteckt): Der Teiler liefert dann bis 1,8 V aus 17 kΩ an einen
  unversorgten Pin; Strom über die Schutzdioden in die 3V3-Schiene bis ca.
  76 µA (Schätzung). Abhilfe im Schaltplan auswählen (z. B. Teiler über die
  3V3-Schiene geschaltet oder hochohmiger mit Pufferung).
- Gleiches gilt für VSERVO_SENSE (Servoschiene läuft auch ohne ESP32) und
  den INA240-Ausgang (Verhalten des INA240 ohne Versorgung bei 6,8 V
  Gleichtakt prüfen) – O-21.

**Eingangspfad-Verluste** bei 10,1 A (Worst Case bei 9,0 V, Schätzung):
XT30 0,25 W, Sicherung 15 A ca. 0,57 W (Widerstand nicht belegt), SiRA99DP
0,41 W. Sicherung: 68 % des Nennstroms, mit Temperatur-Derating bei 60 °C
ca. 72 %.

**Sicherung (O-17):** Der berechnete Akkustrom legt die Sicherung nicht fest.
Offen: Zeit-Strom-Kennlinie und Derating der konkreten Type, Einschaltstrom
(Bulk-Kondensatoren beim Einstecken) und Dauer des Überlastfalls,
DC-Spannungsfestigkeit und Abschaltvermögen, Abstimmung mit Akku-Y-Kabel,
XT30, Halter und Leiterbahnen. Die Sicherung schützt den Strompfad; die
betriebliche Überlastreaktion übernimmt die Firmware.

**Weitere Punkte:** Polarität des XT30 am echten Akkukabel prüfen (O-15);
Einsteck-Überschwingen mit Oszilloskop messen.

### 3.10 Kontakte und Kupfer

| Pfad | Strom | Auslegung | Art |
|---|---:|---|---|
| Akkueingang bis Regler | bis 10,1 A berechnet, Sicherungskandidat 15 A | Kupferflächen Außenlagen plus Innenlage, mehrere Vias; Breiten nach IPC-2152 erst mit Kupferstärke des Fertigers und festgelegter Erwärmung (Vorschlag ΔT ≤ 20 K) | (S) |
| Servoschiene bis J102/J103 | bis 11,2 A | Fläche, kein Einzeltrack | (S) |
| Lenkservo-Stecker J102/J103 (Micro-Fit 3.0, 3-polig) | ca. 5,1 A je Kontakt | Molex PS-43045 (Drittspiegel): 8 A UL je Kontakt (1 Kreis); Derating 30 K, 2-polig W-B 8,5 A (18 AWG) / 7 A (20 AWG), 6-polig 6,5 / 5,5 A; für 3-polig kein Molex-Wert, **interpoliert ca. 8 / 6,5 A – Abschätzung**, bis Kontakt, Gegenstecker, Kabel und Temperatur geprüft sind | (Q) / (S) |
| Reserve-Stiftleisten J104/J105 (2,54 mm) | 0,5 A | unkritisch | (S) |

### 3.11 USB und externe Versorgung

Espressif: USB, 5-V-Pin und 3V3-Pin sind **gegenseitig ausschließende**
Versorgungsarten (Q).

Aus dem DevKit-Schaltplan v1.1 (`SCH_ESP32-S3-DevKitC-1_V1.1_20221130.pdf`):

- Jede USB-Buchse speist über eine eigene Schottky-Diode **1N5819HW-7-F**
  (D1 UART-Port, D7 ESP-USB-Port) das interne Netz `VCC_5V`.
- Der 5-V-Header-Pin liegt direkt auf `VCC_5V`, ohne Diode oder Sicherung.
- LDO U2 = **SGM2212-3.3XKC3G/TR**, SOT-223-3: 800 mA, Strombegrenzung
  810 mA min., θJA 117 °C/W, Dropout 240 mV typ. bei 500 mA / 25 °C (SG Micro).

Folgen:

- Die Dioden verhindern, dass externe 5 V in den USB-Host zurückspeisen.
- Umgekehrt **kann USB die Carrier-5-V-Schiene speisen**, wenn der Akku fehlt
  und JP101 gesteckt ist. Das überlastet Diode und USB-Port. Deshalb bleibt
  der Jumper die Rev-1-Lösung.
- LDO-Verlust (S): (5,0 V − 3,3 V) × 0,35 A ≈ 0,6 W → ca. 70 K über Umgebung.
  Mehr als 50 mA Carrier-Last am 3V3-Pin werden nicht freigegeben.

Umsetzung:

- **Jumper JP101** in der Leitung Carrier-5V → DevKit-5V-Pin; gesteckt =
  Akkubetrieb, kein USB-Kabel (Silkscreen „BAT – kein USB"); offen =
  USB-Betrieb.
- Carrier-Netze (5 V, Servo) werden **nie** aus USB gespeist.
- IMU und OLED hängen am 3V3-Pin des DevKit.
- Puffer zwischen ESP32 und 5-V-Domäne unterstützen Ioff (Anschlussplan 3.1).

### 3.12 Verhalten bei Reset und ausgeschaltetem Controller

- Servo- und ESC-Ausgänge: Puffer U201 bei Reset über `ACT_OE_N` hochohmig,
  Pull-downs an Ein- und Ausgängen → kein Pulsausgang (Anschlussplan 3.1).
- ESC-Anschluss: Pin 2 (BEC +) auf der VCU nicht verbunden; ESC-BEC und
  VCU-Regler werden nie zusammengeschaltet.
- Verhalten des ESC ohne Pulse ist nicht bekannt (O-2).
- Servoschiene läuft weiter, solange der Akku über 8,8 V liegt, auch wenn der
  ESP32 nicht läuft; Messeingänge siehe 3.9 / O-21.

## 4. Komponentendaten (Zwischenstand)

| Komponente | Bestätigt | Offen |
|---|---|---|
| ESP32-S3-DevKitC-1-N16R8 v1.1 | Varianten, Pinout J1/J3, PSRAM-Pins, RGB-LED GPIO38, Maße aus DXF, LDO SGM2212-3.3, USB-Dioden 1N5819HW, USB-UART CP2102N (Q) | Nachmessen am Board, Bestellnummer, Datenblatt 1N5819HW |
| FS-iA6B | 4,0–8,4 V, 6 Kanäle, PWM/PPM/i-BUS/S-BUS, 47 × 26,2 × 15 mm (Q) | Stromaufnahme, i-BUS-Pegel und Baudrate, Pinbelegung |
| Adafruit LSM6DSOX (4438) | Vin 3–5 V, I²C pegelgewandelt, 10 k Pull-ups, Adresse 0x6A/0x6B, 25,6 × 17,8 mm (Q) | Pinreihenfolge, Lochabstand |
| Adafruit OLED 0,96" (326) | Vin 3–5 V, ca. 20 mA, 0x3C/0x3D, 29,2 × 26,7 mm, Lochabstand 24 mm (Q) | Pinreihenfolge; konkretes Modul |
| Hobbywing QuicRun Fusion Pro 2300 KV (Auswahl Owner) | 60 A / 200 A, 2–3S LiPo, BEC 6,0/7,4 V 6 A (nicht abschaltbar – rote Ader ziehen und isolieren), LiPo-Abschaltung aus/3,0/3,25/3,5 V je Zelle, „throttle lost protection", XT60, IP67 (Q Hobbywing) | Verhalten bei Signalverlust im Lauf, Default der LiPo-Abschaltung, Pulsgrenzen |
| 2 × Savöx SW-0231MG+ (Auswahl Owner) | 6,0–7,4 V, Blockierstrom 4,8 A @ 6 V / 5,9 A @ 7,4 V, 1000–2000 µs, 50–360 Hz, IP67 (Q Distributor-Datenblatt, Hauptwerte von Savöx bestätigt) | Laststrom im Fahrbetrieb; Drehmoment (Savöx-Seite widersprüchlich: 15 bzw. 20 kg·cm bei 6 V); Messbezugspunkt der Datenblattwerte |

Hinweis I²C: Beide Adafruit-Module bringen eigene Pull-ups mit; die
Gesamtlast wird im Schaltplan berechnet, Carrier-Pull-ups nur
bestückungsoptional.

### 4.1 Bauteilkandidaten Leistungsteil

| Funktion | Kandidat | Kennwerte | LCSC (Bestand 2026-11-14/15) | Stand |
|---|---|---|---|---|
| FET oben + unten | Infineon BSC026N04LS | 40 V, 3,6 mΩ max @ 4,5 V, Q_g 16 nC | C3039672 (17 028) | gültig; R_DS(on) bei INTVCC ≈ 4,8 V prüfen |
| Drossel Servo | 2,2 µH: Coilcraft XAL1010-222ME (I_sat 34 A @ −30 %, DCR max 2,80 mΩ); 3,3 µH: Recherche läuft | – | C5125746 (290) | 3,3 µH offen (O-17) |
| Strom-Shunt LTC7803 | Vishay WSL1020, 3 mΩ, 1 % | 2 W, ESL < 1 nH | offen | O-17 |
| Messshunt Ausgang | 2 mΩ, 1 % | ≥ 1 W | offen | O-17 |
| Strommessverstärker | TI INA240A3 | SBOS662C | offen | O-17 |
| Drossel 5 V | Würth 74439346100 | I_sat 9,7 A (−30 %), DCR max 29,2 mΩ | C2651185 (1 296) | gültig |
| Ausgangs-Bulk Servo | 2 × Panasonic 16SVPG270MX | 270 µF / 16 V, ESR max 10 mΩ, 5,08 A | C2161621 (4 162) | gültig (16 V > 7,81 V) |
| Eingangs-Bulk | ≥ 35 V, Hybrid/Polymer | – | offen | **neu wählen**: EEH-ZK1E471P (25 V) reicht für 3S nicht |
| Eingangs-MLCC | ≥ 35 V X7R 1210 | – | offen | **neu wählen** |
| TVS | SMBJ13A | 3.9 | offen | O-17 |
| Gate-Zener | z. B. 15 V | 3.9 | offen | O-17 |
| Sicherung | Mini-Flachsicherung 15 A | 3.9 | offen | O-17 |

## 5. Grenzwerte Rev 1 (Vorschlag zur Freigabe)

| Netz | Fahrbetrieb | Worst Case | Spannung |
|---|---:|---:|---|
| Akkueingang (3S) | ca. 5–6 A | 10,1 A bei 9,0 V (berechnet), Sicherungskandidat 15 A | 9,0–12,6 V; Antrieb freigegeben ab 10,5 V (Vorschlag) |
| Servoschiene gesamt | 6 A | Auslegungsziel 11 A kontinuierlich, rechnerisch 11,2 A (Nachweis offen) | Kandidat 6,8 V (6,69–6,91 V) |
| je Lenkservo | 2,5 A | ca. 5,1 A (blockiert) | ≥ 6,0 V am Servoanschluss (3.4) |
| je Reserve | 0,5 A | 0,5 A | nur Geräte für die gesamte Schienenspannung (3.2) |
| 5 V | 1,13 A Bilanz | Regler ≥ 2 A | 5,08 V (4,86–5,30 V) |
| 5 V UART-Erweiterung | 0,2 A | – | – |
| 3,3 V (DevKit) | ≤ 0,05 A Carrier-Anteil | – | – |

## 6. Offene Punkte

| Nr. | Punkt | Wer |
|---|---|---|
| O-1 | Vorhandene Firmware (Repository, Core-/Bibliotheksversionen) – nicht bereitgestellt; ohne sie wird neue ESP32-S3-Firmware entwickelt | Owner |
| O-2 | ESC Hobbywing QuicRun Fusion Pro 2300 KV an 3S (Auswahl). Signalverlust zuerst ohne Motor (Signale, Anzeigen), danach kontrollierter Test mit Motor (tatsächliches Stoppen); LiPo-Abschaltung 3,25 V/Zelle | Owner |
| O-3 | Akkueinbruch am Fahrzeug unter Motorlast messen | Owner |
| O-4 | DevKitC-1-N16R8 v1.1 festgelegt; am gekauften Board nachmessen, Bauhöhe bestimmen | Owner |
| O-7 | LTC7803 Rev B gegenlesen; R_DS(on) bei INTVCC ≈ 4,8 V; Kompensation und Durchtrittsfrequenz im Labor | Agent |
| O-8 | Bestellnummern und Bezugsquellen aller Module | Agent |
| O-15 | Polarität des XT30 am Akkukabel prüfen, „+/−" auf Silkscreen | Owner |
| O-16 | WROOM-1-N16R8 nur bis 65 °C: Platzierung fern von Reglern, Temperatur messen | Owner |
| O-17 | Bauteil- und Schutzkoordination 3S: Drossel 2,2 oder 3,3 µH (Sättigung, Temperatur, DCR, Stromgrenze, Regelkreis), Eingangskondensatoren ≥ 35 V, SMBJ13A mit Schutzspannungsnachweis, Gate-Zener mit Toleranz und Vorwiderstand, Sicherung mit Kennlinie, Derating, Einschaltstrom, DC-Spannung, Abschaltvermögen und Abstimmung gegen Kabel, XT30, Halter und Leiterbahnen, Shunts, INA240A3 | Agent |
| O-18 | Gesamtstromüberwachung INA240A3 an 2-mΩ-Ausgangsshunt, GPIO1 (aufgenommen). Offen: Gesamtfehlerbudget, ADC-Filterung, Kalibrierung | Agent |
| O-19 | 3S festgelegt; Servo-Sollwert 6,8 V vorläufig – Festschreibung nach Messung von Schleifenwiderstand und Überschwingen | Owner |
| O-20 | Fehlerreaktion: Antrieb sperren; Zeitgrenzen, Hysterese und Lenkverhalten in der Firmware-Spezifikation festlegen | Owner |
| O-21 | Alle Messeingänge (VBAT, VSERVO, ISERVO) für „Akku an, ESP32 aus" und Transienten auslegen | Agent |

Erledigt: O-5 (DevKit-LDO), O-6 (Lenkservos), O-9 (Projektort), O-14
(ersetzt durch O-17). O-10 bis O-13 stehen im
[GPIO- und Anschlussplan](rev1-pin-und-anschlussplan.md#5-offene-punkte).

## Anhang A – Historische 2S-Rechnung (ersetzt am 2026-11-15)

**Nicht mehr gültig.** Nur zur Nachvollziehbarkeit der Entscheidungen.
Zahlen reproduzierbar mit `python3 rev1_power_calc.py --history-2s`.

| Stand | Inhalt | Warum ersetzt |
|---|---|---|
| 2026-11-14 | 2S 6,0–8,4 V; Servoschiene 6,0 V, Budget 5 A / 8 A Spitze; 4-mΩ-Shunt (9,7 A nutzbar); RUN ein 5,81 / aus 5,32 V; TPS54302-EN ein 5,6 / aus 5,0 V; 10-A-Sicherung; TVS zuerst SMBJ10A, dann SMBJ12A | Servoauswahl SW-0231MG+ (HV, 6,0–7,4 V, 4,8 A Blockierstrom) |
| 2026-11-15 | Sollwert 6,25 V, 3-mΩ-Shunt, 11 A, 15-A-Sicherung; Regelgrenze bei 11 A: 6,60 V Eingang; Akkustrom bis 12,6 A (6,6 V) / 13,8 A (6,0 V) | Spannungsbudget bis zum Servo: 6,25 V reichen beim Blockieren nicht |
| 2026-11-15 | Vorschlag 6,5 V mit Schwellen 7,0 / 7,2 V | 6,5 V am Servoanschluss nur 6,00–6,10 V; 7,0 V − 0,15 V Messfehler = 6,85 V liegt unter der Reglergrenze 6,87 V. Ersetzt durch 3S |

Kernaussagen der 2S-Herleitung, die für 3S nicht mehr gelten:

- Ein 6-V-Abwärtswandler verliert an einem entladenen 2S-Akku seine
  Regelreserve; mit 100 % Tastverhältnis folgt der Ausgang V_in − I·R.
  Das führte zur Wahl des LTC7803 und des TPS54302 (beide 100 %).
- Dropout-Pfad 2S (Schätzung): ca. 32–37 mΩ vom Akku bis zum Reglerausgang.
- Eingangsschutz 2S: SMBJ12A (V_C 19,9 V) unter 25-V-Kondensatoren,
  Gate-Zener 12 V.
