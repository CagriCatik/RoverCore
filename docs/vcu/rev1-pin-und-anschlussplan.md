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
| Strapping | GPIO0 Pull-up, GPIO3 floatend, GPIO45/46 Pull-down | DS v2.2 Tab. 3-1 | GPIO3/45/46 auf dem Carrier nicht beschalten; GPIO0 nur mit BOOT-Taster SW503 nach GND (Abschnitt 10) |
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
| 12 | J1-18 | BUZZER | LEDC | aus – **verbunden** (Blatt Lighting_IO) |
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
| 47 | J3-17 | EXT_UART_TX | UART2 TX | aus – **verbunden** (Blatt Lighting_IO) |
| 48 | J3-16 | EXT_UART_RX | UART2 RX | ein – **verbunden** (Blatt Lighting_IO) |

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
| Erweiterungs-UART | TX: 1 kΩ in Serie; RX: 4,7 kΩ in Serie am Stecker, ESD-Diode nach GND, 10k Pull-up an +3V3 (keine Klemmdiode nach +3V3 – sie würde die Schiene rückspeisen; Versorgungsdokument 3.13) | definiert |
| I²C | Pull-ups auf den Modulen (je 10k, Adafruit); Carrier-Pull-ups nur bestückungsoptional | – |
| Taster | 10k Pull-up, RC-Entprellung | nicht gedrückt |
| Buzzer | Low-Side-MOSFET, Gate-Pull-down, Freilaufdiode bei magnetischem Buzzer | aus |
| Akkumessung | 120k/20k + 100 nF, 10 kΩ in Serie zum Pin; Q505 klemmt den Teiler ohne +3V3 auf GND (Versorgungsdokument 3.13) | 0 V am Pin ohne +3V3 |
| Servoschienen-Messung | Teiler auf < 2,9 V (ADC ATTEN3) + RC, 10 kΩ in Serie, Klemmung Q405 ohne +3V3 | 0 V am Pin ohne +3V3 |
| Servostrom-Messung | INA240A3 an 2-mΩ-Ausgangsshunt, RC und 10 kΩ in Serie zum ADC (Versorgungsdokument 3.6) | INA240 an +3V3: ohne +3V3 kein Ausgang |

### 3.1 Pufferauswahl (Stand 2026-11-15)

Alle Werte aus TI-Datenblättern (ti.com, abgerufen 2026-11-15); LCSC-Bestand
von JLCPCB am selben Tag, schwankend, alle „Extended Parts".

**Ausgänge 3,3 → 5 V (9 Kanäle)**

| Ref | Baustein | Kanäle | Versorgung | LCSC (Bestand) |
|---|---|---|---|---|
| U201 | **SN74LVC8T245PWR** (TSSOP-24), SCES584D (Mai 2026); Kanalfolge A1/B1 ESC, A2 vorne, A3 hinten, A4 Reserve 1, A5 Reserve 2, A6–A8 LED_1–3 | ESC, Servo vorne, hinten, Reserve 1, Reserve 2, LED_1–3 | VCCA = +3V3_DEVKIT, VCCB = +5V | C27643 (65 377) |
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

- **DIR über R209 10 kΩ an +3V3** → Richtung A → B (DIR-Eingangsstrom ≤ 2 µA → 20 mV).
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
- Je Steckerausgang (ESC, 4 Servos) – **überarbeitet nach Review, keine
  Klemmung in die +5V-Schiene mehr**:
  - U201-B-Ausgang steuert das Gate von Q20x (NTR4003N, Open Drain, 30 V).
  - Drain → 470 Ω → Stecker-Pin 1.
  - Pull-up: +5V → BAT54 (D20x) → 2,2 kΩ an den Drain.
  - 100k Pull-down am Drain.
- Fremdspannung am Signalpin (ESC-BEC bis 7,4 V bei versetztem Stecker,
  Schienenfehler 7,81 V):
  - **VCU ein, Q leitend:** 16,6 mA über 470 Ω in Q (I_D max. 0,56 A).
  - **VCU ein, Q sperrt:** BAT54 in Sperrrichtung (3,07 V).
  - **VCU aus (+5V = 0):** BAT54 sperrt 7,81 V (V_R 30 V); Drain verträgt 30 V.
  - In allen Fällen erreicht die +5V-Schiene nur der BAT54-Sperrstrom
    (≤ 2 µA bei 25 V). Die VCU wird nicht versorgt. U201 ist mit dem Pin nicht
    verbunden.
  - Die Ioff-Funktion des SN74LVC8T245 wird dafür nicht gebraucht; sie gilt
    nur für den Baustein selbst.
- **Die Stufe invertiert.** Pull-ups an A1–A5 (nach +3V3) und an den Gates
  (nach +5V) halten die Leitung low (kein Puls), solange GPIO oder U201
  hochohmig sind (Reset, ACT_OE_N high, VCC-Isolation).
  **Firmware-Anforderung:** LEDC-Ausgänge für ESC und Servos invertieren
  (Ausgangsinvertierung der GPIO-Matrix).
- High-Pegel (Schätzung): ca. 4,5 V offen, 4,2 V an 50 kΩ, 3,6 V an 10 kΩ
  Eingangswiderstand. Low: Q mit ≤ 1,5 Ω. Pull-up-Strom 2,2 mA je Kanal
  bei Low.
- ESD-TVS am Stecker: V_RWM ≥ 8 V nötig (O-30).
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

Beide Module stecken mit ihrer Stiftleiste direkt in einer Buchsenleiste des
Carriers (Bauteilseite oben). Keine STEMMA-QT-Kabel, keine losen Leitungen.
Pinbelegung, Geometrie und Beschaltung aus den Original-Eagle-Dateien von
Adafruit (Abschnitt 9).

