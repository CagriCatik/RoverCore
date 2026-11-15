# VCU Rev 1 – GPIO- und Anschlussplan

Status: **Entwurf zur Review**, Stand 2026-11-15 (3S-Basis). Maschinenlesbare Fassung:
[`hardware/interfaces/pinmap.csv`](../../hardware/interfaces/pinmap.csv).
Die Carrier-Referenzbezeichner (J101, U201 …) sind vorläufig und werden im
Schaltplan vergeben; danach werden Pinmap und Schaltplan abgeglichen.
„J1-x“ und „J3-x“ bezeichnen immer die Stiftleisten des DevKit.

Grundlagen: ESP32-S3 Series Datasheet v2.2, ESP32-S3-WROOM-1/1U Datasheet
v1.8, ESP32-S3-DevKitC-1 User Guide v1.1, ESP-IDF-Doku (GPIO, LEDC).

## 1. Randbedingungen aus den Datenblättern

| Thema | Fakt | Quelle | Folge |
|---|---|---|---|
| Peripherie-Routing | LEDC, RMT, UART und I²C sind über die GPIO-Matrix auf jeden GPIO legbar | ESP-IDF GPIO-Übersicht | Zuordnung nach Layout und Boot-Verhalten statt nach Funktion |
| RMT | 4 TX-Kanäle | DS v2.2, Abschnitt RMT | Alle 4 TX-Kanäle für die 4 LED-Ausgänge (SK6812MINI-E, WS2812-kompatibles Protokoll); keiner frei |
| LEDC | 8 Kanäle, 4 Timer, nur Low-Speed-Modus | ESP-IDF LEDC | 5 × Servo/ESC + Buzzer = 6 Kanäle |
| ADC | ADC1 = GPIO1–10, ADC2 = GPIO11–20; ADC2 nicht zusammen mit Wi-Fi | DS v2.2 Tab. 2-8 und Hinweis | Messungen nur auf ADC1 |
| Einschaltstörungen | GPIO1–17: Low-Pegel-Glitch 60 µs; **GPIO18: High- und Low-Glitch**; GPIO19/20: High-Glitches | DS v2.2 Tab. 2-2 | Keine Ausgänge auf GPIO18; Low-Glitches sind bei Servo-/ESC-Signalen (Ruhepegel low) unkritisch |
| Strapping | GPIO0 Pull-up, GPIO3 floatend, GPIO45/46 Pull-down | DS v2.2 Tab. 3-1 | Auf dem Carrier nicht beschalten |
| PSRAM | WROOM-1-N16R8 = 16 MB Quad-Flash + 8 MB **Octal**-PSRAM; IO35–37 belegt | WROOM-1 DS v1.8 | GPIO35–37 gesperrt |
| GPIO47/48 | 1,8 V nur bei R16V-Varianten | DS v2.2 Pin-Fußnote 4 | Bei N16R8 normale 3,3-V-GPIOs |
| Pegel | V_IH max = VDD + 0,3 V | DS v2.2 Tab. 5-4 | **Nicht 5-V-tolerant** – jeder 5-V-Eingang braucht Pegelwandler oder Klemmung |
| Temperatur | WROOM-1-N16R8: Umgebung −40 … 65 °C | WROOM-1 DS v1.8 | Gilt im Fahrzeug unter der Karosserie; Lage fern von Reglern |

## 2. GPIO-Zuordnung

