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
| DevKit über D501: Modul-Anforderung ≥ 0,5 A (WROOM-1 DS v1.8 Tab. 6-2) **plus** 50 mA Carrier-Last am 3V3-Pin (IMU, OLED, INA240, Puffer-VCCA, Status-LED, Supervisor); LDO-Eingangsstrom ≈ Ausgangsstrom | 0,55 A | Datenblatt + Festlegung; dieselbe Zahl in 3.11 |
| FS-iA6B Empfänger (über U603) | 0,10 A | (S); Hersteller nennt nur 4,0–8,4 V |
| 4 × SK6812MINI-E, je max. 3 × 14,5 mA + 0,6 mA (Opsco Rev B/2), über U601 | 0,18 A | Datenblatt |
| Buzzer CMT-8540S-SMT-TR (Same Sky): max. 150 mA bei 4 kHz, 50 % Tastverhältnis (extern angesteuert) | 0,15 A | Datenblatt |
| Aktor-Ausgänge: 5 × Pull-up 2,2 kΩ bei Low (2,1 mA), Puffer-VCCB, 3 × TPS2553-Ruhestrom | 0,02 A | Rechnung (S) |
| UART-Erweiterung (Budget, Grenzwert), über U602 | 0,20 A | Festlegung |
| **Summe / Reglerauslegung** | **1,20 A / ≥ 2 A** | gemeinsames Lastbudget für 3.8 und 3.11 (Stand 2026-11-15) |

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
| Servo | ADI **LTC7803** (Controller, externe FETs), MSOP-16-EP, LCSC C1016554 | 4,5–40 V Eingang, 100 % Tastverhältnis („PassThru"), V_FB 0,788–0,812 V, V_SENSE(MAX) 45/50/55 mV, Festfrequenz 340–375–410 kHz, RUN 1,15–1,25 V / 100 mV Hysterese (Rev A, in Rev B unverändert, 3.5a) | Kein PGOOD → Schiene über VSERVO_SENSE und ISERVO_SENSE überwacht; JLC-Bestand nur 25 |
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
| Freigabe | `SERVO_PWR_EN` (GPIO7, aktiv high); ohne aktive Freigabe zieht Q403 RUN auf GND (3.13) | **Reglerabschaltung**, keine Leistungstrennung, siehe unten |

**Rückspeisung und Abschaltung (nicht bestätigt):** Im Forced-Continuous-Modus
kann der Wandler Energie vom Ausgang zum Eingang zurückführen; über den
eingeschalteten Verpol-P-FET kann sie in den Akku gelangen. Bei RUN low sind
beide FETs aus; die Body-Diode des High-Side-FETs sperrt in Richtung
Akku → Schiene. Ob und wohin Rückspeisung eines bewegten Servos dann fließt,
wie lange die Ausgangsladung (ca. 606 µF bei 6,8 V ≈ 14 mJ) ansteht und
welche Entladepfade es gibt, wird anhand der tatsächlichen Schaltung geprüft
und am Prototyp gemessen.

### 3.5a Schaltplanblatt `ServoPower` (Stand 2026-11-15)

Datei `ServoPower.kicad_sch` (A3), einmalig erzeugt mit
`hardware/scripts/bootstrap_servo_power.py`; danach ist die KiCad-Datei
maßgeblich. LTC7803-Angaben aus Datenblatt **Rev B (11/22)**, Analog Devices,
im Repository unter `components/datasheets/ltc7803.pdf` (SHA-256
`3a27428e…f670`, vollständig in `components/sources.csv`).
Rev B ändert gegenüber Rev A laut Revisionshistorie nur AEC-Q100-Angaben;
Pinbelegung und Kennwerte sind gleich (O-7 erledigt). Das LTC7803-Symbol fehlt in KiCad und
liegt projektlokal in `hardware/libraries/symbols/ProjectSymbols.kicad_sym`
(`sym-lib-table` mit `${KIPRJMOD}`), Pinbelegung MSOP-16E laut Rev B:
1 TRACK/SS, 2 SENSE+, 3 SENSE−, 4 VFB, 5 ITH, 6 RUN, 7 FREQ, 8 PLLIN/SPREAD,
9 MODE, 10 INTVCC, 11 EXTVCC, 12 VIN, 13 BG, 14 BOOST, 15 TG, 16 SW,
17 (Exposed Pad) GND.

| Funktion | Bauteil / Beschaltung | Begründung |
|---|---|---|
| Regler | U401 LTC7803EMSE#PBF, Projekt-Footprint `ADI_MSE16_MSOP-16-1EP_ThermalVias` (O-26) | FREQ = GND (375 kHz), PLLIN/SPREAD = GND (fest), MODE = INTVCC (Forced Continuous), EXTVCC = VSERVO_REG (6,8 V > 4,7 V Umschaltschwelle, abs. max. 30 V) |
| FETs | Q401/Q402 Infineon BSC026N04LS, Projekt-Footprint `Infineon_PG-TDSON-8_BSC026N04LS` (O-26) | generisches Symbol S 1–3, G 4, D 5 = Footprint-Pads |
| Drossel | L401 Coilcraft XAL1010-332MED (3,3 µH, **Kandidat**; 2,2 µH Alternative) | siehe Rechnung unten |
| Strom-Shunt | RS401 Vishay WSL10203L000FEA 3 mΩ, Projekt-Footprint `R_Vishay_WSL1020` | Land Pattern nach Vishay (O-26) |
| Sense-Filter | RF401 100 Ω **nur in SENSE+**, CF401 1 nF C0G über SENSE+/SENSE− | Datenblatt Abb. 2a; SENSE− zieht bei 6,8 V ca. 0,7 mA, ein Widerstand dort würde die Schwelle verschieben. Startwerte |
| Boost | D401 Nexperia BAS316 (schnelle PN-Diode, **Kandidat**), C411 **1 µF / 25 V** (korrigiert, vorher 100 nF) | Sperrspannung der Diode ≈ VIN; Schottky-Kandidaten überschreiten heiß den 30-µA-Mindeststrom der Ladepumpe; ADI erlaubt ausdrücklich eine PN-Diode mit kleinem Leckstrom. C_B muss laut Datenblatt ≥ 100 × Eingangskapazität des oberen FETs sein: C_iss max. 3,22 nF → ≥ 0,32 µF; 100 nF war zu klein |
| INTVCC | C412 4,7 µF + C413 1 µF | Datenblatt: ≥ 4,7 µF, zusätzlich 1 µF direkt an den Pins |
| Kompensation | R413 11 kΩ, C418 3,3 nF, C419 100 pF | Startwerte aus Abb. 13 (5 V/10 A), im Labor abstimmen |
| Soft-Start | C414 33 nF | 2,1 ms |
| Rückkopplung | R403 75,0 kΩ / R404 10,0 kΩ, 0,1 % Dünnfilm (Yageo RT0603) | 6,80 V (6,69–6,91 V) |
| Rückkopplungsabgriff | **NT403**: ein Punkt an den Ausgangskondensatoren, **vor** dem Messshunt RS402 | Abfall an RS402 (22 mV bei 11,2 A) wird nicht ausgeregelt, ist im Spannungsbudget enthalten (3.4) |
| Kelvin-Leitungen | **NT401/NT402** (SENSE+/SENSE− an RS401), **NT404/NT405** (INA240 an RS402) | Net-Ties machen die Messleitungen zu eigenen Netzen, die getrennt vom Laststrom als enges Paar ab den Shunt-Pads geführt werden |
| RUN / Freigabe | R405 140 kΩ / R406 20 kΩ (ein 9,60 V, aus 8,80 V), C420 100 nF (1,75 ms); Q403 NTR4003N hält RUN auf GND, solange sein Gate über R414 100 kΩ / R407 220 kΩ aus VBAT_PROT hochgezogen ist; Q404 NTR4003N (Gate an `SERVO_PWR_EN`, R415 100 kΩ Pull-down) zieht dieses Gate nur bei aktiver Freigabe auf GND – **Standard AUS** (3.13) | Reglerabschaltung, keine Leistungstrennung |
| Ausgangskondensatoren | C406/C407 Panasonic 16SVPG270MX, C408–C410 3 × 22 µF Murata | Projekt-Footprint `CP_Panasonic_OSCON_SVPG_C8` nach Panasonic-Land-Pattern (O-26) |
| Eingangskondensatoren | C401–C404 4 × 10 µF/50 V, C405 100 nF am VIN-Pin | Eingangsrippel bis ca. 5,6 A bei 12,6 V |
| Strommessung | RS402 2 mΩ (WSL10202L000FEA), U402 INA240A3DR (Symbol INA240A1D, gleiche Pinbelegung), REF1/REF2 = GND, R412 1 kΩ / C415 1 µF, R416 10 kΩ zum ADC | 3.6 |
| Spannungsmessung | R410 100 kΩ / R411 47 kΩ, C417 100 nF, R417 10 kΩ → VSERVO_SENSE; Klemmung Q405/Q406 ohne +3V3 (O-21, 3.13) | 6,91 V → 2,21 V, 7,81 V → 2,50 V (ADC 0–2,9 V) |
| Messpunkte | TP401 +V_SERVO, TP402 GND, TP403 ISERVO_SENSE | Kupferpads, nicht in der BOM |

Signale zum Controller- und Aktorblatt (`SERVO_PWR_EN`, `VSERVO_SENSE`,
`ISERVO_SENSE`, `+V_SERVO`) sind globale Labels, `+3V3` ist das Netz des
DevKit-LDO; VBAT_PROT kommt hierarchisch vom Blatt `Power`.

**Unabhängiger Datenblattabgleich (Stand 2026-11-15):** Der Vergleich der
Netzliste mit den Generatorvorgaben bestätigt nur, dass die Vorgaben
umgesetzt sind – nicht, dass sie elektrisch richtig sind. Deshalb zusätzlich:

| Bauteil | Abgleich gegen | Ergebnis |
|---|---|---|
| LTC7803 Projektsymbol | Pin-Tabelle „Pin Configuration", MSE-Gehäuse (MSOP-16E), Datenblatt **Rev A und Rev B** | alle 17 Pins stimmen in beiden Revisionen; einzige Gehäusevariante MSE16; Exposed Pad = Pin 17 = GND und muss verlötet werden; Footprint führt das EP als Pad 17 |
| INA240A3D (SOIC-8) | TI SBOS662C Tab. 6-1 | 1 IN−, 2 GND, 3 REF2, **4 NC**, 5 OUT, 6 VS, 7 REF1, 8 IN+. Das KiCad-Symbol nennt Pin 4 „GND"; TI erlaubt „connect to ground or leave floating" – Verbindung nach GND zulässig. VS abs. max. 6 V, versorgt mit 3,3 V |
| BSC026N04LS | Infineon-Datenblatt (Table 1, Table 4) | S1–S3, G4, D5–D8 = generisches Symbol und PG-TDSON-8-Pads 1–5 (Drain-Pads 5–8 und Fahne als Pad 5); V_GS(th) 1,2–2,0 V; R_DS(on) max. 3,6 mΩ bei 4,5 V, 2,6 mΩ bei 10 V |
| BAS316 | Nexperia, 1 July 2022 | V_F max. 715 mV/1 mA, 855 mV/10 mA, 1,0 V/50 mA, 1,25 V/150 mA; I_R 30 nA bei 25 V, 25 °C |

**O-25 – Gatespannung des oberen FETs (Schätzung):**

| Beitrag | Wert | Quelle |
|---|---|---|
| INTVCC min. | 4,95 V − 2 % Lastregelung = 4,85 V | LTC7803 Rev B, EC-Tabelle |
| Diodenabfall BAS316 | 1,0 V bei 50 mA (25 °C), ca. 1,09 V bei −20 °C | Nexperia; Temperaturkoeffizient generisch |
| Bootstrap-Abfall während der Einschaltphase | Q_g max. 22 nC / C_B wirksam 0,6–1,0 µF = 22–37 mV | Infineon / Annahme DC-Bias |
| **V_GS,min oberer FET** | **3,72 V (−20 °C) … 3,83 V (25 °C)** | |
| zum Vergleich mit Schottky (V_F ≈ 0,45 V) | ≈ 4,36 V | |

Bewertung: Der BSC026N04LS garantiert R_DS(on) nur bei V_GS = 4,5 V und
10 V. Bei 3,7–3,8 V ist sein Einschaltwiderstand **nicht garantiert**, nur
über typische Kurven abschätzbar – und auch mit Schottky-Diode bliebe V_GS
unter 4,5 V. Das ist eine Eigenschaft der Kombination LTC7803 (INTVCC 5,15 V
nominal) und dieses FETs, nicht der Diode. Bei 100 % Tastverhältnis hält die
interne Ladepumpe BOOST; welche Gatespannung sich dabei einstellt, nennt
auch Rev B nicht (O-25). Der untere FET erhält INTVCC direkt (≥ 4,85 V) und ist
nicht betroffen. Folge: Für den oberen FET einen Typ suchen, dessen R_DS(on)
bei V_GS ≤ 3,5 V garantiert ist, oder den Wert am Muster messen und mit
Reserve bewerten (O-25).

**Prüfbericht – was die Netzlistenprüfung zeigt:** Der Abgleich der
exportierten Netzliste mit den Generatorvorgaben bestätigt die **Umsetzung**
der Vorgaben, nicht ihre elektrische Richtigkeit. Die elektrische Richtigkeit
stützt sich auf den unabhängigen Datenblattabgleich oben, die Rechnungen
(Schätzungen) und später die Messung am Prototyp.

**Drossel:** 3,3 µH bleibt vorläufig. Der Sense-Rippel von 7,6 mV liegt unter
ADIs empfohlenem Ziel von 10–20 mV bei etwa 50 % Tastverhältnis; das ist kein
Ausschlusskriterium, verlangt aber sorgfältige Filter- und Layoutauslegung
(Kelvin-Führung, RF401/CF401) und eine Messung am Prototyp.

**Auslegung mit Toleranzen** (L ±20 %, f_min 340 kHz, V_out 6,69–6,91 V,
V_in 9,0–12,6 V, R_S +1 % und +100 ppm/K über +60 K, V_SENSE,min 45 mV;
`rev1_power_calc.py`, Funktion `servo_stage_parts`; Schätzung):

| Größe | 2,2 µH (XAL1010-222ME) | **3,3 µH (XAL1010-332MED)** |
|---|---|---|
| Rippel nominal / ungünstigst | 3,79 / 5,24 A | 2,53 / 3,50 A |
| nutzbarer Ausgangsstrom min. | 12,14 A (Reserve 0,9 A zu 11,2 A) | **13,01 A (Reserve 1,8 A)** |
| Spitzenstromgrenze max. | 18,5 A | 18,5 A |
| I_sat (−30 %, 25 °C) | 34,0 A | 27,4 A; Wert bei 125 °C nicht veröffentlicht |
| Sense-Rippel (Ziel 10–20 mV) | 11,4 mV | **7,6 mV – darunter** (Störabstand im Labor prüfen) |
| Kupferverlust (DCR max., heiß) | 0,46 W | 0,67 W; Kernverlust nicht enthalten |
| FET oben, Leitung (+ Schalten grob) | 0,49 W (+0,12) bei 9 V; 0,35 W (+0,16) bei 12,6 V | gleich |
| FET unten, Leitung | 0,15 W (9 V) / 0,29 W (12,6 V) | gleich |
| RS401 | 0,38 W bei 11,2 A, 1,03 W an der Stromgrenze (2 W bei 70 °C) | gleich |

### 3.5b Footprints nach Hersteller-Land-Pattern (O-26, Stand 2026-11-15)

Die KiCad-Standardfootprints weichen bei vier Bauteilen von den
Herstellerangaben ab. Projekt-Footprints in
`hardware/libraries/footprints/ProjectFootprints.pretty` (`fp-lib-table` mit
`${KIPRJMOD}`), erzeugt mit `hardware/scripts/make_project_footprints.py`;
Grafik und 3D-Modell aus KiCad 10.0.7, Pads nach Hersteller, Courtyard = KiCad
∪ Pads + 0,25 mm.

| Footprint | Quelle | Abweichung KiCad → Hersteller | Ergebnis |
|---|---|---|---|
| `R_Vishay_WSL1020` (RS401, RS402) | Vishay Dok. 30183 (27.03.2024), Solder Pad Dimensions | Padmittenabstand −0,25 mm, Spalt −0,40 mm | Pads 1,00 × 5,65 mm bei ±1,25 mm |
| `CP_Panasonic_OSCON_SVPG_C8` (C406, C407) | Panasonic AAB8000COL10 (31.10.2025), Gehäuse C8 | Padabstand −0,2 mm | Pads 3,5 × 1,6 mm bei ±2,8 mm; Pad 1 = Anode, Polaritätsmarke übernommen |
| `ADI_MSE16_MSOP-16-1EP_ThermalVias` (U401) | LTC7803 Rev B S. 36, MSE16 05-08-1667 Rev F | Pads +0,56 mm länger, Reihenabstand 0,35–0,6 mm enger | Pads 0,305 × 0,889 mm, Reihenspalt 3,325 mm (Mitte des Bereichs 3,20–3,45); EP 1,651 × 2,845 mm unverändert (identisch) |
| `Infineon_PG-TDSON-8_BSC026N04LS` (Q401, Q402) | BSC026N04LS Rev 2.3, Fig. 2 Outline Boardpads | Abstand Pin-Reihe zu Drain 0,65 statt 1,27 mm | Pins 0,5 × 0,925 mm; Drain 4,41 mm hoch mit vier Fingern 0,6 × 0,8 mm. **Pastenfenster des Drain-Pads (2 × 2 je 1,5 mm) sind eine Näherung** – vor Schablonenbestellung prüfen (O-27) |

Prüfung: ERC 0 Befunde; Netzliste unverändert (nur sieben Footprint-Felder
geändert); `scripts/kit verify` meldet `pin_pad_mapping` und
`library_references` ohne Befund; Sichtprüfung der F.Cu/F.Paste/F.CrtYd-
Ansicht jedes Footprints. Net-Ties (NT401–NT405) markieren nur die
Kelvin-Abgriffe im Schaltplan; die eigentliche Kelvin-Führung (getrenntes,
enges Leitungspaar ab den inneren Padkanten der Shunts) entsteht erst im
Layout und ist dort zu prüfen.

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

### 3.8 Dimensionierung TPS54302 (3S) – Schaltplanblatt `LogicPower`

Stand 2026-11-15. Grundlage TPS54302-Datenblatt SLVSDG6C (03/2026),
Abschnitt 7.2. Schaltplan: `LogicPower.kicad_sch` (Bootstrap
`hardware/scripts/bootstrap_logic_power.py`, danach KiCad-Datei maßgeblich).
Alle Werte sind Schätzungen; die Regelschleife ist nicht gemessen.

| Größe | Wahl | Rechnung / Begründung |
|---|---|---|
| Regler | U301 TPS54302DDCR (C311983), Footprint TSOT-23-6 | Pinbelegung GND 1, SW 2, VIN 3, FB 4, EN 5, BOOT 6 (Tab. 4-1) = KiCad-Symbol |
| Drossel | L301 10 µH, Würth 74439346100 (C2651185) | ΔI_L worst bei 12,6 V 1,3 A, I_pk 2,7 A bei 2 A |
| Ausgangsspannung | R302 100 kΩ / **R303 13,7 kΩ** (vorher 13,3 kΩ), 1 % | 0,596 V × (1 + 100/13,7) = 4,95 V; mit V_REF ±2,5 % und 1 %: **4,74–5,16 V** (0,1 %: 4,81–5,08 V). 13,3 kΩ hätte 4,86–5,30 V ergeben |
| Ausgangskondensatoren | **3 × 22 µF / 25 V X7R 1210** (Murata GRM32ER71E226KE15L, C21397), C304/C305/C307 | siehe Kapazitätsabschätzung unten; TI-Referenz nutzt 2 × 22 µF |
| Vorhaltekondensator | C306 75 pF C0G (Yageo CC0603JRNPO9BN750, C282074) | Gl. 16 für 30–56 µF wirksam: 46–86 pF; 75 pF liegt darin |
| Messwiderstand | R301 49,9 Ω zwischen +5V und Teiler | Einspeisepunkt für die Messung der Regelschleife (TI-Referenz R1) |
| Eingangskondensatoren | C301 10 µF / 50 V X7R 1210 + C302 100 nF / 50 V 0603 | ≥ 35 V für 3S und TVS-Klemmung |
| BOOT | C303 100 nF / 50 V X7R (Yageo CC0603KRX7R9BB104, C14663) | Datenblatt 7.2.3.2 |
| Unterspannung (EN) | R304 69,8 kΩ / R305 11,5 kΩ | ein 8,65 V, aus 8,04 V; EN bei 21,5 V ≈ 3,0 V < 7 V abs. max. |
| Hierarchie | VBAT_PROT als Eingang vom Blatt `Power`; +5V und GND global | PWR_FLAG an VBAT_PROT und +5V, weil beide nur über passive Bauteile gespeist werden |

**Verbraucherverträglichkeit +5V** (statisch 4,74–5,16 V; Transienten siehe
unten). Bewertet wird gegen den **Betriebsbereich** laut Datenblatt, nicht
gegen absolute Grenzwerte.

| Verbraucher | Betriebsbereich (Quelle) | Bewertung |
|---|---|---|
| DevKit 5-V-Pin → LDO SGM2212-3.3 | Eingang 2,7–20 V; Dropout 240 mV typ. bei 500 mA (SG Micro) | erfüllt |
| Empfänger FS-iA6B | 4,0–8,4 V (FlySky-Anleitung 2024) | erfüllt; bestimmt die harte Untergrenze 4,0 V |
| LED **Opsco SK6812MINI-E** (SK6812MINI-E-012, Spec Rev B/2 2025-11-22, LCSC-Kopie; LCSC C5149201) | **3,7 / 5,0 / 5,5 V** min/typ/max (§9), absolut 3,7–5,5 V (§7); V_IH 0,65 × V_DD; 800 kbit/s | erfüllt, auch für Transienten bis 5,5 V. Rückwärts montierte LED (Loch in der LED-Platine). Pinbelegung hat sich zwischen Rev 04 und Rev B/2 geändert – Footprint gegen B/2 prüfen. Worldsemi-Typen verworfen: nur absolute Grenze 5,3 V, kein Betriebsbereich |
| Buzzer **Same Sky CMT-8540S-SMT-TR** (Rev 1.04, 2024-09-11) | **extern angesteuerter** magnetischer Wandler; Nennspannung 5,0 V, Betrieb 1,0–6,0 V; max. 150 mA **bei 4 kHz und 50 % Tastverhältnis** (Messbedingung, kein allgemeiner Spitzenstrom); Spule 10–16 Ω | Spannungsbereich erfüllt. Ansteuerung nur per LEDC mit 4 kHz/50 %; **kein dauerhaftes Einschalten** per GPIO (Firmware-Regel, Gate-Pull-down). Freilaufdiode nötig. MOSFET und Freilaufpfad für den tatsächlichen Schaltstrom auslegen: Spitzenstrom am Ende jeder Einschaltphase und Fehlerfall Dauer-Ein (bis 5,16 V / 10 Ω ≈ 0,52 A) – Werte im Schaltplanschritt. LCSC-Bestand 0, bei DigiKey/Mouser/Arrow lieferbar |
| SN74LVC8T245 / LVC1T45 (V_CCB) | 1,65–5,5 V (TI) | erfüllt |
| UART-Erweiterung J112 | – | **verbindliches Budget:** +5V_EXT max. 0,2 A dauernd; 4,74–5,16 V statisch; **dynamisches Fenster 4,56–5,34 V** (berechnete Lastsprünge bis 1 A, siehe Reglerrechnung) innerhalb der Auslegungsgrenzen 4,5–5,5 V; Signale 3,3 V, RX nicht 5-V-tolerant. Angeschlossene Geräte müssen diesen Bereich vertragen. Schutzelement: TPS2553 (U602), Grenze 0,23–0,30 A (Anschlussplan 8) |

Grenzen für die Transientenbewertung: **Untergrenze 4,5 V** (Auslegungsziel
mit Reserve über den 4,0 V des Empfängers), **Obergrenze 5,5 V** (LED-
Betriebsmaximum und LVC8T245).

**Wirksame Ausgangskapazität (Stand 2026-11-15, Schätzung):**

Bauteil: 3 × **Murata GRM32ER71E226KE15L** (22 µF, 25 V, X7R, 1210, ±10 %;
LCSC C21397). Teilspezifische DC-Bias-Kennlinie von Murata (SimSurfing,
„25.0 degC, AC0.5Vrms", typische Werte, aus den Diagrammkoordinaten gelesen):
−17,8 % bei 4,74 V, −20,1 % bei 5,0 V, −21,5 % bei 5,16 V.

| Einfluss | Ansatz | Quelle / Art |
|---|---|---|
| Anfangstoleranz | −10 % | Murata, garantiert |
| DC-Bias bei 5,16 V | −21,5 % | Murata, **typisch**, teilspezifisch, bei 25 °C |
| Temperatur | −15 % (X7R-Klassengrenze) | Klassengrenze; die Teilekurve bei 0 V zeigt −7 % bei −20 °C, das Zusammenspiel mit DC-Bias ist nicht veröffentlicht – deshalb nur die Klassengrenze, nicht beides |
| Alterung | −5 % (2 Dekaden nach Bezugszeit) | **generisch** für X7R, nicht teilspezifisch (Murata-Daten nur mit Login) |
| **Ergebnis** | **≈ 37,7 µF** (3 Stück), typisch 52,7 µF bei 25 °C, 5 V | Schätzung |

Die Mindestkapazität beruht auf einem **typischen** DC-Bias-Wert und
generischer Alterung; sie ist **kein garantierter Mindestwert**. C307
verbessert die Reserve, sichert sie aber nicht nachweislich ab. Nachweis
durch Messung der Regelschleife (über R301) und der Lastsprünge am Prototyp.

**Reglerrechnung** (TPS54302 SLVSDG6C, Gl. 11, 12, 14, 16; f_SW,min 290 kHz;
L bis 12 µH; Rechenweg `rev1_power_calc.py`, Funktion `logic_5v_capacitance`):

| Kriterium | Anforderung | Ergebnis mit 37,7 µF (typ. 52,7 µF) |
|---|---|---|
| Regelschleife, Gl. 14 (f_o < 40 kHz) | ≥ 26,9 µF | f_o 27,4 kHz (19,6 kHz) – rechnerisches Kriterium unter den dokumentierten Kapazitätsannahmen erfüllt; Regelkreisstabilität nicht gemessen |
| Vorhaltekondensator, Gl. 16 | 1/(2π f_o R2) | 58 pF (81 pF); **75 pF** liegt im Bereich; Phasenreserve messen |
| Rippel, Gl. 12 (30 mV) | ≥ 18,8 µF | 15 mV |
| **Lastzunahme** 0,6 A / 1,0 A (Gl. 11) | Minimum ≥ 4,5 V | 4,63 V / 4,56 V – bedingt erfüllt |
| **Lastabwurf** 0,6 A / 1,0 A (Gl. 11) | Maximum ≤ 5,5 V | 5,27 V / 5,34 V – bedingt erfüllt; Energiebilanz der Drossel nur 11 / 31 mV |
| Buzzer-Lastwechsel bei 4 kHz (bis 0,15 A unter Datenblattbedingung) | – | ca. 27 mV je Wechsel |

Bedingungen: Gl. 11 ist TIs Abschätzung „Ausgangskondensator überbrückt
zwei Schaltperioden" und gilt für Lastanstiege schneller als ca. 7 µs
(ungünstigster Fall); langsamere Anstiege sind günstiger. Die
Laständerungen sind Szenarien (0,6 A ≈ WLAN-Sendespitze plus alle LEDs plus
Buzzer; 1,0 A mit Reserve für die UART-Erweiterung). Die Rechnung ersetzt
keine Messung von Über- und Unterschwingen.

### 3.9 Eingangsschutz und Messeingänge (3S)

Pfad: **J101 XT30 → F101 Sicherung → Q101 Verpol-P-FET → D101 TVS →
Eingangs-Bulk → Regler**.

**Schaltplan (Stand 2026-11-15):** Blatt `Power` (`Power.kicad_sch`), einmalig
erzeugt mit `hardware/scripts/bootstrap_power_input.py`; ab jetzt ist die
KiCad-Datei maßgeblich. Netze: VBAT_IN (J101.2, F101, TP101), VBAT_FUSED
(F101 → Q101 Drain), VBAT_PROT (Q101 Source, D101, D102, C101, C102, TP102),
Q101_GATE (Q101 Gate, R101 10k nach GND, D102 15 V), GND. Zusätzlich C102
10 µF/50 V am Schutzknoten. ERC 0, Netzliste gegen den Entwurf geprüft,
Pin/Pad-Zuordnung PASS. Offen: PCB aus dem Schaltplan aktualisieren
(Abgleich), Bauteilakten, R101/D102-Auslegung (O-17), XT30-Polarität (O-15).

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
- **Akku angeschlossen, ESP32 unversorgt:** umgesetzt mit Klemmung und
  Serienwiderstand, siehe 3.13 (O-21).

**Einschaltstrom (offener Nachweis):** Q101 ist **keine kontrollierte
Einschaltstrombegrenzung**. Beim Einstecken lädt der Akku C101, C102 und die
Eingangskondensatoren beider Regler (C301, C302, Servostufe) über Kabel,
XT30, Sicherung und den bereits leitenden P-FET. Spitzenstrom, Funkenbildung
am XT30, Belastung von Q101 (SOA) und Sicherung (I²t) sind zu rechnen und am
Prototyp zu messen.

**Zener D102 (MMSZ5245BT1G, onsemi Rev. 17):** V_Z 14,25–15,75 V bei
I_ZT 8,5 mA, Z_ZK 600 Ω bei 0,25 mA, Leckstrom max. 0,1 µA bei 11 V. Bei
12,6 V Akkuspannung liegt V_GS unter V_Z,min; der Leckstrom bei 12,6 V ist
nicht spezifiziert (Prüfspannung 11 V). Bei TVS-Klemmung (21,5 V) fließen über
R101 10 kΩ ca. 0,6 mA; V_Z bei diesem Strom ist nicht garantiert (nur
typische Kurven anderer Spannungen). Nachweis |V_GS| < 20 V am Muster.

**Eingangspfad-Verluste** bei 10,1 A (Worst Case bei 9,0 V, Schätzung):
XT30 0,25 W, Sicherung 15 A ca. 0,47 W (4,58 mΩ kalt, Littelfuse 0297015 [Spiegel]),
SiRA99DP 0,41 W. Sicherung: 68 % des Nennstroms, mit Temperatur-Derating bei 60 °C
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

Folgen und Umsetzung (geändert 2026-11-15, Blatt `Controller`):

**Eigene Erweiterung, nicht von Espressif vorgesehen.** Espressif nennt USB-,
5-V-Pin- und 3,3-V-Pin-Versorgung weiterhin gegenseitig ausschließend. Der
DevKit-Schaltplan v1.1 (Blatt 1 vom 13.04.2022, Blatt 2 vom 30.11.2022)
zeigt: VBUS (UART-Port) → D1 1N5819HW-7-F → `VCC_5V`, VBUSB (ESP-USB-Port) →
D7 1N5819HW-7-F → `VCC_5V`, 5-V-Stiftleistenpin direkt auf `VCC_5V`, LDO
U2 SGM2212-3.3 aus `VCC_5V`. Mit **D501** (Carrier +5V → 5-V-Pin) läuft jede
der drei Quellen über eine eigene Diode in `VCC_5V`: ein Dioden-ODER.
Rückströme zwischen den Quellen sind auf die Sperrströme der Dioden begrenzt.
Das gilt **nur für die Leistungsversorgung**: Über D501 erreicht USB-Strom
die Carrier-Schiene +5V nur als Sperrstrom (PMEG4010CEH typ. 0,8 µA bei 5 V
und 25 °C, ca. 30 µA bei 65 °C nach Fig. 2; kein Maximalwert bei 5 V). Rückspeisung über Signalleitungen behandelt O-21 (3.13).

Datengrundlage: PMEG4010CEH Nexperia Product data sheet v.3 (12.10.2023,
`components/datasheets/PMEG4010CEH.pdf`, SHA-256 in `components/sources.csv`):
V_F max. 490 mV bei 0,5 A, 520 mV bei 0,7 A, 570 mV bei 1 A – **nur bei 25 °C
und gepulst** (t_p ≤ 300 µs, δ ≤ 0,02), also kein garantierter Wert für alle
Betriebsbedingungen. Fig. 1 (typisch) zeigt bei 0,5 A ca. +0,1 V von 25 °C nach
−40 °C (≈ 1,7 mV/K). I_R typ. 0,8 µA bei 5 V/25 °C, max. 50 µA bei 40 V/25 °C;
Fig. 2 typ. ca. 30 µA bei 5 V und 65 °C. R_th(j-a) 330 K/W (Standard-Pad),
150 K/W (1 cm² Kathodenfläche), T_j max. 150 °C. SGM2212-3.3 Rev A.2 (07/2023, LCSC-Kopie):
V_OUT 3,251–3,349 V, Dropout max. 380 mV bei 500 mA und 610 mV bei 800 mA
über −40…125 °C. ESP32-S3-WROOM-1 DS v1.8: VDD 3,0–3,6 V, Versorgung muss
≥ 0,5 A liefern können, Spitzen 355 mA (Wi-Fi TX).

**Rechnung (Schätzung, `rev1_power_calc.py --controller`):**

| Größe | Wert |
|---|---|
| Auslegungslast am LDO | 0,55 A – dieselbe Zeile wie in der 5-V-Bilanz (3.2) |
| LDO-Dropout bei 0,55 A | 418 mV (linear zwischen den Max-Werten interpoliert) |
| V_F D501 | 498 mV max. bei 25 °C (gepulst); bei −20 °C ca. 588 mV (2 mV/K angenommen, Fig. 1 typ. ≈ 1,7 mV/K; nicht spezifiziert) |
| +5V minimal | 4,74 V statisch − 0,10 V Lastsprung-Reserve |
| Sockel + Leitungen | 50 mV angenommen |
| **LDO-Eingang minimal (Akku allein)** | **4,00 V** |
| benötigt für Regelung (3,349 V + Dropout) | 3,77 V → Reserve 0,24 V |
| benötigt für VDD ≥ 3,0 V | 3,42 V |
| D501-Verlust Mittel / Dauer 0,55 A | 90 mW / 274 mW |
| T_j bei 65 °C Umgebung, 1 cm² Kathodenkupfer | 78 °C / 106 °C |
| T_j bei Standard-Pad und 0,55 A Dauer | 155 °C – **nicht zulässig** → Layoutvorgabe ≥ 1 cm² Kathodenkupfer |

**Betriebsfälle:**

| Fall | Verhalten | Nachweis |
|---|---|---|
| Akku allein | D501 leitet, LDO-Eingang ≥ 4,00 V (Schätzung) | Rechnung oben, Messung am Muster |
| USB allein | DevKit wie von Espressif vorgesehen; D501 gesperrt (V_R ≈ 4,5–5 V), Sperrstrom in die stromlose +5V-Schiene (µA) | V_F der DevKit-Diode 1N5819HW nicht geprüft (Datenblatt fehlt) |
| Beide | höhere Quelle versorgt, sonst Aufteilung über die Dioden; kein Querstrom außer Sperrströmen | Messung V_CC_5V und Rückstrom in VBUS |
| USB stecken bei laufendem Akku | DevKit-Diode leitet nur, wenn USB höher ist | Messung |
| USB ziehen bei laufendem Akku | erwartet: Last wechselt auf D501; ob ohne Unterbrechung, **ist zu prüfen** | Messung Einbruch V_CC_5V |
| Akku stecken bei laufendem USB | +5V steigt mit dem TPS54302-Softstart; erwartet ist eine Übernahme durch D501 – Stoßfreiheit **ist zu prüfen** | Messung |
| Akku ziehen bei laufendem USB | V_CC_5V fällt auf USB-Pfad zurück; Reset nur, wenn USB-Pfad < 3,77 V | Messung, 1N5819HW-Daten offen (O-28) |
| DevKit unter Spannung stecken/ziehen | **nicht zulässig** (keine definierte Kontaktfolge der Buchsenleisten) | Betriebsanweisung |

- LDO-Verlust (S): (5,0 V − 3,3 V) × 0,35 A ≈ 0,6 W → ca. 70 K über Umgebung.
  Mehr als 50 mA Carrier-Last am 3V3-Pin werden nicht freigegeben.
- IMU, OLED, INA240 und die VCCA-Seite der Puffer hängen an +3V3 (DevKit-LDO).
  Aufstellung des Carrier-Anteils (Stand 2026-11-15, **Schätzung**, messen):

  | Verbraucher an +3V3 | Strom |
  |---|---|
  | OLED Adafruit 326 | ca. 20 mA typ. (Adafruit, abhängig von leuchtenden Pixeln), angesetzt **30 mA** |
  | IMU Adafruit 4438 | LSM6DSOX 0,55 mA typ. (Accel + Gyro High-Performance, ST DS12814 Rev 4, Typwert nicht garantiert) + AP2112K + Modul-LED ≈ 0,2 mA, angesetzt **1,5 mA** |
  | I²C-Pull-ups bei Low | bis 1,3 mA (Anschlussplan 9.4), angesetzt 0,7 mA Mittel |
  | INA240A3 | 2,6 mA max. (SBOS662C) |
  | Status-LED D502 | 1,3 mA |
  | Pull-ups R501/R502/R617, Teiler-Pull-ups R201–R205, R604, R803 | zusammen ≤ 1,5 mA (je 0,33 mA bzw. 33 µA, nur bei Low) |
  | U201/U202/U203/U204/U504/U505/U506 statisch | < 0,1 mA (TPS3808 ≤ 5 µA, LVC1G74/1G32 je ≤ 10 µA; R517 33 µA bei Low) |
  | **Summe** | **≈ 38 mA** von 50 mA Zuteilung → Reserve ca. 12 mA |

- Ideal-Diode LM66100 verworfen: Mit CE an VOUT schaltet sie erst ab, wenn
  VOUT um V_OFF (0–80 mV) über VIN liegt; bis dahin fließt Rückstrom bis
  I_RCB 0,5–1 A (TI SLVSEZ8A, 8.3.2). Die TI-ODER-Schaltung braucht Zugriff auf
  beide Quellen, VBUS liegt aber im DevKit.

### 3.12 Verhalten bei Reset und ausgeschaltetem Controller

- Servo- und ESC-Ausgänge: Puffer U201 bei Reset über `ACT_OE_N` hochohmig,
  Pull-downs an Ein- und Ausgängen → kein Pulsausgang (Anschlussplan 3.1).
- ESC-Anschluss: Pin 2 (BEC +) auf der VCU nicht verbunden; ESC-BEC und
  VCU-Regler werden nie zusammengeschaltet.
- Verhalten des ESC ohne Pulse ist nicht bekannt (O-2).
- Servoschiene: **Standard AUS** – sie läuft nur, solange der ESP32 sie über
  `SERVO_PWR_EN` aktiv freigibt (3.13).

### 3.13 Schaltplanblatt `Controller` und Standardzustände (Stand 2026-11-15)

Datei `Controller.kicad_sch` (A3), einmalig erzeugt mit
`hardware/scripts/bootstrap_controller.py`; Sockel-Symbol und -Footprint mit
`hardware/scripts/make_devkit_socket.py`.

| Funktion | Umsetzung |
|---|---|
| DevKit-Sockel U501 | Original ESP32-S3-DevKitC-1-N16R8 v1.1; zwei 1×22-Buchsenleisten 2,54 mm, Reihenabstand 22,86 mm; Pads 1–22 = J1, 23–44 = J3. Silkscreen: Pfeil und „J1-1"/„J3-1" an Pin 1 beider Reihen (Antennenende), „ANT", „USB" mit Pfeil, DevKit-Umriss; Antennen-Sperrfläche auf allen Kupferlagen. x-Lage des Antennenüberstands mittig angenommen (O-4) |
| 5 V | D501 +5V → 5-V-Pin (Dioden-ODER, 3.11); ≥ 1 cm² Kathodenkupfer; TP503 |
| 3,3 V | +3V3 nur aus dem DevKit-LDO; C501 10 µF + C502 100 nF am Sockel; TP502, TP504 (GND) |
| Freigabetaster | SW501 direkt nach GND, R502 10 kΩ Pull-up; **kein Kondensator am Pin** (O-21) – Entprellung in der Firmware |
| Status-LED | GPIO11 → R504 1 kΩ → D502 (AlGaInP, Typ offen, O-28), ca. 1,3 mA (Schätzung) |
| Akkumessung | Q505 (NTR4171P) schaltet den Teiler R505 120 kΩ / R506 20 kΩ nur bei P3V3_OK an VBAT_PROT; C504 1 nF, D506 BAT54 nach +3V3, R507 10 kΩ (O-21) |
| 3,3-V-Überwachung | U504 TLV809ED29 (2,93 V, Freigabe 33–67 ms) → `P3V3_OK`; R510 100k Pull-down |
| Reserve | GPIO18 nur auf TP501 (Eingang) |
| Nicht verbunden | RST, GPIO0/3/45/46 (Strapping), 19/20 (USB), 43/44 (UART0), 35–38 – No-Connect-Marken (Prüfbericht im Anschlussplan) |

#### Standardstellung der Servoversorgung: AUS (vom Owner übernommen)

Die Schiene läuft nur, solange der ESP32 `SERVO_PWR_EN` (GPIO7) aktiv auf
high treibt. GPIO7 hat bei und nach Reset weder Pull-up noch Pull-down noch
Eingangsfreigabe (ESP32-S3 DS v2.2, Tab. 2-1) und nur einen Low-Glitch beim
Einschalten (Tab. 2-2). Die Beschaltung liegt auf `ServoPower`:

- R414 100 kΩ (von VBAT_PROT) / R407 220 kΩ am Gate von **Q403**, Q403 zieht
  RUN auf GND.
- **Q404** zieht das Q403-Gate nur bei GPIO7 high auf GND; R415 100 kΩ hält
  Q404 sonst aus.
- Q403 und Q404 sind **NTR4003N** (onsemi NTR4003N/D Rev 6, 01/2026):
  V_GS(th) 0,8–1,4 V bei 250 µA, R_DS(on) ≤ 2,0 Ω bei V_GS 2,5 V / ≤ 1,5 Ω bei
  4,0 V (10 mA, 25 °C), I_DSS ≤ 1 µA bei 30 V/25 °C, V_GS ±20 V. Ersetzt
  2N7002L/BSS138, deren R_DS(on) erst ab 4,5–5 V garantiert ist.
- **C420 100 nF an RUN** (neu): verzögert RUN mit 17,5 kΩ × 100 nF = 1,75 ms.

**Statische Rechnung** (Widerstände ±2 % = 1 % + 100 ppm/K über 85 K;
`rev1_power_calc.py --controller`; Schätzung):

| Zustand | Bedingung | Ergebnis |
|---|---|---|
| AUS | Q403 braucht V_GS ≥ 4,0 V für die R_DS(on)-Angabe | V_GS min. 6,18 V bei 9,2 V (unterste RUN-Einschaltschwelle), 8,48 V bei 12,6 V; abzüglich 1 µA Leckstrom (Q404 I_DSS + Q403 I_GSS) über 69 kΩ |
| AUS | V_GS max. < 20 V | 14,9 V bei 21,5 V TVS-Klemmung |
| AUS | RUN muss unter der Schwelle bleiben | RUN ≤ 69 µA × 1,5 Ω (×1,6 heiß, Fig. 5 typ.) ≈ 0,2 mV |
| EIN | GPIO7 V_OH min. 0,8 × VDD = 0,8 × 3,251 V = 2,60 V ≥ 2,5 V (Spezifikationspunkt) | Q404 R_DS(on) ≤ 2,0 Ω (25 °C), heiß ca. 3,2 Ω (typ. Faktor 1,6) |
| EIN | Strom durch R414 | max. 219 µA (21,5 V, R414 −2 %) → Q403-Gate ≤ 0,7 mV ≪ V_GS(th) min. 0,8 V (heiß ca. 0,6 V, −3,4 mV/K typ.) |
| EIN | Leckstrom Q403 verschiebt RUN | 1 µA (25 °C max.) × 17,5 kΩ = 17,5 mV (≈ 1,5 % der Schwelle); heiß nur typ. angegeben (20 nA bei 125 °C, Fig. 6) |
| EIN | GPIO7 Hi-Z-Leckstrom 50 nA × R415 | 5 mV → Q404 sicher aus, wenn nicht getrieben |

Q404 ist damit nicht „voll durchgeschaltet" nachgewiesen, sondern: Bei
minimalem GPIO-High nimmt Q404 den erforderlichen Strom (≤ 219 µA) mit
≤ 0,7 mV Spannungsabfall auf und sperrt Q403 sicher. Annahme: R_DS(on) sinkt
mit steigender Gatespannung (2,60 V > 2,5 V Prüfpunkt).

**Einschalttransienten (getrennt, Entwurfsannahme bis zur Messung):**

- Akku einstecken: Das Q403-Gate folgt VBAT mit τ ≈ 69 kΩ × 87 pF ≈ 6 µs
  (C_iss Q403 42 pF + C_oss Q404 40 pF max. + 5 pF Leitung). RUN folgt mit
  1,75 ms (C420). Q403 leitet ab V_GS ≈ 1,4 V, also nach wenigen µs. RUN
  erreicht in dieser Zeit nur wenige mV. „Inhibit ist rechtzeitig aktiv" ist
  damit **plausibel, aber nicht nachgewiesen** – Messung an RUN und +V_SERVO
  beim Einstecken mit Oszilloskop (O-29).
- ESP32-Hochlauf: GPIO7 hochohmig oder Low-Glitch → Q404 aus → AUS.
- Freigabe entziehen: Q404 aus, Q403-Gate steigt mit ca. 6 µs, C420 wird über
  Q403 entladen.
- Akku unter 8,8 V: Abschaltung über den RUN-Teiler (mit 1,75 ms Verzögerung).

| Zustand | ACT_OE_N / Puffer U201 | Servoschiene | Buzzer | Taster |
|---|---|---|---|---|
| Akku eingesteckt, Hochlauf | +3V3 noch aus: VCCA = 0 → Ports hochohmig (VCC-Isolation), B-Pull-downs low | AUS (siehe oben) | aus (Gate-Pull-down) | – |
| ESP32 in Reset / Boot | R501 hält OE high → hochohmig; Low-Glitch von GPIO2 bei Eingängen low = kein Puls | AUS | aus | high |
| DevKit fehlt | VCCA = 0 → hochohmig | AUS (R415) | aus | – |
| Betrieb | Firmware gibt erst die Schiene, dann die Puffer frei | EIN, solange GPIO7 high | – | – |
| ESP32 hängt ohne Reset | Zustand eingefroren | bleibt EIN → Watchdog in der Firmware verpflichtend | – | – |
| Akku unter 8,8 V | – | AUS durch RUN-Teiler | – | – |

#### O-21: Eingänge bei ausgeschaltetem oder fehlendem DevKit (überarbeitet nach Review)

Grundlage: ESP32-S3 DS v2.2, Tab. 5-4: V_IH max. = VDD + 0,3 V. Einen
zulässigen Injektionsstrom nennt das Datenblatt nicht. **Ein
Serienwiderstand gilt deshalb nicht als Schutz.** Auslegungsregel: Kein
ESP32-Pin darf über **VDD + 0,3 V** liegen – in Betrieb, bei Hochlauf, beim
Abschalten und bei fehlendem +3V3. Die 10-kΩ-Serienwiderstände bleiben, werden
aber nicht als Nachweis gezählt.

**Gemeinsames Signal `P3V3_OK`** (U504 TLV809ED29, TI SLVSES2J):
- high nur, solange +3V3 ≥ V_IT+ (2,87–2,99 V + 0,9–1,5 % Hysterese) –
  frühestens 33 ms (variant D) nach Erreichen;
- low innerhalb von 50 µs, sobald +3V3 unter 2,87–2,99 V fällt;
- definiert low ab VDD 0,7 V, darunter und ohne DevKit über R510 auf GND.

| Eingang | Quelle | Maßnahme | Nachweis (Schätzung, `rev1_power_calc.py --controller`) |
|---|---|---|---|
| VBAT_SENSE (GPIO4) | Teiler am Akku | Q505 NTR4171P (−30 V, V_GS ±12 V, I_DSS ≤ 1 µA) schaltet den Teiler nur bei P3V3_OK ein (V_GS −0,5 × VBAT: −4,5 V bei 9 V, −10,75 V bei 21,5 V). C504 1 nF (τ 17 µs). D506 BAT54 vom Knoten nach +3V3 | Ohne P3V3_OK ist der Teiler offen: Knoten ≤ 1 µA × 17 kΩ = 20 mV. Mit P3V3_OK ist VDD ≥ 2,87 V und der Knoten ≤ 3,07 V (TVS-Klemmung) < VDD + 0,3 V = 3,17 V. Beim Abschalten fließt nur die Ladung von 1 nF über D506: ≤ 10 µA bei 10 V/ms → Pin ≤ VDD + 0,24 V |
| VSERVO_SENSE (GPIO5) | Restladung der Servoschiene | Q405 NTR4171P (V_GS −0,82 × V_SERVO: −5,6 V bei 6,8 V), C417 1 nF, D403 BAT54 | wie oben; Leckstrom-Fehler ≤ 47 mV |
| ISERVO_SENSE (GPIO1) | INA240 an +3V3 | C415 von 1 µF auf **10 nF** verkleinert, R412 10 kΩ (τ 0,1 ms), D404 BAT54 | ≤ 0,1 mA bei 10 V/ms Abfall → Pin ≤ VDD + 0,24 V |
| ENABLE_BTN_N (GPIO10) | Pull-up an +3V3 | Kondensator C503 und R503 **entfernt** | keine gespeicherte Ladung am Pin |
| EXT_UART_RX (GPIO48) | externes Gerät an J112 | U602 EN = P3V3_OK: +5V_EXT ist nur bei gutem +3V3 eingeschaltet; 4,7 kΩ, ESD nach GND, keine Klemmdiode | Ein über J112 versorgtes Gerät ist ohne P3V3_OK stromlos. **Vorgabe:** Geräte an J112 nur aus +5V_EXT versorgen; eigenversorgte Geräte brauchen eine eigene Abschaltung (Rest-Risiko, O-21) |
| IBUS_RX_3V3 (GPIO21) | U203 an +3V3 | – | Ausgang ohne VCC hochohmig (Ioff); gleiche Schiene wie VDD |
| IMU_INT1, I2C | Module an +3V3 (Blatt Sensors_Display) | Vorgabe: keine eigene Versorgung der Module | gleiche Schiene |

Annahme: +3V3 fällt höchstens mit 10 V/ms. Geschätzt sind etwa 3 V/ms, aus
ca. 32 µF Schienenkapazität und 0,1 A Last. Die BAT54-Grenze von 240 mV
gilt bis 0,1 mA (Nexperia, 25 °C). Am Muster messen (O-21).

ERC: anfangs 16 Hinweise „Label connected to only one pin", seit
Actuators und Lighting_IO noch 3 (Sensors_Display). Jeder ist im Anschlussplan
(Abschnitt 6) zugeordnet; nicht ausgeblendet, `scripts/kit verify` bleibt
bis dahin fehlgeschlagen.

### 3.14 Gemeinsame Hauptabschaltung (Festlegung 2026-11-15)

**Hauptschalter trennt die LiPo-Versorgung. USB kann den Controller weiterhin versorgen.**
(Hinweis auch im Schaltplan, Blatt `Power`.)

Versorgungspfad: **LiPo → Hauptabschaltung → Y-Verteiler → ESC und VCU (J101)**.

- Die Hauptabschaltung liegt außerhalb der VCU und wirkt unabhängig von der
  Firmware.
- Der Motorstrom fließt nicht über die VCU-Platine. Ein kleiner Schalter auf
  dem Carrier wird nicht mit dem Antriebsstrom belastet; die VCU hat keinen
  eigenen Leistungsschalter.
- Die Auswahl ist **offen (O-34)**. Kriterien:

  | Kriterium | Wert / Stand |
  |---|---|
  | Dauerstrom | ESC 60 A (Hobbywing-Angabe) + VCU bis 10,1 A (3.10) – tatsächlicher Fahrstrom unbekannt (O-3) |
  | Lastspitzen | ESC 200 A Burst (Hobbywing) – Dauer und Häufigkeit unbekannt |
  | DC-Spannung | 3S: bis 12,6 V; Schaltvermögen **DC** muss angegeben sein (AC-Werte gelten nicht) |
  | Einschaltstrom | Eingangskapazität des ESC unbekannt, VCU C101/C102 ≈ 340 µF + Reglereingänge (O-24) → Funkenbildung am Kontakt; Anti-Spark-Lösung prüfen |
  | Elektronische Lösung | Body-Dioden: ein einzelner MOSFET sperrt nur in einer Richtung → Rückspeisung aus ESC-Kapazitäten/Motor (generatorisch) über die Body-Diode; Back-to-back-Anordnung, Ruhestrom und Zustand ohne Ansteuerung (muss AUS sein) prüfen |
  | Ausgeschalteter Zustand | Keine Restverbindung zwischen LiPo und ESC/VCU; keine Versorgung des Schalters selbst aus der LiPo-Seite, die bei AUS weiterläuft |

  Bis zur Auswahl wird keine Abschaltung als fertig dargestellt.

### 3.15 Betriebszustände (Prüfung an der Schaltung, Stand 2026-11-15)

Grundlage: Schaltplan nach Ergänzung von RESET/BOOT und Sensors_Display. Alle
Aussagen sind aus der Schaltung abgeleitet, **nicht gemessen**.

| Zustand | +5V / +3V3 | Aktorpuffer U201/U202, Ausgänge | Servoschiene | Sensors_Display | Bemerkung |
|---|---|---|---|---|---|
| Akku allein | +5V aus TPS54302, D501 → DevKit, +3V3 aus LDO | bis zur Freigabe Hi-Z (R501), Ausgänge low | AUS bis SERVO_PWR_EN | versorgt | Normalbetrieb (3.11) |
| USB allein | +5V **aus** (D501 sperrt, µA Sperrstrom), +3V3 aus USB | U201/U202: V_CCB = 0 → VCC-Isolation, alle Ausgänge Hi-Z; Servo-/ESC-Leitungen ohne Versorgung | AUS (LTC7803 ohne VIN) | versorgt, funktionsfähig | J112-TX treibt bei Ruhepegel High bis ca. 3 mA über 1 kΩ in ein ungespeistes Gerät → Firmware hält TX ohne Akku inaktiv (O-35) |
| Akku und USB | Dioden-ODER (3.11) | wie Akku allein | wie Akku allein | versorgt | kein Querstrom außer Sperrströmen |
| Hauptabschaltung AUS, USB bleibt | wie USB allein; ESC ebenfalls stromlos | wie USB allein; Latch U506 wird bei VBAT_PROT < 10,0 V gelöscht und bleibt über USB gelöscht | fällt mit VBAT | versorgt | Controller läuft weiter. **Wiedereinschalten:** Servoschiene und Puffer bleiben gesperrt, auch bei weiter aktiven GPIOs, bis SW501 betätigt wird (Wiederanlaufsperre 3.16). Firmware setzt zusätzlich SERVO_PWR_EN low und ACT_OE_N high (O-35) |
| RESET im Betrieb (Latch bleibt gesetzt) | unverändert | ESP32-GPIOs hochohmig: ACT_OE_N über R501 high → U201 Hi-Z, Gate-Pull-ups → Q20x leiten → Leitungen low (keine Pulse); LED_4 über U202-Eingangs-Pull-down low; Buzzer-Gate-Pull-down → still | SERVO_PWR_EN hochohmig → R415 → Q404 aus, Q403 hält RUN low → **AUS** | bleibt versorgt (OLED zeigt letztes Bild) | P3V3_OK bleibt high → +5V_EXT bleibt an. RESET ist **keine Leistungsabschaltung**: der ESC bleibt aus dem Akku versorgt und sieht keine Pulse – Verhalten nachzuweisen (O-2) |
| BOOT/Download | wie RESET | wie RESET (Anwendungs-GPIOs hochohmig; ROM nutzt nur UART0/USB, auf dem Carrier offen) | AUS | versorgt | Einschaltstörungen GPIO1–17/18 wie Anschlussplan 1 |
| DevKit fehlt | +5V an, **+3V3 stromlos** | U201/U202: V_CCA = 0 → Hi-Z; Q20x-Gates über Pull-ups an +5V → Leitungen low | SERVO_PWR_EN offen → R415 → AUS | stromlos; Pull-ups an +3V3 → keine Rückspeisung | P3V3_OK über R510 low → U602 (+5V_EXT) aus, Teiler Q505/Q405 offen. U601/U603 (LED, Empfänger) bleiben an. Externes Gerät an J112 kann über R616 4,7 kΩ + R617 10 kΩ ca. 0,2 mA in die stromlose +3V3 speisen (bekannt, O-21) |
| IMU fehlt | – | – | – | IMU_INT1 über R803 low; Bus mit 10 kΩ (OLED) → nur 100 kHz | Firmware erkennt fehlendes Gerät an NACK auf 0x6A |
| OLED fehlt | – | – | – | Bus mit 10 kΩ (IMU) → nur 100 kHz | NACK auf 0x3D |
| beide fehlen | – | – | – | SDA/SCL ohne Pull-up; interne ESP32-Pull-ups für die Erkennung, R801/R802 DNP | keine Rückspeisung |

Rückspeisung über Signalleitungen: Die I²C-Pull-ups und INT1 hängen an
+3V3, also an der Schiene des ESP32 selbst. Auf diesen Leitungen ist deshalb
keine Rückspeisung möglich. Für die übrigen Leitungen gilt O-21 (3.13).

Gesperrte Zustände bleiben in allen Fällen erhalten:
- Puffer Hi-Z ohne aktive Freigabe;
- Servoschiene AUS ohne SERVO_PWR_EN.

Das Wiedereinschalten des Akkus bei laufendem Controller ist seit 2026-11-16 in
Hardware gesperrt (3.16). Offen bleiben Unterbrechungen, die kürzer sind als
die Haltezeit der VCU-Kondensatoren (3.16, O-36).

### 3.16 Wiederanlaufsperre (O-35, Stand 2026-11-16)

**Anforderung:** Nach Verlust der LiPo-Versorgung ist eine erneute bewusste
Freigabe nötig. Das gilt auch bei weiterlaufendem USB und dauerhaft hohen
Freigabe-GPIOs. Eine reine Firmware-Lösung reicht nicht, weil ein kurzer Ausfall
zwischen zwei Abtastungen liegen kann.

**Lösung:** Freigabe-Latch in Hardware, versorgt aus +3V3. Damit überlebt der
Zustand „gesperrt“ jeden USB-Dauerbetrieb.

1. **Wächter U505 (TPS3808G01):** misst VBAT_PROT über R515 237 kΩ / R516 10 kΩ.
   Seine VBAT_OK-Leitung (Open-Drain, R517 100 kΩ) löscht U506 asynchron, sobald
   VBAT_PROT unter 10,0 V fällt (U506 Funktionstabelle: CLR low → Q low unabhängig
   von CLK und D).
2. **Latch U506 (SN74LVC1G74):** D und PRE fest auf 1. Gesetzt wird er nur durch
   eine **steigende Flanke am Tasterknoten** von SW501, also beim Loslassen oder
   beim Prellen während des Drückens, und nur, solange VBAT_OK high ist.
3. **Firmware kann den Latch nicht setzen:** GPIO10 liest den Taster über R518
   47 kΩ. Treibt die Firmware GPIO10 low, bleibt der Takt auf
   3,3 V × 47/(47+10) = 2,72 V > V_IH 2,0 V (SCES794G). Ein Taster mit Dauerschluss
   erzeugt keine Flanke.
4. **Wirkung:**
   - ACT_ARMED → Q407 in Reihe zu Q404: Q403 gibt RUN nur frei, wenn
     SERVO_PWR_EN **und** ACT_ARMED anliegen.
   - ACT_DISARMED → U204 (OR) → U201 OE high: Servo-, ESC- und LED-1–3-Ausgänge
     hochohmig. Die Ausgangsstufen ziehen die Leitungen low, es entstehen keine Pulse.
5. **Einschalten:** U505 hält VBAT_OK nach Erreichen von V_DD ≥ 0,8 V low und
   gibt erst 12–28 ms nach gültigem SENSE frei (CT offen). U506 startet daher
   immer gelöscht.
6. **Fehlender DevKit (+3V3 stromlos):** U506 und U204 sind unversorgt (Ioff).
   R420 hält Q407 aus, U201 ist über V_CCA = 0 hochohmig.

**Schwelle (Schätzung aus Datenblattgrenzen):**

| Größe | Wert |
|---|---|
| U505 V_IT | 0,405 V ± 2 % (−40…125 °C), Hysterese 1,5 % typ., 3 % max. (SBVS050N) |
| Teiler | (237 k + 10 k)/10 k = 24,7 → **10,0 V fallend**, mit ±1 % Widerständen ca. **9,61–10,40 V** |
| steigend | + Hysterese → ca. 10,15 V typ., bis 10,71 V |
| Servo-Aus (LTC7803 RUN) | RUN steigend 1,15–1,25 V, Hysterese 100 mV typ. → fallend ca. 1,05–1,15 V × 8 = 8,4–9,2 V, mit Widerstandstoleranz bis ca. 9,36 V |
| Abstand | 9,61 − 9,36 ≈ **0,25 V**: der Latch löscht vor jeder Unterspannungsabschaltung der Servoschiene. Eine Rückkehr über die RUN-Schwelle kann daher nie selbst wieder anlaufen |
| Filter | 237 k ∥ 10 k = 9,6 kΩ × 47 nF = **0,45 ms** (+ 20 µs U505), kürzer als das RUN-Filter (1,75 ms) |

Folgen und Grenzen (zu messen):
- **Einbrüche unter Last:** Fällt VBAT_PROT länger als ca. 0,5 ms unter 9,6–10,4 V,
  wird alles gesperrt und muss neu freigegeben werden. Das liegt unter der
  Firmware-Sperre (10,5 V) und bei der ESC-Abschaltung (9,75 V). Ein gesunder
  Akku sollte nicht so tief einbrechen. Ist das am Fahrzeug doch der Fall (O-3),
  werden Schwelle und Filter neu bewertet.
- **Kurze Unterbrechungen werden nicht erkannt:** Die VCU-Kondensatoren an
  VBAT_PROT (ca. 0,39 mF: C101, C102, C401–C405, C301/C302) halten die Spannung
  bei 12,6 V Start:
  - ca. 7 ms bei 0,15 A Grundlast;
  - ca. 0,9 ms bei 1,2 A mit belasteter Servoschiene.

  In dieser Zeit bleiben auch die VCU-Schienen an, die Sperre ist also nicht
  nötig. Der **ESC** liegt aber parallel am Y-Verteiler und kann in dieser Zeit
  neu starten, während die VCU weiter Pulse sendet. Sein Verhalten muss
  nachgewiesen werden (O-2, O-36).
- **RESET/Watchdog** löschen den Latch nicht (kein LiPo-Verlust). Nach jedem
  Neustart sind die Ausgänge durch die Ruhepegel ohnehin gesperrt. Ob die
  Firmware nach einem Neustart ohne Taster wieder freigeben darf, regelt O-35.
  Option: MR von U505 an DEVKIT_EN legen (belastet EN zusätzlich mit 90 kΩ,
  nicht umgesetzt).
- **Rücklesen:** Die Firmware kann den Latch nicht direkt lesen. Erkennbar ist
  der Zustand indirekt an VSERVO_SENSE ≈ 0 trotz SERVO_PWR_EN. Option: GPIO18
  als Lese-Eingang mit Serienwiderstand (nicht umgesetzt, GPIO18 bleibt Reserve).



## 4. Komponentendaten (Zwischenstand)

| Komponente | Bestätigt | Offen |
|---|---|---|
| ESP32-S3-DevKitC-1-N16R8 v1.1 | Varianten, Pinout J1/J3, PSRAM-Pins, RGB-LED GPIO38, Maße aus DXF, LDO SGM2212-3.3, USB-Dioden 1N5819HW, USB-UART CP2102N (Q) | Nachmessen am Board, Bestellnummer, Datenblatt 1N5819HW |
| FS-iA6B | 4,0–8,4 V, 6 Kanäle, PWM/PPM/i-BUS/S-BUS, 47 × 26,2 × 15 mm (Q) | Stromaufnahme, i-BUS-Pegel und Baudrate, Pinbelegung |
| Adafruit LSM6DSOX (4438) | Vin 3–5 V, I²C pegelgewandelt, 10 k Pull-ups, Adresse 0x6A/0x6B, 25,6 × 17,8 mm (Q); Pinout, Löcher und Beschaltung aus `Adafruit_LSM6DSOX.brd/.sch` (Anschlussplan 9) | Stromaufnahme (O-33), Bauhöhe gesteckt (O-31) |
| Adafruit OLED 0,96" (326) | STEMMA-QT-Revision ab 2020-08-03: I²C Standard, Auto-Reset, ca. 20 mA, 0x3D (0x3C über SJ3), 29,21 × 31,75 mm inkl. Eckfahnen (Q); Pinout aus der Eagle-Datei (Anschlussplan 9) | Strom bei Vollbild (O-32), Bauhöhe (O-31) |
| Hobbywing QuicRun Fusion Pro 2300 KV (Auswahl Owner) | 60 A / 200 A, 2–3S LiPo, BEC 6,0/7,4 V 6 A (nicht abschaltbar – rote Ader ziehen und isolieren), LiPo-Abschaltung aus/3,0/3,25/3,5 V je Zelle, „throttle lost protection", XT60, IP67 (Q Hobbywing) | Verhalten bei Signalverlust im Lauf, Default der LiPo-Abschaltung, Pulsgrenzen |
| 2 × Savöx SW-0231MG+ (Auswahl Owner) | 6,0–7,4 V, Blockierstrom 4,8 A @ 6 V / 5,9 A @ 7,4 V, 1000–2000 µs, 50–360 Hz, IP67 (Q Distributor-Datenblatt, Hauptwerte von Savöx bestätigt) | Laststrom im Fahrbetrieb; Drehmoment (Savöx-Seite widersprüchlich: 15 bzw. 20 kg·cm bei 6 V); Messbezugspunkt der Datenblattwerte |

Hinweis I²C: Beide Adafruit-Module bringen eigene Pull-ups mit; die
Gesamtlast wird im Schaltplan berechnet, Carrier-Pull-ups nur
bestückungsoptional.

### 4.1 Bauteilkandidaten Leistungsteil

Werte aus Herstellerdatenblättern, Ausnahmen markiert: [Spiegel] =
Herstellerdokument von Drittserver, [Auszug] = nur Suchauszug, [Dist] =
nur Distributordaten. LCSC-Bestand von JLCPCB, 2026-11-14/15, schwankend;
alle „Extended Parts". Alle Teile bleiben **Kandidaten** bis zur
Schutzkoordination (O-17).

| Funktion | Kandidat | Kennwerte | LCSC (Bestand) | Bemerkung |
|---|---|---|---|---|
| FET oben + unten | Infineon BSC026N04LS | 40 V, R_DS(on) max 3,6 mΩ @ 4,5 V, Q_g 16 nC | C3039672 (17 028) | R_DS(on) bei INTVCC ≈ 4,8 V prüfen |
| Drossel Servo, 2,2 µH | Coilcraft XAL1010-222ME | I_sat 34 A (−30 %), DCR max 2,80 mΩ | C5125746 (290) | Sense-Rippel 11,4 mV, nutzbar 12,2 A |
| Drossel Servo, 3,3 µH | **Coilcraft XAL1010-332MED** (Dok. 804-1, 02/25/26) | I_sat 27,4 A (−30 %, 25 °C), I_rms 18,2 A (ΔT 20 K), DCR 3,70 / max 4,10 mΩ, ca. 11,3 × 10 × 10 mm | C3911672 (342) | nutzbar 13,1 A; Kupferverlust ca. 0,5 W bei 11,2 A; I_sat bei 125 °C nicht veröffentlicht. Alternative Würth 744393605033 (DCR max 3,4 mΩ, nicht bei LCSC). Verworfen: Bourns SRP1265A-3R3M (DCR 6,8 mΩ), Vishay IHLP-4040DZ-01 (I_sat 18,6 A, DCR 14,4 mΩ); XAL8080-332 existiert nicht |
| Strom-Shunt LTC7803 | **Vishay WSL10203L000FEA** (Dok. 30183, 27-Mar-2024) | 3 mΩ, 1 %, 2,0 W bei 70 °C, TCR +100/−10 ppm/K | C844481 (7 621) | 0,38 W bei 11,2 A, ca. 1,0 W an der Stromgrenze |
| Messshunt Ausgang | **Vishay WSL10202L000FEA** (Dok. 30183) | 2 mΩ, 1 %, 2,0 W, TCR +100/−10 ppm/K | C1711510 (23 430) | statt WSL2512 2 mΩ (nur 1 W, ±275 ppm/K) |
| Strommessverstärker | **TI INA240A3DR** (SOIC-8) / INA240A3PWR (TSSOP-8) | SBOS662C: I_Q 1,8 mA typ., 2,6 mA max (−40 … 125 °C), V_S 2,7–5,5 V | C2060584 (1 350) / C544538 (895) | – |
| Drossel 5 V | Würth 74439346100 | I_sat 9,7 A (−30 %), DCR max 29,2 mΩ | C2651185 (1 296) | gültig |
| Ausgangs-Bulk Servo | 2 × Panasonic 16SVPG270MX | 270 µF / 16 V, ESR max 10 mΩ, 5,08 A | C2161621 (4 162) | 16 V > 7,81 V (OV-Schwelle) |
| Eingangs-Bulk | **Rubycon 35PJV330M10X10.5** (Hybrid-Katalog 06/2025) | 330 µF / 35 V, ESR max 20 mΩ, 2,8 A (125 °C, 100 kHz), D10 × 10,5 | C3274921 (1 000) | Gleichwertig Panasonic EEH-ZK1V331P (C278516, nur 68). EEH-ZK1V471P existiert nicht. Größer: 35PJV560M10X16.5 (560 µF, 11 mΩ, 4,0 A, 16,5 mm hoch) |
| Eingangs-MLCC | **Samsung CL32B106KBJNNNE** | 10 µF / 50 V X7R 1210; typische Kurve: ca. 7,4 µF bei 12 V (−26,5 %) | C138687 (137 925) | 3–4 Stück am Leistungsteil; Eingangsrippel 5,6 A muss überwiegend in den MLCC fließen oder ein zweiter Bulk-Elko |
| TVS | **SMBJ13A**, Littelfuse C151252 (349) oder Vishay SMBJ13A-E3/52 C968569 (138) | Vishay 88392: V_RWM 13 V, V_BR 14,4–15,9 V, V_C 21,5 V bei 27,9 A (10/1000 µs), I_R 1 µA | s. links | Littelfuse-Werte nur [Auszug]; Ladegerät-Überschwingen muss unter ca. 13 V bleiben |
| Gate-Zener Q101 | **onsemi MMSZ5245BT1G** (Rev. 17, 03/2024) oder Diodes BZT52C15-7-F (DS18004) | 14,25–15,75 V bei 8,5 mA (±5 %) bzw. 13,8–15,6 V bei 5 mA; 500 mW | C129730 (65 890) / C177014 (52 287) | Vz min 14,25 V > 12,6 V; Auslegung mit Vorwiderstand im Schaltplan (3.9) |
| Sicherung | **Littelfuse 0297015.WXNV** (MINI 32 V) [Spiegel] | 15 A, 4,58 mΩ kalt, 98 mV, I²t 270 A²s; 110 % ≥ 360 000 s, 135 % 0,75–600 s, 200 % 0,15–5 s, 350 % 0,08–0,5 s; 32 V, 1 kA | C151095 (13 643) | Eaton ATM-15 [Spiegel]: 4,93 mΩ, C3662566 (0). Kennlinie vor Freigabe vom Hersteller neu laden |

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
| O-4 | DevKitC-1-N16R8 v1.1 festgelegt; am gekauften Board nachmessen, Bauhöhe bestimmen; x-Lage des Antennenüberstands (im Footprint mittig angenommen) | Owner |
| O-8 | Bestellnummern und Bezugsquellen aller Module | Agent |
| O-15 | Polarität des XT30 am Akkukabel prüfen, „+/−" auf Silkscreen | Owner |
| O-16 | WROOM-1-N16R8 nur bis 65 °C: Platzierung fern von Reglern, Temperatur messen | Owner |
| O-17 | Bauteil- und Schutzkoordination 3S: Drossel 2,2 oder 3,3 µH (Sättigung, Temperatur, DCR, Stromgrenze, Regelkreis), Eingangskondensatoren ≥ 35 V, SMBJ13A mit Schutzspannungsnachweis, Gate-Zener mit Toleranz und Vorwiderstand, Sicherung mit Kennlinie, Derating, Einschaltstrom, DC-Spannung, Abschaltvermögen und Abstimmung gegen Kabel, XT30, Halter und Leiterbahnen, Shunts, INA240A3 | Agent |
| O-18 | Gesamtstromüberwachung INA240A3 an 2-mΩ-Ausgangsshunt, GPIO1 (aufgenommen). Offen: Gesamtfehlerbudget, ADC-Filterung, Kalibrierung | Agent |
| O-19 | 3S festgelegt; Servo-Sollwert 6,8 V vorläufig – Festschreibung nach Messung von Schleifenwiderstand und Überschwingen | Owner |
| O-20 | Fehlerreaktion: Antrieb sperren; Zeitgrenzen, Hysterese und Lenkverhalten in der Firmware-Spezifikation festlegen | Owner |
| O-21 | Eingangsschutz überarbeitet (3.13): P3V3_OK-Supervisor, geschaltete Teiler, BAT54-Spannungsgrenze, kein C am Tasterpin, +5V_EXT an P3V3_OK. Offen: Abfallrate von +3V3 und Pinspannungen beim Ab-/Einschalten messen; eigenversorgte Geräte an J112 ausschließen | Agent / Owner |
| O-22 | Datenblattquellen ohne verifizierten Herstellerlink: C101 Rubycon 35PJV330M10X10.5, C102/C301 Samsung CL32B106KBJNNNE, L301 Würth 74439346100 (we-online antwortet 403), C306 Yageo CC0603JRNPO9BN750 (C282074). Keine URL nach Namensmuster eintragen | Agent |
| O-23 | +5V: LED SK6812MINI-E und Buzzer CMT-8540S-SMT-TR gewählt (3.8); Schutzelement für J112 umgesetzt (TPS2553, Anschlussplan 8). Offen: Opsco-Datenblatt direkt vom Hersteller (nur LCSC-Kopie), LED-Footprint gegen Rev B/2, Buzzer-Beschaffung (LCSC 0) und Funktion der linken Buzzer-Pads, Lastsprünge und Regelschleife am Prototyp messen | Agent / Owner |
| O-24 | Einschaltstrom beim Einstecken (C101, C102, Reglereingänge) rechnen und messen; Q101-SOA und Sicherungs-I²t prüfen | Agent |
| O-25 | Oberer Servo-FET: V_GS,min 3,72–3,83 V (Rechnung 3.5a) liegt unter dem einzigen garantierten R_DS(on)-Punkt des BSC026N04LS (4,5 V). FET mit garantiertem R_DS(on) bei V_GS ≤ 3,5 V suchen oder am Muster messen; Ladepumpenverhalten bei 100 % Tastverhältnis (in Rev B nicht spezifiziert) am Muster messen | Agent |
| O-27 | ServoPower: Pastenöffnungen des TDSON-Drain-Pads vor Schablonenbestellung gegen Infineon Fig. 2 bzw. Bestückerregeln prüfen (3.5b); Kompensation (R413/C418/C419) und Sense-Filter (RF401/CF401) im Labor abstimmen; Entscheidung 2,2 oder 3,3 µH nach Störabstand und Lastsprung; Datenblattquellen Coilcraft, Panasonic SVPG, Samsung/Yageo-MLCC und RT-Widerstände nur als LCSC-Kopie (O-22) | Agent |
| O-28 | Controller: 1N5819HW-Daten (USB-Pfad); Status-LED-Typ (AlGaInP, V_F ≤ 2,4 V) und Taster (TL3342, JLC-Bestand 0); Buchsenleisten 1×22 mit Bauhöhe (O-4) | Agent |
| O-29 | Einschalttransienten der Servo-Freigabe messen: RUN, Q403-Gate und +V_SERVO beim Einstecken des Akkus und beim ESP32-Hochlauf | Owner |
| O-30 | Actuators: ESD-TVS je Steckerausgang mit V_RWM ≥ 8 V (Schienenfehler 7,81 V, ESC-BEC 7,4 V) auswählen und Datenblatt prüfen; Stecker-Bauteil 1×3 2,54 mm festlegen | Agent |
| O-31 | Sensors_Display: Buchsen Samtec SSW-109/108-01-T-S gewählt (8,51 mm); offen: Bohrung 1,0 mm gegen Samtec-Footprint prüfen, Stiftleistenträger der Module messen, Abstandshalter M2,5 (ca. 11 mm, Schätzung) auswählen, 1:1-Ausdruck an echten Modulen prüfen, Achsen der IMU für die Firmware festhalten | Agent / Owner |
| O-32 | I²C-Anstiegszeit an TP801/TP802 und OLED-Strom bei Vollbild messen; 400 kHz erst danach | Owner |
| O-33 | ~~ST-Datenblatt LSM6DSOX~~ – erledigt 2026-11-16 (DS12814 Rev 4, Anschlussplan 9.3): INT1 beim Einschalten 0 (R803), Push-Pull aktiv high, 0,55 mA typ. | – |
| O-34 | Hauptabschaltung außerhalb der VCU auswählen (3.14): Dauer-/Spitzenstrom, DC-Schaltvermögen bei 12,6 V, Einschaltstrom; bei elektronischer Lösung Body-Dioden, Rückspeisung, AUS-Zustand | Owner |
| O-35 | Wiederanlaufsperre in Hardware umgesetzt (3.16). Firmware zusätzlich: bei VBAT-Verlust SERVO_PWR_EN low, ACT_OE_N high, ESC neutral; Freigabe nach Neustart nur über SW501; GPIO10 ohne interne Pull-ups; J112-TX ohne Akku inaktiv; GPIO0 und GPIO6 nie als Ausgang. Messen: Schwelle, Löschen bei langsamem und schnellem Abfall, kein Setzen durch GPIO10 | Agent / Owner |
| O-36 | Unterbrechungen kürzer als die Haltezeit der VCU-Kondensatoren (ca. 0,9–7 ms, Schätzung) erkennt die Sperre nicht; ESC-Verhalten bei kurzer eigener Versorgungsunterbrechung mit anliegenden Pulsen nachweisen (mit O-2) | Owner |

Erledigt: O-5 (DevKit-LDO), O-6 (Lenkservos), O-7 (LTC7803 Rev B, 3.5a;
Kompensation weiter unter O-27), O-9 (Projektort), O-14 (ersetzt durch O-17),
O-26 (Footprints, 3.5b; Rest unter O-27), O-11 (Modulpinouts, Anschlussplan 9). O-10 bis O-13 stehen im
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