| J115 (1×9, Adafruit 4438 JP1) | 1 VIN = +3V3 · 2 3Vo (frei) · 3 GND · 4 SCL · 5 SDA · 6 DO (frei, 0x6A) · 7 CS (frei) · 8 INT1 = IMU_INT1 · 9 INT2 (frei) |
|---|---|
| **J116 (1×8, Adafruit 326 JP2)** | 1 Data = SDA · 2 Clk = SCL · 3 DC/A0 (frei, 0x3D) · 4 Rst (frei) · 5 CS (frei) · 6 3Vo (frei) · 7 Vin = +3V3 · 8 GND |

### Bedienelemente auf dem Carrier

| Ref | Funktion |
|---|---|
| U501 | DevKit-Sockel (Blatt `Controller`) |
| D501 | Schottky Carrier-5V → DevKit-5V-Pin, ersetzt JP101 (Versorgungsdokument 3.11) |
| SW501 | Freigabetaster |
| SW502 | `RESET`: DevKit-EN nach GND (Abschnitt 10) |
| SW503 | `BOOT`: GPIO0 nach GND (Abschnitt 10) |
| BZ101 | Buzzer Same Sky CMT-8540S-SMT-TR (magnetisch, 5 V, max. 150 mA, Freilaufdiode, Low-Side-MOSFET ≥ 0,52 A) |
| D502 | Status-LED |
| TP | Messpunkte: VBAT_IN, VBAT_PROT, +V_SERVO, +5V, +3V3_DEVKIT, GND (mehrfach), IBUS_RX, ein Servo- und ein LED-Signal |

## 5. Offene Punkte

| Nr. | Punkt |
|---|---|
| O-10 | FS-iA6B: i-BUS-Pegel, Baudrate und Pinreihenfolge am i-BUS-Port |
| O-11 | ~~Pinreihenfolge der Stiftleisten von Adafruit 4438 und 326~~ – erledigt 2026-11-15 aus den Adafruit-Eagle-Dateien, direkte Steckmontage (Abschnitt 9) |
| O-12 | ~~Pufferbausteine~~ – erledigt 2026-11-15: SN74LVC8T245 + SN74LVC1T45 (Ausgänge), SN74LVC1G17 (i-BUS), Abschnitt 3.1 |
| O-13 | Arduino-ESP32-Core-Version festlegen und prüfen, dass LEDC/RMT/UART auf den gewählten Pins wie vorgesehen funktionieren (Bring-up-Test) |


## 6. Prüfbericht DevKit-Sockel U501 und globale Labels (Stand 2026-11-15, nach RESET/BOOT)

Erzeugt mit `python3 hardware/scripts/check_socket_pinmap.py`. Das Skript
exportiert die Netzliste mit kicad-cli und vergleicht alle 44 Pads mit
`pinmap.csv`. Abweichungen führen zu Exit-Status 1. Die 11 in `pinmap.csv`
als `reserved` geführten Pins sind **erwartete No-Connects**. EN (J1-3) und
GPIO0 (J3-14) sind seit RESET/BOOT verbunden und werden als Signal geprüft
(vorher 13 No-Connects, 24 Signal). Geprüft wird
dabei auch, dass der Pinname im Netz `unconnected-(…)` zum GPIO und zur
Padnummer passt.

Ergebnis: **26 Signal, 7 Versorgung, 11 erwartete No-Connects, 0 unerklärte
Abweichungen.** Das bestätigt die Umsetzung von `pinmap.csv`. Die Pinbelegung
selbst stammt aus dem Espressif User Guide v1.1 (Abschnitt 1).