| GPIO | DevKit-Pin | Signal | Funktion | Richtung |
|---|---|---|---|---|
| 4 | J1-4 | VBAT_SENSE | ADC1_CH3 | Analog ein |
| 5 | J1-5 | VSERVO_SENSE | ADC1_CH4 – Ersatz für fehlendes PGOOD des LTC7803 | Analog ein |
| 6 | J1-6 | IMU_INT1 | GPIO-Interrupt | ein |
| 7 | J1-7 | SERVO_PWR_EN | gibt Servoschiene frei (aktiv high); ohne aktive Freigabe AUS (Versorgungsdokument 3.13) | aus |
| 8 | J1-12 | I2C_SDA | I²C0 | bidirektional |
| 9 | J1-15 | I2C_SCL | I²C0 | aus |
| 10 | J1-16 | ENABLE_BTN_N | Freigabetaster, aktiv low | ein |
| 11 | J1-17 | STATUS_LED | GPIO | aus |
| 12 | J1-18 | BUZZER | LEDC | aus |
| 13 | J1-19 | ESC_PWM | LEDC | aus |
| 14 | J1-20 | SERVO_AUX2_PWM | LEDC | aus |
| 15 | J1-8 | SERVO_FRONT_PWM | LEDC | aus |
| 16 | J1-9 | SERVO_REAR_PWM | LEDC | aus |
| 17 | J1-10 | SERVO_AUX1_PWM | LEDC | aus |
| 39 | J3-9 | LED_4 | RMT TX | aus |
| 40 | J3-8 | LED_3 | RMT TX | aus |
| 41 | J3-7 | LED_2 | RMT TX | aus |
| 42 | J3-6 | LED_1 | RMT TX | aus |
| 21 | J3-18 | IBUS_RX | UART1 RX | ein |
| 2 | J3-5 | ACT_OE_N | Freigabe der Ausgangspuffer U201 (aktiv low) | aus |
| 1 | J3-4 | ISERVO_SENSE | ADC1_CH0 – INA240A3, Gesamtstrom Servoschiene (O-18) | Analog ein |
| 47 | J3-17 | EXT_UART_TX | UART2 TX | aus |
| 48 | J3-16 | EXT_UART_RX | UART2 RX | ein |

Reserve (nur Testpunkt): GPIO18 (nur als Eingang).
Gesperrt: GPIO0/3/45/46 (Strapping), 19/20 (USB), 35–37 (PSRAM),
38 (RGB-LED v1.1), 43/44 (UART0 zum CP2102N).

Layoutgedanke: Aktoren, Messung und Bedienung auf der J1-Seite, Licht und
Kommunikation auf der J3-Seite. Die Leistungsseite des Carriers liegt damit
an J1, Licht- und Erweiterungsstecker an J3.

GPIO39–42 sind die JTAG-Pads. Standardmäßig läuft JTAG über USB
(GPIO19/20); die Pads sind dann normale GPIOs. Das wird beim ersten
Firmware-Test mit einem Pegeltest bestätigt.

## 3. Signalaufbereitung (Vorgabe für den Schaltplan)

| Signalgruppe | Aufbereitung | Zustand bei Reset / ohne 3,3 V |
|---|---|---|
| Servo/ESC (5×) | Puffer U201 3,3 → 5 V mit Ioff (3.1), Freigabe über `ACT_OE_N`; 100k Pull-downs an Ein- und Ausgang; Serienwiderstand + ESD am Stecker | Ausgang hochohmig + Pull-down → low, keine Pulse |
| LED SK6812MINI-E (4×) | LED_1–3 über U201, LED_4 über U202 (ohne OE); 5-V-Ausgang (SK6812MINI-E V_IH 0,65 × V_DD) | Daten low, LEDs behalten/aus |
| i-BUS ein | U203 SN74LVC1G17 an 3,3 V (5-V-tolerant, Ioff), 2,2 kΩ Serie, 100k Pull-down | Eingang hochohmig |
| Erweiterungs-UART | TX: Serienwiderstand; RX: Serienwiderstand + Klemmung auf 3,3 V, 10k Pull-up | definiert |
| I²C | Pull-ups auf den Modulen (je 10k, Adafruit); Carrier-Pull-ups nur bestückungsoptional | – |
| Taster | 10k Pull-up, RC-Entprellung | nicht gedrückt |
| Buzzer | Low-Side-MOSFET, Gate-Pull-down, Freilaufdiode bei magnetischem Buzzer | aus |
| Akkumessung | Kandidat 120k/20k + RC + Serienwiderstand/Klemmung; Fall „Akku an, ESP32 aus" offen (Versorgungsdokument 3.9, O-21) | – |
| Servoschienen-Messung | Teiler auf < 2,9 V (ADC ATTEN3) + RC | – |
| Servostrom-Messung | INA240A3 an 2-mΩ-Ausgangsshunt, RC zum ADC (Versorgungsdokument 3.6) | – |

### 3.1 Pufferauswahl (Stand 2026-11-15)

Alle Werte aus TI-Datenblättern (ti.com, abgerufen 2026-11-15); LCSC-Bestand
von JLCPCB am selben Tag, schwankend, alle „Extended Parts".

**Ausgänge 3,3 → 5 V (9 Kanäle)**

| Ref | Baustein | Kanäle | Versorgung | LCSC (Bestand) |
|---|---|---|---|---|
| U201 | **SN74LVC8T245PWR** (TSSOP-24), SCES584D | ESC, Servo vorne, hinten, Reserve 1, Reserve 2, LED_1–3 | VCCA = +3V3_DEVKIT, VCCB = +5V | C27643 (65 377) |
| U202 | **SN74LVC1T45DBVR** (SOT-23-6), SCES515N | LED_4 | VCCA = +3V3_DEVKIT, VCCB = +5V | C7843 (305 880) |

Warum dieser Baustein:

- **Ioff an A- und B-Seite**, ±2 µA bei 0–5,5 V, wenn eine der beiden
  Versorgungen 0 V ist (EC-Tabelle).
- **VCC-Isolation:** Fällt eine Versorgung unter 100 mV, werden beide Ports
  kurz schwach nach unten gezogen und dann hochohmig (§7.3.5). Im USB-Betrieb
  ohne Akku (+5V aus, ESP32 aktiv) fließt damit kein Strom aus den GPIOs in
  die 5-V-Seite.
- ±32 mA Treiberstrom bei 4,5–5,5 V, ESD 4 kV HBM / 1 kV CDM.

Verworfen:

| Baustein | Grund |
|---|---|
| SN74LV1T125 / LV1T34 | kein Ioff spezifiziert, Ausgang abs. max. VCC + 0,5 V |
| SN74AHCT1G125 / AHCT125 | kein Ioff (nur Eingangsstrom bei VCC = 0 spezifiziert); AHCT125 bei JLC nicht lieferbar |
| SN74HCT125 / ACT125 | Eingangsklemmdiode nach VCC – der ESP32 würde die 5-V-Schiene rückspeisen |
| SN74LV4T125 (Ersatz) | Ioff spezifiziert, aber widersprüchlich: Abs-Max-Wert für abgeschalteten Ausgang 4,6 V, Ioff-Test bis 5,5 V |
| SN74LV8T244 | kein Ioff, nur 8 Stück bei JLC |
| SN74LVC1G125/1G34 an 5 V | V_IH = 0,7 × VCC = 3,5 V – mit 3,3-V-Eingang nicht garantiert |

Beschaltung:

- **DIR an +3V3** → Richtung A → B (Function Table 7-1).
- **OE (aktiv low, auf VCCA bezogen) an GPIO2 = `ACT_OE_N`**, 10k Pull-up auf
  +3V3. Bei Reset und während des Bootens sind alle Ausgänge von U201
  hochohmig; die Firmware gibt sie erst nach der Initialisierung frei. Der
  Low-Glitch von GPIO2 beim Einschalten (60 µs) könnte die Ausgänge kurz
  freigeben; dann liegen aber die Eingänge über ihre Pull-downs auf low, also
  auch die Ausgänge – kein Puls.
- **Pull-downs 100k an allen A-Eingängen** (Datenblatt verlangt definierte
  Pegel an nicht getriebenen Eingängen) und **100k an allen B-Ausgängen**, damit
  ESC und Servos bei hochohmigem Puffer sicher „kein Signal" sehen.
- U202 (1T45) hat kein OE; sein Kanal ist LED_4. Bei hochohmigem
  GPIO39 hält der Eingangs-Pull-down die Datenleitung low.
- Serienwiderstand 33–100 Ω je Ausgang vor dem Stecker, ESD-Diode am Stecker.
- 0,1 µF an VCCA und VCCB, nah am Baustein.

Pegel- und Timingreserve (Schätzung):

| Prüfung | Wert | Reserve |
|---|---|---|
| ESP32 V_OH min → A-Eingang V_IH | 0,8 × 3,3 V = 2,64 V ≥ 2,0 V (VCCA 3,0–3,6 V) | 0,64 V |
| B-Ausgang → LED V_IH | V_OH ≥ 3,8 V bei −32 mA / 4,5 V; bei der kleinen Datenlast nahe +5V. Benötigt V_IH 0,65 × V_DD = 3,35 V bei 5,16 V (SK6812MINI-E Rev B/2) | LED und Puffer hängen an derselben +5V-Schiene, die Schwelle wandert mit |
| Laufzeit A → B | 4,4 ns max (VCCA 3,3 V, VCCB 5 V) | ≪ 1,2 µs Mindest-Bitperiode der SK6812MINI-E, ≪ Servo-Auflösung |
| Servo/ESC | 5-V-Puls 1–2 ms, 50–400 Hz | unkritisch |