| Pad | DevKit-Pin | Port | pinmap.csv | Netz im Schaltplan | Einstufung |
|---:|---|---|---|---|---|
| 1 | J1-1 | 3V3 | +3V3 | +3V3 | power |
| 2 | J1-2 | 3V3 | +3V3 | +3V3 | power |
| 3 | J1-3 | CHIP_PU | DEVKIT_EN | DEVKIT_EN | signal – **neu** RESET SW502 |
| 4 | J1-4 | GPIO4 | VBAT_SENSE | VBAT_SENSE | signal |
| 5 | J1-5 | GPIO5 | VSERVO_SENSE | VSERVO_SENSE | signal |
| 6 | J1-6 | GPIO6 | IMU_INT1 | IMU_INT1 | signal – **verbunden** (Blatt Sensors_Display) |
| 7 | J1-7 | GPIO7 | SERVO_PWR_EN | SERVO_PWR_EN | signal |
| 8 | J1-8 | GPIO15 | SERVO_FRONT_PWM_3V3 | SERVO_FRONT_PWM_3V3 | signal – **verbunden** (Blatt Actuators) |
| 9 | J1-9 | GPIO16 | SERVO_REAR_PWM_3V3 | SERVO_REAR_PWM_3V3 | signal – **verbunden** (Blatt Actuators) |
| 10 | J1-10 | GPIO17 | SERVO_AUX1_PWM_3V3 | SERVO_AUX1_PWM_3V3 | signal – **verbunden** (Blatt Actuators) |
| 11 | J1-11 | GPIO18 | SPARE_GPIO18 | SPARE_GPIO18 | signal |
| 12 | J1-12 | GPIO8 | I2C_SDA | I2C_SDA | signal – **verbunden** (Blatt Sensors_Display) |
| 13 | J1-13 | GPIO3 | STRAP_GPIO3 | unconnected-(U501-J1-13/GPIO3-Pad13) | expected NC |
| 14 | J1-14 | GPIO46 | STRAP_GPIO46 | unconnected-(U501-J1-14/GPIO46-Pad14) | expected NC |
| 15 | J1-15 | GPIO9 | I2C_SCL | I2C_SCL | signal – **verbunden** (Blatt Sensors_Display) |
| 16 | J1-16 | GPIO10 | ENABLE_BTN_N | ENABLE_BTN_N | signal |
| 17 | J1-17 | GPIO11 | STATUS_LED | STATUS_LED | signal |
| 18 | J1-18 | GPIO12 | BUZZER | BUZZER | signal |
| 19 | J1-19 | GPIO13 | ESC_PWM_3V3 | ESC_PWM_3V3 | signal – **verbunden** (Blatt Actuators) |
| 20 | J1-20 | GPIO14 | SERVO_AUX2_PWM_3V3 | SERVO_AUX2_PWM_3V3 | signal – **verbunden** (Blatt Actuators) |
| 21 | J1-21 | 5V | +5V_DEVKIT | +5V_DEVKIT | power |
| 22 | J1-22 | GND | GND | GND | power |
| 23 | J3-1 | GND | GND | GND | power |
| 24 | J3-2 | GPIO43 | U0TXD | unconnected-(U501-J3-2/TX-Pad24) | expected NC |
| 25 | J3-3 | GPIO44 | U0RXD | unconnected-(U501-J3-3/RX-Pad25) | expected NC |
| 26 | J3-4 | GPIO1 | ISERVO_SENSE | ISERVO_SENSE | signal |
| 27 | J3-5 | GPIO2 | ACT_OE_N | ACT_OE_N | signal |
| 28 | J3-6 | GPIO42 | LED_1_3V3 | LED_1_3V3 | signal – **verbunden** (Blatt Actuators) |
| 29 | J3-7 | GPIO41 | LED_2_3V3 | LED_2_3V3 | signal – **verbunden** (Blatt Actuators) |
| 30 | J3-8 | GPIO40 | LED_3_3V3 | LED_3_3V3 | signal – **verbunden** (Blatt Actuators) |
| 31 | J3-9 | GPIO39 | LED_4_3V3 | LED_4_3V3 | signal – **verbunden** (Blatt Lighting_IO) |
| 32 | J3-10 | GPIO38 | DEVKIT_RGB | unconnected-(U501-J3-10/GPIO38-Pad32) | expected NC |
| 33 | J3-11 | GPIO37 | PSRAM_GPIO37 | unconnected-(U501-J3-11/GPIO37-Pad33) | expected NC |
| 34 | J3-12 | GPIO36 | PSRAM_GPIO36 | unconnected-(U501-J3-12/GPIO36-Pad34) | expected NC |
| 35 | J3-13 | GPIO35 | PSRAM_GPIO35 | unconnected-(U501-J3-13/GPIO35-Pad35) | expected NC |
| 36 | J3-14 | GPIO0 | STRAP_GPIO0 | STRAP_GPIO0 | signal – **neu** BOOT SW503 |
| 37 | J3-15 | GPIO45 | STRAP_GPIO45 | unconnected-(U501-J3-15/GPIO45-Pad37) | expected NC |
| 38 | J3-16 | GPIO48 | EXT_UART_RX | EXT_UART_RX | signal |
| 39 | J3-17 | GPIO47 | EXT_UART_TX | EXT_UART_TX | signal |
| 40 | J3-18 | GPIO21 | IBUS_RX_3V3 | IBUS_RX_3V3 | signal – **verbunden** (Blatt Lighting_IO) |
| 41 | J3-19 | GPIO20 | USB_DP | unconnected-(U501-J3-19/GPIO20-Pad41) | expected NC |
| 42 | J3-20 | GPIO19 | USB_DN | unconnected-(U501-J3-20/GPIO19-Pad42) | expected NC |
| 43 | J3-21 | GND | GND | GND | power |
| 44 | J3-22 | GND | GND | GND | power |