**Eingang i-BUS**

| Ref | Baustein | Versorgung | LCSC (Bestand) |
|---|---|---|---|
| U203 | **SN74LVC1G17DBVR** (Schmitt-Trigger, SOT-23-5), SCES351Y | +3V3_DEVKIT | C7836 (6 125) |

- Eingang bis 5,5 V (abs. max. 6,5 V) unabhängig von VCC, Ioff ±10 µA bei
  VCC = 0.
- Schwellen bei VCC = 3 V: V_T+ 1,48–1,92 V, V_T− 0,89–1,20 V, Hysterese
  0,51–0,83 V. Ein Empfänger mit 3,3-V- oder 5-V-Pegel wird sicher erkannt.
- Laufzeit ≤ 6,5 ns – bei 115 200 Bd (8,7 µs je Bit) vernachlässigbar.
- 2,2 kΩ Serienwiderstand am Eingang plus ESD-Diode am Stecker: begrenzt den
  Strom, falls am Signalpin mehr als 5,5 V anliegen (der Empfänger darf bis
  8,4 V versorgt werden; vom Carrier bekommt er 5 V).
- 100k Pull-down am Eingang, damit ohne Empfänger kein offener Eingang
  Zeichen erzeugt.
- Der Ausgang (3,3-V-CMOS) erfüllt V_IH des ESP32 (0,75 × 3,3 V = 2,48 V).

**FS-iA6B (O-10, weiterhin offen):** Die offizielle FlySky-Anleitung
(2024-03-27, über einen Händler gehostet) bestätigt die Ports „Servo
(i-BUS/S.BUS)" und „SENS (i-BUS)" sowie 4,0–8,4 V Versorgung, nennt aber
weder Pegel noch Baudrate noch Pinreihenfolge. 115 200 Bd 8N1 ist nicht aus
einer Herstellerquelle belegt. Die Aufbereitung oben deckt 3,3 V und 5 V ab;
Baudrate und Polarität werden beim Bring-up gemessen. Am Sender muss am
Servo-Port i-BUS (nicht S.BUS, invertiertes anderes Protokoll) eingestellt
sein.

### 3.2 Firmware-Anforderungen LEDs (SK6812MINI-E)

Quelle: Opsco SK6812MINI-E Spec Rev B/2 (2025-11-22, LCSC-Kopie, §10). Werte
vor der Implementierung gegen das Herstellerdokument prüfen (O-23).

| Anforderung | Wert |
|---|---|
| Protokoll | WS2812-kompatibel, 800 kbit/s, ein RMT-TX-Kanal je LED (GPIO39–42) |
| 0-Bit | T0H 0,25–0,40 µs, T0L ≥ 0,80 µs |
| 1-Bit | T1H 0,70–1,00 µs, T1L ≥ 0,2 µs |
| Bitperiode | ≥ 1,2 µs |
| Reset | low > 200 µs (ältere Rev 04: > 80 µs) – Firmware hält > 280 µs ein |
| Farbreihenfolge | laut Datenblatt prüfen, nicht aus WS2812B-Bibliotheken übernehmen |
| Strom | max. ca. 44 mA je LED (3 × 14,5 mA + IC) bei voller Helligkeit |
| Start | Ausgänge erst nach `ACT_OE_N`-Freigabe treiben; beim Booten bleiben die Datenleitungen low |


## 4. Steckerbelegungen

Pin 1 ist auf dem Silkscreen markiert. Alle Signalspannungen bezogen auf GND.

### J101 – Akku (XT30, Platinenseite)

| Pin | Signal | Spannung | Strom |
|---|---|---|---|
| + | VBAT_IN | 3S: 9,0–12,6 V (Entwurfsbasis seit 2026-11-15) | Fahrbetrieb ca. 6 A, Worst Case ca. 10,1 A bei 9,0 V (Versorgungsdokument 3.2) |
| − | GND | – | – |

### J102, J103 – Lenkservos (Molex Micro-Fit 3.0, 3-polig, verriegelnd)

Geändert 2026-11-15: Die gewählten Savöx SW-0231MG+ ziehen blockiert
4,8 A bei 6,0 V (bei 6,8 V Sollwert ca. 5,0–5,1 A als vereinfachte Lastabschätzung, Versorgungsdokument 3.4). Eine 2,54-mm-Stiftleiste (ca. 3 A je
Kontakt) reicht dafür nicht.

| Pin | Signal | Spannung | Richtung |
|---|---|---|---|
| 1 | SERVO_x_PWM (5-V-Puls) | 0/5 V | aus |
| 2 | +V_SERVO | Kandidat 6,8 V (6,69–6,91 V), Versorgungsdokument 3.4 | Versorgung aus, bis ca. 5,1 A |
| 3 | GND | – | Rückleiter, bis 5,0 A |

- Platinenstecker: **Molex 43650-0300** (liegend, THT, Kunststoff-Pegs),
  LCSC C503478 (6 548). Gegenstück 43645-0300 (C259740), Crimpkontakte
  43030-0038 für 18 AWG (C259772) oder 43030-0001 für 20–24 AWG (C259786).
- Belastbarkeit (Molex PS-43045, Drittspiegel): 8 A UL je Kontakt; für
  3-polig nennt Molex keinen Derating-Wert, interpoliert ca. 8 A (18 AWG) /
  6,5 A (20 AWG) bei 30 K Erwärmung (Schätzung). Die Servoleitung selbst ist
  22 AWG mit JR-Stecker: Adapterkabel JR → Micro-Fit möglichst kurz, Kabel
  zur Platine 20 AWG oder stärker.
- Die Micro-Fit-Verriegelung sitzt im Gegenstück; der Stecker ist kodiert,
  Verpolen ist mechanisch ausgeschlossen. Pin-Reihenfolge wie RC-Standard
  (Signal, +, −), damit das Adapterkabel 1:1 verdrahtet wird.
- Servo-Puls (Datenblatt): 1000–2000 µs, Neutral 1500 µs, 50–360 Hz;
  Endpunkte in der Firmware begrenzen.

J102 = vorne, J103 = hinten.

### J104, J105 – Reserve-Servos (3-polige Stiftleiste 2,54 mm, RC-Standard)

| Pin | Signal | Spannung | Richtung |
|---|---|---|---|
| 1 | SERVO_AUXx_PWM (5-V-Puls) | 0/5 V | aus |
| 2 | +V_SERVO | Kandidat 6,8 V (6,69–6,91 V) plus Überschwingen; im Reglerfehler bis 7,81 V | Versorgung aus, max. 0,5 A |
| 3 | GND | – | – |

J104 = Reserve 1, J105 = Reserve 2. Budget je 0,5 A (Versorgungsdokument
Abschnitt 5). Zulässig sind nur Geräte, deren Versorgungsbereich die
**gesamte tatsächliche Schienenspannung** abdeckt (Versorgungsdokument 3.2);
ein weiterer SW-0231MG+ ist hier wegen des Strombudgets nicht freigegeben.
Silkscreen „S + −" und „max 0,5 A".

### J106 – ESC (3-polige Stiftleiste 2,54 mm)

| Pin | Signal | Spannung | Richtung |
|---|---|---|---|
| 1 | ESC_PWM (5-V-Puls) | 0/5 V | aus |
| 2 | **nicht verbunden** (ESC-BEC +) | – | – |
| 3 | GND | – | – |

Silkscreen „BEC NC". Damit wird das ESC-BEC nie mit einem VCU-Netz verbunden.