**Globale Labels vom Controller (ERC „Label connected to only one pin": anfangs 16, nach Actuators 8, nach Lighting_IO 3, nach Sensors_Display 0).**
Alle Labels haben jetzt ein echtes Gegenstück; nichts ist ausgeblendet.

| Label | Quelle | Geplantes Gegenstück |
|---|---|---|
| SERVO_FRONT_PWM_3V3 | GPIO15 | Actuators: U201 A-Eingang → J102 |
| SERVO_REAR_PWM_3V3 | GPIO16 | Actuators: U201 → J103 |
| SERVO_AUX1_PWM_3V3 | GPIO17 | Actuators: U201 → J104 |
| SERVO_AUX2_PWM_3V3 | GPIO14 | Actuators: U201 → J105 |
| ESC_PWM_3V3 | GPIO13 | Actuators: U201 → J106 |
| LED_1_3V3 | GPIO42 | Actuators: U201 → LED_1_5V → Lighting_IO J108 |
| LED_2_3V3 | GPIO41 | Actuators: U201 → LED_2_5V → Lighting_IO J109 |
| LED_3_3V3 | GPIO40 | Actuators: U201 → LED_3_5V → Lighting_IO J110 |
| LED_4_3V3 | GPIO39 | Lighting_IO: U202 SN74LVC1T45 → J111 |
| BUZZER | GPIO12 | Lighting_IO: Low-Side-Treiber BZ101 |
| EXT_UART_TX | GPIO47 | Lighting_IO: 1 kΩ → J112 |
| EXT_UART_RX | GPIO48 | Lighting_IO: 4,7 kΩ, ESD, 10 kΩ Pull-up → J112 |
| IBUS_RX_3V3 | GPIO21 | Lighting_IO: U203 SN74LVC1G17 → J107 |
| IMU_INT1 | GPIO6 | Sensors_Display: J115-8, R803 (verbunden) |
| I2C_SDA | GPIO8 | Sensors_Display: J115-5, J116-1, R801 (DNP), TP801 (verbunden) |
| I2C_SCL | GPIO9 | Sensors_Display: J115-4, J116-2, R802 (DNP), TP802 (verbunden) |

## 7. Blatt `Actuators` (Stand 2026-11-15)

Datei `Actuators.kicad_sch` (A3), einmalig erzeugt mit
`hardware/scripts/bootstrap_actuators.py`.

| Ref | Funktion |
|---|---|
| U201 | SN74LVC8T245PWR, VCCA +3V3, VCCB +5V, DIR über R209 an +3V3, OE = `ACT_OE_N` (Pull-up R501 auf Controller) |
| C201, C202 | 100 nF an VCCA bzw. VCCB |
| R201–R205 / R206–R208 | 100k Pull-ups (A1–A5, invertierte Stufe) / Pull-downs (A6–A8, LEDs) |
| R211–R215 / R216–R218 | 100k Gate-Pull-ups nach +5V (B1–B5) / Pull-downs (B6–B8) |
| Q201–Q205, D201–D205, R221–R225, R231–R235, R241–R245 | Open-Drain-Stufe je Steckerausgang: NTR4003N, BAT54 + 2,2 kΩ Pull-up, 470 Ω, 100k (3.1) |
| J102, J103 | Molex Micro-Fit 3.0 43650-0300: 1 Signal, 2 +V_SERVO, 3 GND |
| J104, J105 | Stiftleiste 1×3 2,54 mm: 1 Signal, 2 +V_SERVO, 3 GND (0,5 A) |
| J106 | Stiftleiste 1×3 2,54 mm: 1 ESC-Signal, **2 nicht verbunden (BEC +)**, 3 GND |
| LED_1_5V…LED_3_5V | globale Ausgänge zu Lighting_IO (Steckerschutz dort) |

Netzlistenprüfung (Umsetzung, nicht elektrische Richtigkeit): J102–J106
Pin 1–3 und die U201-Anschlüsse entsprechen dieser Tabelle; 0 Abweichungen.
Unabhängiger Abgleich: KiCad-Symbol SN74LVC8T245 gegen TI SCES584D,
Tab. 4-1 (1 VCCA, 2 DIR, 3–10 A1–A8, 11–13 GND, 14–21 B8–B1, 22 OE, 23/24
VCCB) – stimmt. BAT54-Projektsymbol (1 A, 3 K) gegen Nexperia BAT54 (01.07.2022)
Tab. 2 – stimmt. `scripts/kit verify`: `pin_pad_mapping` ohne Befund.

## 8. Blatt `Lighting_IO` (Stand 2026-11-15)

Datei `Lighting_IO.kicad_sch` (A3), einmalig erzeugt mit
`hardware/scripts/bootstrap_lighting_io.py`. Projektbauteile:
`make_lighting_parts.py` (Symbol TPS2553DBV, Footprint Buzzer).

**Externe 5-V-Ausgänge über strombegrenzte Schalter** (TI TPS2553DBVR,
SLVS841G, Okt. 2026). Ein Kurzschluss im Kabel schaltet nur seine Gruppe ab;
+5V für DevKit und Puffer bleibt stabil (statt Polyfuse, die erst nach einem
Spannungseinbruch auslöst). EN fest an IN, Auto-Retry, FAULT ungenutzt. Die
Grenzen sind aus SLVS841G Gl. 1/3 gerechnet, inklusive Temperatur- und
Prozessstreuung, ohne Widerstandstoleranz (1 %). **U602: EN = P3V3_OK** –
+5V_EXT nur bei gutem +3V3 (O-21):

| Schalter | Ausgang | R_ILIM | I_OS min–max | Last |
|---|---|---|---|---|
| U601 | +5V_LED → J108–J111 | 93,1 kΩ | 0,25–0,32 A | 4 × 44 mA = 0,18 A |
| U602 | +5V_EXT → J112 | 100 kΩ | 0,23–0,30 A | Budget 0,2 A dauernd |
| U603 | +5V_RX → J107 | 150 kΩ | 0,155–0,21 A | ca. 0,1 A (Schätzung, O-10) |

r_DS(on) ≤ 135 mΩ über Temperatur (DBV) → ≤ 27 mV Abfall bei 0,2 A.

| Ref | Funktion |
|---|---|
| U202 | SN74LVC1T45DBVR (SCES515N): LED_4 3,3 → 5 V, DIR über R604 an +3V3, 100k an A und B |
| R607–R610 | 330 Ω in den LED-Datenleitungen: Kurzschluss nach GND ≤ 16 mA; begrenzt den Strom in eine stromlose LED |
| D601–D608 | TPD1E05U06 (SLVSBO7O, ±12 kV Kontakt, V_RWM 5,5 V) am Steckerpin – nur auf Leitungen, deren höchster Gleichpegel +5V ist |
| J108–J111 | JST PH 3-polig: 1 +5V_LED, 2 Daten, 3 GND |
| BZ101, Q601, D605 | Buzzer CMT-8540S an +5V; Low-Side NTR4501N (Rev 16: R_DS(on) ≤ 105 mΩ bei V_GS 2,5 V, 3,2 A); Freilaufdiode PMEG4010CEH (1 A). Fehlerfall Dauer-Ein 0,52 A: Q601 ≈ 28 mW, Diode nur im Abschaltmoment. Gate über R611 100 Ω, Pull-down R612 100k |
| J107, U203 | i-BUS: Stiftleiste (1 Signal, 2 +5V_RX, 3 GND), 2,2 kΩ + 100k Pull-down, SN74LVC1G17 an +3V3 (SCES351Y) |
| J112 | JST PH 4-polig: 1 +5V_EXT, 2 TX über 1 kΩ, 3 RX über 4,7 kΩ mit 10k Pull-up an +3V3 (keine Klemmdiode nach +3V3), 4 GND |
| TP601, TP602 | i-BUS nach U203, LED-1-Daten |

Buzzer-Footprint: Same Sky Datenblatt rev 1.04 (11.09.2024), vier Pads
2,5 × 2,5 mm im Raster 7,0 mm. Draufsicht: „+" unten rechts (Pad 1), „−"
oben rechts (Pad 2). Die Funktion der beiden linken Pads nennt das Datenblatt
nicht. Sie sind als mechanische Pads ohne Netz angelegt; vor der Fertigung am
Bauteil prüfen (O-23).

Netzlistenprüfung (Umsetzung): Stecker, Polarität von Buzzer, Freilaufdiode
und Q601, U202/U203 und die Schalterausgänge entsprechen dieser Tabelle;
34 Anschlüsse geprüft, 0 Abweichungen. Unabhängiger Abgleich der Symbole:
- TPS2553 gegen SLVS841G Tab. 5-1 (1 IN, 2 GND, 3 EN, 4 FAULT, 5 ILIM,
  6 OUT);
- SN74LVC1T45 gegen SCES515N Tab. 4-1;
- 74LVC1G17 (DBV) gegen SCES351Y (1 NC, 2 A, 3 GND, 4 Y, 5 VCC);
- TPD1E05U06 gegen SLVSBO7O Tab. 4-1 (1 I/O, 2 GND);
- NTR4501N gegen NTR4501N/D (1 G, 2 S, 3 D).

Alle stimmen. `pin_pad_mapping` ohne Befund.

## 9. Blatt `Sensors_Display` (Stand 2026-11-15)

Datei `Sensors_Display.kicad_sch` (A4), erzeugt mit
`hardware/scripts/bootstrap_sensors_display.py`, Layout über
`relayout_sheet.py` / `sheet_layouts.py`. Symbole und Footprints der
Modulsockel: `hardware/scripts/make_sensor_module_sockets.py`.

### 9.1 Quellen der Modulpinouts

Ausgewertet wurden die **Original-Eagle-Dateien** (Board und Schaltplan,
XML) aus den Adafruit-Repositories, nicht Fotos:

| Modul | Datei | Stand | Produktseite (2026-11-15) |
|---|---|---|---|
| 4438 LSM6DSOX | `adafruit/Adafruit-LSM6DSOX-PCB`: `Adafruit_LSM6DSOX.brd/.sch` | Commit c05abef (2020-09-07) | 25,6 × 17,8 × 4,6 mm; Revisionen 2022-06-15 (evtl. anderer Regler ≥ 250 mA), 2023-10-27 (nur Silkscreen) |
| 326 OLED 0,96″ | `adafruit/Adafruit-128x64-Monochrome-OLED-PCB`: `Adafruit 0.96in 128x64 OLED STEMMA QT.brd/.sch` | Boarddateien 1031d65 (2020-08-06), XML-Konvertierung 2797692 | ab 2020-08-03 I²C Standard, Auto-Reset, STEMMA QT; 2024-04-02 nur Silkscreen |

**Modulrevision 326:** Verwendet wird nur die STEMMA-QT-Revision (ab
2020-08-03). Ältere 326 stehen ab Werk auf SPI und brauchen den Reset-Pin –
für diesen Carrier nicht zulässig (BOM-Hinweis). Der STEMMA-QT-Anschluss
beider Module bleibt unbenutzt.

### 9.2 Pinout, Geometrie, Orientierung

Draufsicht, Modul mit Bauteilseite nach oben gesteckt (Carrier-Draufsicht =
Modul-Draufsicht, keine Spiegelung). Pin 1 ist auf dem Carrier-Silkscreen mit
Dreieck markiert, die Pinnamen stehen neben den Pads.

| | 4438 (J115) | 326 (J116) |
|---|---|---|
| Platine | 25,40 × 17,78 mm, Ecken R 2,54 | 29,21 × 31,75 mm mit Aussparung 19,05 × 5,08 mm an der Unterkante (Produktseite „26,7 mm" = Hauptteil ohne Eckfahnen) |
| Steckleiste | JP1 1×9, Raster 2,54 mm, an der Unterkante (Y = 2,54) | JP2 1×8, Raster 2,54 mm, an der Oberkante (Y = 29,21), Pin 1 rechts |
| Pins | 1 VIN, 2 3Vo, 3 GND, 4 SCL, 5 SDA, 6 DO, 7 CS, 8 INT1, 9 INT2 | 1 Data, 2 Clk, 3 DC/A0, 4 Rst, 5 CS, 6 3Vo, 7 Vin, 8 GND |
| weitere Reihe | JP2 1×5 (Aux-Bus) bei Y = 15,24, Abstand zu JP1 12,70 mm – **nicht bestücken**, keine Buchse | – |
| Befestigung | 2 × Ø 2,5 mm bei (2,54/15,24) und (22,86/15,24) → 2 Abstandshalter M2,5, Carrier-NPTH 2,7 mm | 4 × Ø 2,5 mm; die zwei Löcher neben der Steckleiste liegen 3,18 mm von Pin 1/8 – ein Abstandshalter kollidiert dort mit dem Buchsenkörper. **Nur die zwei Eckfahnen-Löcher** erhalten Carrier-NPTH |
| Unterseite | nur Lötjumper SJ1 (Adresse) und Silkscreen | Flexkabel des Displays umgeschlagen, Lötpads bei Y ≈ 11 |
| INT1 auf der Steckleiste | ja, JP1-8, direkt vom Sensor (nicht pegelgewandelt) | – |

**Buchsen (Auswahl 2026-11-16):** Samtec **SSW-109-01-T-S** (J115) und
**SSW-108-01-T-S** (J116), einreihig, 2,54 mm, Zinn. Samtec-Zeichnung
SSW-1XX-XX-XXX-X-XX-XXX-XX Rev CJ, Blatt 1:
- Körperhöhe 8,51 mm über der Platine, Körper 2,41 mm breit, Länge N × 2,54 + 0,51 mm;
- Anschluss 0,79 × 0,41 mm, 2,64 mm lang (Bauform -01);
- 4,7 A je Kontakt (nur aus dem DigiKey-Eintrag; Samtec-Seiten am 2026-11-16 mit 429 bzw. 403 abgewiesen).

Samtec nennt keine Leiterplattenbohrung. 1,0 mm im Footprint lässt
0,11 mm zur Diagonale des Anschlusses (0,89 mm); vor der Fertigung prüfen.
Der Buchsenkörper ist im Footprint auf F.Fab eingezeichnet.

**Abstandsprüfung OLED:** Der SSW-108-Körper endet bei X = 25,02 mm (Modulkoordinaten),
der Rand des Modullochs liegt bei 25,42 mm. Ein Abstandshalter (M2,5, Sechskant
ca. 5 mm) passt dort nicht; das bestätigt die Beschränkung auf die Eckfahnen-Löcher.

**Freiraum und Zugänglichkeit (Schätzung):** Abstand Carrier → Modulunterseite
= 8,51 mm Buchse + Kunststoffträger der Modul-Stiftleiste (typ. 2,5 mm, Adafruit
nennt keinen Wert) ≈ 11 mm. Unter beiden Modulen nur flache SMD-Bauteile,
keine Prüfpunkte und keine Bedienelemente. Die Courtyards entsprechen dem
Modulumriss. Lötjumper der Module sind gesteckt nicht erreichbar; benötigt
wird keiner (Werkszustand).

**1:1-Prüfung:** `qa/generated/footprint-print/2026-11-16/sensor_sockets_1to1_A4.pdf`
(A4, Vektor, 50-mm-Maßstab; nicht versioniert). Ausdruck mit 100 %, an echten
Modulen und Buchsen anhalten. Erst danach gelten die Footprints als bestätigt (O-31).

### 9.3 Versorgung, Pegel, Adressen

| | 4438 | 326 |
|---|---|---|
| Versorgung | VIN = +3V3 (DevKit-LDO); Regler AP2112K-3.3 auf dem Modul, Adafruit: VIN 3–5 V | Vin = +3V3; AP2112K-3.3 auf dem Modul, Ladungspumpe im Display |
| I²C-Pegelwandler | BSS138 (Q2) je Leitung, 10 kΩ an VIN (Busseite) und 10 kΩ an 3,3 V (Sensorseite) | gleiche Schaltung (Q2, R3 10 kΩ an Vin) |
| Adresse | **0x6A** (DO über Modulwiderstand nach GND, SJ1 offen); DO auf dem Carrier offen | **0x3D** (DC/A0 über 10 kΩ hoch, SJ3 offen); DC auf dem Carrier offen |
| Weitere Pins | CS mit Modul-Pull-up hoch → I²C-Modus; INT2, 3Vo offen | Rst: Reset-IC APX803 auf dem Modul; CS, 3Vo offen |

**Netze auf den Modulen (aus den Eagle-Schaltplänen, je Widerstandsgatter):**

| Netz | 4438 LSM6DSOX | 326 OLED |
|---|---|---|
| VIN-Netz (`VCC`) = Carrier +3V3 | J1-1; AP2112K IN und EN; Bus-Pull-ups | J2-7; AP2112K IN und EN; Bus-Pull-ups |
| Modul-3,3 V (`3.3V`) = **Ausgang AP2112K** | Sensor VDD/VDDIO, Gates Q2 (BSS138), sensorseitige Pull-ups, J1-2 3Vo | Display VDD/VBAT, Gates Q2, displayseitige Pull-ups, Reset-IC, J2-6 3Vo |
| Busseite SCL/SDA | R3 G$2/G$1 10 kΩ → **VIN** | R3 G$1/G$3 10 kΩ → **VIN** |
| Sensor-/Displayseite | SCL_3V/SDA_3V: R2 G$1/G$2 10 kΩ → **Modul-3,3 V** | D0/D1_3.3V: R3 G$2/G$4 10 kΩ → **Modul-3,3 V** |
| Adresse | SDO: R2 G$4 10 kΩ → GND (0x6A); SJ1 → 3,3 V | DC/SA0: R2 G$2 10 kΩ → Modul-3,3 V (0x3D); SJ3 → GND |
| weitere | CS_3V: R3 G$3 → Modul-3,3 V; LED D1 über R2 G$3 | RST/CS: R2 G$3/G$4 → Modul-3,3 V; BS1: R2 G$1 → GND, SJ2 → 3,3 V; LED über R1 |

Folgerungen:
- **Busseitige Pull-ups:** Am Carrier-Bus wirken nur die Pull-ups an VIN = +3V3.
  Die Pull-ups hinter Q2 liegen an der Modul-3,3 V. Sie belasten den Bus nur,
  solange Q2 leitet, also bei Low (Senkstrom 9.4).
- **Reglerausgang:** Bei VIN = 3,3 V arbeitet der AP2112K im Dropout; die
  Modul-3,3 V liegt wenige mV unter VIN (Schätzung: 250 mV bei 600 mA → ca.
  8 mV bei 20 mA). VDD des LSM6DSOX (max. 3,6 V) und die Gate-Spannung der
  BSS138 (3,3 V, ausreichend über V_th) bleiben eingehalten.
- **Keine Rückspeisung:** VIN, die Bus-Pull-ups und damit beide Modulnetze
  hängen nur an +3V3, der Schiene des ESP32. Über SDA, SCL oder INT1 kann
  deshalb keine Quelle in einen stromlosen ESP32 speisen. INT1 kommt
  ungewandelt aus der Modul-3,3 V (Push-Pull, V_OH = VDDIO − 0,2 V bei 4 mA).

**LSM6DSOX-Datenblatt (O-33, geschlossen 2026-11-16)** – ST DS12814 Rev 4 (Juni 2024),
lokal `components/datasheets/DS_lsm6dsox.pdf` (vom Owner abgelegt, nicht versioniert):

| Punkt | Datenblatt | Folge |
|---|---|---|
| INT1 nach Reset | „Default: input with pull-down“; Fußnote 2: „INT1 must be set to 0 or left unconnected during power-on if the I²C/SPI interfaces are used“ | R803 100 kΩ nach GND erfüllt das; GPIO6 nie treiben |
| INT1-Ausgang | CTRL3_C: PP_OD = 0 (Push-Pull), H_LACTIVE = 0 (aktiv high), INT1_CTRL = 00h (nichts geroutet) | Firmware routet nur die benötigten Ereignisse; Pegel aktiv high |
| Pegel | V_OH = VDDIO − 0,2 V, V_OL ≤ 0,2 V bei 4 mA | ESP32 V_IH 0,75 × VDD erfüllt |
| Strom (Sensor) | 0,55 mA typ. kombiniert High-Performance, 170 µA nur Accel, 3 µA Power-down; Typwerte „not guaranteed“ | Breakout-Strom = Sensor + AP2112K + LED (ca. 0,13 mA); Budget 1,5 mA bleibt Schätzung |
| Versorgung | VDD 1,71–3,6 V, VDDIO 1,62–3,6 V; Einschaltzeit 35 ms | Firmware wartet ≥ 35 ms nach +3V3, bevor sie den Sensor anspricht |
| Adresse | 110101xb, SA0 = 0 → 0x6A | wie 9.3 |

### 9.4 Pull-up-Auslegung (Schätzung)

| Größe | Wert |
|---|---|
| Busseitige Pull-ups | 10 kΩ ∥ 10 kΩ = **5,0 kΩ** an +3V3 (beide Module gesteckt) |
| Anstiegszeit 30→70 % | 0,847 · 5,0 kΩ · 50 pF ≈ **0,21 µs** bei **angenommenen** 50 pF → 400 kHz (≤ 0,3 µs) ist nur **rechnerisch plausibel** |
| Festlegung Firmware | erste Firmware **100 kHz**; 400 kHz erst nach Messung an TP801/TP802 (O-32) |
| nur ein Modul | 10 kΩ → ≈ 0,42 µs → nur Standard Mode (≤ 1 µs) |
| Senkstrom bei Low | je Modul 0,33 mA (Busseite) + 0,33 mA (Sensorseite über BSS138) = 0,66 mA → 1,32 mA gesamt ≪ 3 mA |
| Carrier-Pull-ups | R801/R802 4,7 kΩ **DNP** (Option, wenn ein Modul ohne Pull-ups eingesetzt wird; dann 1,9 kΩ gesamt, 1,7 mA + 1,32 mA) |
| IMU_INT1 | R803 100 kΩ Pull-down **bestückt**: definiert Low ohne IMU und während GPIO6 hochohmig ist; 33 µA Last am Push-Pull-Ausgang |

Messung der Anstiegszeit an TP801/TP802 bleibt offen (O-32).

## 10. RESET und BOOT auf dem Carrier (Blatt `Controller`, Gruppe 6)

Geprüft gegen den Espressif-Schaltplan `SCH_ESP32-S3-DevKitC-1_V1.1_20221130.pdf`,
Blatt 2, als Bild gerendert und abgelesen:

| DevKit | Beschaltung |
|---|---|
| CHIP_PU (EN) | R5 10K(1%) nach ESP_3V3, C6 1uF/16V nach GND, SW2 nach GND (C14 0.1uF „NC"), Header J1-3 direkt |
| GPIO0 | SW1 nach GND (C13 0.1uF „NC"), **kein externer Pull-up**, Header J3-14 direkt |
| Auto-Reset | CP2102N DTR/RTS über R10/R12 10K(1%) an Q1/Q2 L8050QLT1G; Q1-Kollektor über R8 0 Ω an CHIP_PU, Q2-Kollektor über R13 0 Ω an GPIO0 |

Carrier:

- **SW502 `RESET`**: Taster zwischen DEVKIT_EN (J1-3) und GND, parallel zu SW2.
  Kein zusätzlicher Kondensator oder Pull-up – R5/C6 sitzen auf dem DevKit.
  Der Taster entlädt C6 (1 µF, 3,3 V) wie der DevKit-Taster.
- **SW503 `BOOT`**: Taster zwischen STRAP_GPIO0 (J3-14) und GND, parallel zu SW1.
  Kein Pull-up und kein Pull-down auf dem Carrier. Ungedrückt bleibt der
  interne schwache Pull-up wirksam → Strapping 1 = SPI-Boot.
- Beide Taster sind offene Kollektoren/Kontakte nach GND wie die
  Auto-Reset-Transistoren. Sie können parallel betätigt werden.
- Firmware darf GPIO0 nicht als Ausgang treiben (Kurzschluss über SW503).
- **Download-Modus:** BOOT halten, RESET kurz drücken, BOOT loslassen.
- RESET ist **keine Leistungsabschaltung** (Versorgungsdokument 3.15).
- GPIO18 bleibt Reserveeingang, keine weiteren GPIOs belegt.
- Taster TL3342F160QG (wie SW501, Bestand offen, O-28).

## 11. Elektrische Änderungen gegenüber `d53365c`

Ermittelt mit `compare_schematic_revisions.py d53365c` (31 Unterschiede, alle
hier aufgeführt). Alle übrigen Netze und Bauteile sind unverändert.

| Änderung | Netze / Bauteile |
|---|---|
| Neues Blatt `Sensors_Display` (Root-Block bei 190,5/121,92, Seite 8) | J115, J116, R801, R802 (DNP), R803, TP801, TP802 |
| I2C_SDA | vorher nur U501.12 → + J115.5, J116.1, R801.2, TP801.1 |
| I2C_SCL | vorher nur U501.15 → + J115.4, J116.2, R802.1, TP802.1 |
| IMU_INT1 | vorher nur U501.6 → + J115.8, R803.1 |
| +3V3 | + J115.1, J116.7, R801.1, R802.2 |
| GND | + J115.3, J116.8, R803.2, SW502.2, SW503.2 |
| DEVKIT_EN (neu) | U501.3 (vorher No-Connect), SW502.1 |
| STRAP_GPIO0 (neu) | U501.36 (vorher No-Connect), SW503.1 |
| Unbelegte Modulpins | J115.2/6/7/9, J116.3/4/5/6 mit No-Connect |
| Felder | U501 Beschreibung (EN/GPIO0 verbunden) |

## 12. Wiederanlaufsperre (O-35, Stand 2026-11-16)

Anforderung: Nach einem Verlust der LiPo-Versorgung ist eine **erneute bewusste
Freigabe** nötig. Das gilt auch bei weiterlaufendem USB und unverändert hohen
GPIO-Pegeln. Umsetzung in Hardware, Blatt `Controller`, Gruppe 7; Begründung und
Rechnung im Versorgungsdokument 3.16.

| Ref | Funktion |
|---|---|
| U505 TPS3808G01 | VBAT_PROT-Wächter, Schwelle 9,62–10,40 V über R515 237 kΩ / R516 10 kΩ, Filter C506 100 nF; MR an DEVKIT_EN (RESET löscht); versorgt aus +3V3 |
| U506 SN74LVC1G74 | Freigabe-Latch an +3V3: CLR = VBAT_OK über Schmitt-Puffer U508, D = 1, PRE = 1, CLK = Tasterknoten SW501 über Filter C511 und Schmitt-Puffer U507 |
| R405 (ServoPower) | 115 kΩ statt 140 kΩ: RUN-Teiler nur Rückfallebene, damit die Reihenfolge Latch → RUN beweisbar ist (Versorgung 3.16) |
| R518 47 kΩ | trennt GPIO10 vom Takt: Firmware kann den Latch nicht setzen |
| Q407 (ServoPower) | in Reihe zu Q404: RUN nur mit SERVO_PWR_EN **und** ACT_ARMED |
| U204 (Actuators) | U201-OE = ACT_OE_N **oder** ACT_DISARMED |

Bedienung: Nach jedem Anstecken bzw. Einschalten des Akkus, nach jedem
Akkuverlust und nach RESET bleiben Servoschiene und Puffer gesperrt, bis SW501
losgelassen wird; die Ist-Schaltung setzt beim Loslassen.

**Prüfung 2026-11-16:** Die verschärfte Anforderung ist nicht erfüllt. Sie
verlangt: Taster erst bei gültiger Versorgung als losgelassen erkennen, und nur
eine danach begonnene Betätigung gibt frei. Ein über den Fehler gehaltener oder
klemmender Taster setzt den Latch beim späteren Öffnen. Siehe Versorgung 3.16
und 3.17 Punkt 3, O-35. Kandidat K1 ist unzureichend und wird nicht eingebaut. Zustandsmodell: Versorgung 3.18. **Rev1:** Freigabelogik in der Firmware, V2 geparkt; Vorschläge GPIO18 ← ACT_ARMED und Ausgangssperre bei ungültiger +3V3 (O-37): Versorgung 3.20. BOOT allein löscht den Latch nicht. Ein
RESET löscht ihn, auch der RESET beim Download und der Auto-Reset über den
USB-UART. Das gilt auch, wenn die Firmware die Freigabe-GPIOs bereits
auf aktiv gesetzt hat. Der Freigabetaster bleibt zugleich Firmware-Eingang
(GPIO10, ohne interne Pull-ups).

Elektrische Änderungen gegenüber `fea128b` (`compare_schematic_revisions.py`,
45 Unterschiede: die 43 hier aufgeführten elektrischen plus die Felder MPN/Beschreibung von J115/J116; übrige Netze unverändert):

| Änderung | Netze / Bauteile |
|---|---|
| neu Controller | U505, U506, R515–R518, C506–C508; Netze VBAT_LOSS_SENSE, VBAT_OK, ENABLE_BTN_RAW, ACT_ARMED, ACT_DISARMED (global) |
| ENABLE_BTN_N | vorher R502.2, SW501.1, U501.16 → jetzt R518.2, U501.16; SW501.1 und R502.2 am neuen Netz ENABLE_BTN_RAW |
| VBAT_PROT | + R515.1 |
| neu ServoPower | Q407, R420; Q404.2 (Source) vorher GND, jetzt SERVO_EN_SRC → Q407.3 |
| neu Actuators | U204, C203; U201.22 (OE) vorher ACT_OE_N, jetzt ACT_OE_GATED_N ← U204.4; ACT_OE_N → U204.2 |
| +3V3 / GND | neue Versorgungs- und Massepins der genannten Bauteile; U505.3 (MR) und U505.4 (CT) offen |

Nachtrag 2026-11-16, Prüfung nach Versorgungsdokument 3.17: Korrekturen gegenüber
`6fc36ff` (`compare_schematic_revisions.py`):
- neu: U507, U508 (SN74LVC1G17), C509–C511; Netze BTN_CLK (U507.4 → U506.1)
  und VBAT_OK_BUF (U508.4 → U506.6);
- ENABLE_BTN_RAW: + C511.1, U507.2 statt U506.1;
- VBAT_OK: U508.2 statt U506.6;
- DEVKIT_EN: + U505.3 (MR, vorher offen);
- Wertänderungen: R405 140k → 115k, C506 47n → 100n;
- übrige Netze unverändert.