ESC: **Hobbywing QuicRun Fusion Pro 2300 KV** (Auswahl Owner 2026-11-15). Laut
Hobbywing-Anleitung lässt sich das BEC (6,0/7,4 V, 6 A) nicht abschalten;
Hobbywing empfiehlt, die rote Ader aus dem Gasstecker zu ziehen und zu
isolieren. Zusätzlich bleibt Pin 2 auf der VCU unbeschaltet. Das Verhalten
bei Signalverlust im Lauf nennt die Anleitung nicht („throttle lost
protection" ist nur als Funktion genannt) – Test am ESC ohne Motor (O-2).

### J107 – Empfänger FS-iA6B, i-BUS (3-polige Stiftleiste 2,54 mm)

| Pin | Signal | Spannung | Richtung |
|---|---|---|---|
| 1 | IBUS (Servo-Ausgang des Empfängers) | Pegel offen (O-10) | ein |
| 2 | +5V_RX | 5,0 V (Empfänger: 4,0–8,4 V) | Versorgung aus |
| 3 | GND | – | – |

Pinreihenfolge am Empfänger (i-BUS-Port) ist noch nicht verifiziert (O-10).

### J108–J111 – LEDs SK6812MINI-E (JST-PH 3-polig, verpolsicher)

| Pin | Signal | Spannung | Richtung |
|---|---|---|---|
| 1 | +5V_LED | 4,74–5,16 V, max. ca. 44 mA je LED (Opsco SK6812MINI-E Rev B/2) | Versorgung aus |
| 2 | LED_x_DIN | 0/5 V | aus |
| 3 | GND | – | – |

### J112 – Erweiterungs-UART (JST-PH 4-polig)

| Pin | Signal | Spannung | Richtung |
|---|---|---|---|
| 1 | +5V_EXT | 4,74–5,16 V statisch, Transienten bis 5,5 V; verbindliches Budget max. 0,2 A dauernd (Schutzelement im Schaltplan) | Versorgung aus |
| 2 | EXT_UART_TX | 3,3 V | aus (von VCU) |
| 3 | EXT_UART_RX | 3,3 V, nicht 5-V-tolerant | ein (zur VCU) |
| 4 | GND | – | – |

### U501 – DevKit-Sockel (2 × 1×22 Buchsenleiste, 2,54 mm, Abstand 22,86 mm)

Belegung siehe `pinmap.csv`; Footprint-Pads 1–22 = J1-1…J1-22, 23–44 = J3-1…J3-22
(projektlokal, `make_devkit_socket.py`). Silkscreen: Umriss des DevKit, „ANT",
„USB" mit Pfeil, Pfeil und „J1-1"/„J3-1" an Pin 1 beider Leisten.

### J115 – IMU-Modul (Adafruit 4438), J116 – OLED-Modul (Adafruit 326)

Benötigte Signale: IMU – VIN (+3V3_DEVKIT), GND, SCL, SDA, INT1;
OLED – VIN (+3V3_DEVKIT), GND, SCL, SDA. Die Pinreihenfolge der
Stiftleisten beider Module ist **noch nicht verifiziert** (O-11) und wird
aus den Adafruit-Platinendateien oder am Modul bestimmt, bevor der Footprint
entsteht. Alternative: STEMMA-QT-Kabel (JST-SH 4-polig) für I²C plus
separater INT1-Draht.

### Bedienelemente auf dem Carrier

| Ref | Funktion |
|---|---|
| U501 | DevKit-Sockel (Blatt `Controller`) |
| D501 | Schottky Carrier-5V → DevKit-5V-Pin, ersetzt JP101 (Versorgungsdokument 3.11) |
| SW501 | Freigabetaster |
| BZ101 | Buzzer Same Sky CMT-8540S-SMT-TR (magnetisch, 5 V, max. 150 mA, Freilaufdiode, Low-Side-MOSFET ≥ 0,52 A) |
| D502 | Status-LED |
| TP | Messpunkte: VBAT_IN, VBAT_PROT, +V_SERVO, +5V, +3V3_DEVKIT, GND (mehrfach), IBUS_RX, ein Servo- und ein LED-Signal |

## 5. Offene Punkte

| Nr. | Punkt |
|---|---|
| O-10 | FS-iA6B: i-BUS-Pegel, Baudrate und Pinreihenfolge am i-BUS-Port |
| O-11 | Pinreihenfolge der Stiftleisten von Adafruit 4438 und 326 (oder Wahl STEMMA QT) |
| O-12 | ~~Pufferbausteine~~ – erledigt 2026-11-15: SN74LVC8T245 + SN74LVC1T45 (Ausgänge), SN74LVC1G17 (i-BUS), Abschnitt 3.1 |
| O-13 | Arduino-ESP32-Core-Version festlegen und prüfen, dass LEDC/RMT/UART auf den gewählten Pins wie vorgesehen funktionieren (Bring-up-Test) |
