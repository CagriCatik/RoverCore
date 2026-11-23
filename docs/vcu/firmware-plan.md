# Firmware-Plan RoverCore VCU (ESP32-S3-DevKitC-1 N16R8 v1.1)

Stand 2026-11-23, Stufe 1 von 5. Ziel: Firmware ohne Antrieb in Betrieb nehmen.
Alle Zahlen zu Schwellen und Skalierungen sind **Schätzungen aus Nennwerten**
und ersetzen keine Messung auf dem aufgebauten Carrier.

## Stufen

| Stufe | Inhalt | Stand |
|---|---|---|
| 1 | ESP-IDF-Projekt, Pinmap → Header, sichere GPIO-Zustände beim Start, Freigabe-Zustandsmaschine angebunden, `ACT_ARMED_FB` (Pegel + Flanken-Interrupt), Task-Watchdog, Versorgungsüberwachung, Status-LED, serielle Messwertausgabe | Code und Hosttests fertig; **Zielbuild noch nicht ausgeführt** (ESP-IDF lokal nicht installiert) |
| 2 | Buzzer-Muster, Fehlerprotokoll, ADC-Plausibilisierung VSERVO/ISERVO gegen Freigabezustand | offen |
| 3 | IMU (I2C, `IMU_INT1` nur Eingang), OLED, iBUS-Empfänger auf GPIO21 | offen |
| 4 | Servo-/ESC-PWM (LEDC/MCPWM) mit Invertierung für die Open-Drain-Stufen Q20x, Begrenzungen, RC-Ausfallverhalten | offen |
| 5 | Adressierbare LEDs GPIO39–42 (RMT) | offen |

## Aufbau

- `firmware/app/` (plattformunabhängig, Hosttests):
  - `enable_fsm.c/.h` – bestehende Freigabe-Zustandsmaschine, **unverändert** übernommen.
  - `supervisor.c/.h` – bindet die Zustandsmaschine ein: Versorgung, Abtastlücke, `ACT_ARMED`-Flanke, Ausgangssperre.
  - `diag.c/.h` – Status-LED-Muster und Diagnosezeile.
  - `sense.h` – Skalierung der ADC-Pinspannungen (Nennwerte).
- `firmware/bsp/esp32s3/` (einzige Stelle mit GPIO-/ADC-Zugriff):
  - `rovercore_pins.h` – erzeugt von `firmware/tools/gen_pins.py` aus `hardware/interfaces/pinmap.csv`, nie von Hand ändern.
  - `board_io.c/.h` – sicherer Start, Eingänge lesen, Ausgänge setzen.
- `firmware/esp32/` – ESP-IDF-Projekt (`main/main.c`, `Kconfig.projbuild`, `sdkconfig.defaults`).

## Sicherheitsregeln Stufe 1

1. **Erster Schritt** in `app_main`: `bio_safe_init()` setzt `SERVO_PWR_EN` (GPIO7) = 0, `ACT_OE_N` (GPIO2) = 1, LED und Buzzer aus.
   Pegel wird vor der Richtungsumschaltung gesetzt, damit kein Glitch entsteht.
2. PWM-Leitungen GPIO13–17 und LED-Daten GPIO39–42 bleiben im Reset-Zustand Hi-Z (keine Pulse, U201 gesperrt).
   GPIO6 (`IMU_INT1`, Strap) wird nie getrieben.
3. **Aktoren gesperrt:** Die Ausgänge werden nur freigegeben, wenn alle Bedingungen erfüllt sind:
   - `CONFIG_ROVERCORE_ACTUATORS_PERMITTED=y` (Standard **n**, in Stufe 1 nicht setzen);
   - die Zustandsmaschine ist in S2;
   - kein Versorgungs- und kein Abtastfehler liegt an.

   Ohne die Option zeigt die LED in S2 einen Doppelblitz; die Ausgänge bleiben gesperrt.
4. **Kein automatisches Wiederfreigeben:** Nach jedem Fehler fällt die Zustandsmaschine auf S0 zurück. Freigeben kann danach nur eine neue, vollständige Tastersequenz. Fehlerursachen:
   - Versorgung zu niedrig oder Messung fehlt;
   - Abtastlücke ≥ 12 ms;
   - fallende Flanke an `ACT_ARMED_FB`, auch eine kurze zwischen zwei Abtastungen (Interrupt);
   - Watchdog-Reset.
5. **Versorgung (Vorschlag):**
   - Fehler unter 10,5 V, Warnung unter 10,8 V, Hysterese 200 mV.
   - Gefiltert wird exponentiell mit Shift 3; ein einzelner niedriger Messwert sperrt aber sofort.
   - Nach dem Start gilt die Versorgung als schlecht, bis 10,7 V gefiltert erreicht sind.
6. **Zeitverhalten:**
   - Steuertask alle 5 ms auf Core 1, beim Task-Watchdog angemeldet (1 s, Panic → Reset).
   - Brown-out-Detektor aktiv, FreeRTOS-Tick 1 kHz.

## Kconfig (Menü „RoverCore VCU")

| Option | Standard | Zweck |
|---|---|---|
| `ROVERCORE_ACTUATORS_PERMITTED` | n | Ausgänge dürfen nach gültiger Sequenz freigeben. Erst nach Carrier-Messungen setzen. |
| `ROVERCORE_BENCH_DEVKIT_ONLY` | n | Nacktes DevKit: interne Pull-ups/-downs an GPIO10/18, VBAT fest 12,0 V. Nur ohne Aktor-Option wählbar; Diagnosezeile endet mit `BENCH`. **Nie auf dem Carrier.** |
| `ROVERCORE_DIAG_PERIOD_MS` | 500 | Abstand der Diagnosezeilen |

Diagnosezeile (115200 Bd, UART0 über USB-UART-Brücke):
```
RC t=<ms> st=<S0|S1|PR|PV|S2> en= pwr= oe_n= btn= arm= vbat=<mV|-> vfilt= vsv= isv= flt=0x latch=0x gapmax= gaps= act=
```

## Testebenen

### A. Hosttests (automatisch, ohne Hardware)

`.venv/bin/python -m unittest discover -s qa/tests -t qa/tests`

| Test | Prüft |
|---|---|
| `test_firmware_enable_fsm.py` | Sequenzen der Zustandsmaschine, U505/U506-Modell, Abtastintervalle |
| `test_firmware_supervisor.py` | Ausgangssperre ohne Kconfig-Freigabe, Freigabe nur mit Option, Versorgungsfehler ohne Auto-Wiederfreigabe, Hysterese/Warnung, fehlende Messung, Abtastlücke 12 ms, `ACT_ARMED`-Flanke, Diagnosezeile, Skalierung, LED-Muster; Header-Parität `gen_pins.py --check` |

Mutationsprobe (2026-11-23, manuell): Folgende vier Mutationen wurden von den Tests erkannt:
- Freigabe-Gate entfernt;
- Flanke ignoriert;
- `>` statt `>=` bei der Lücke;
- Start mit „Versorgung gut".

### B. DevKit-Tests (nacktes ESP32-S3-DevKitC-1, ohne Carrier, ohne Antrieb)

Voraussetzung: ESP-IDF v5.x, `idf.py set-target esp32s3 build`; dafür `CONFIG_ROVERCORE_BENCH_DEVKIT_ONLY=y` setzen.

| # | Test | Erwartung |
|---|---|---|
| B1 | Build ohne Warnungen, Flash, Boot-Log | Resetgrund und `actuators permitted: 0` werden ausgegeben |
| B2 | Pegel nach Reset messen (Multimeter/Logikanalysator) | GPIO7 = 0 V, GPIO2 = 3,3 V, GPIO13–17/39–42 hochohmig |
| B3 | GPIO10 kurz gegen GND (≥ 50 ms), dann loslassen; GPIO18 per Draht auf 3,3 V | `st` S0 → S1 → PR → PV → S2; `pwr=0 oe_n=1`; LED zeigt Doppelblitz |
| B4 | GPIO18 in S2 kurz auf GND tippen | `st=S0`, `latch` enthält 0x4, kein Wiederfreigeben ohne neue Sequenz |
| B5 | Steuertask künstlich blockieren (Testbuild) | Reset durch den Task-Watchdog nach ca. 1 s; Resetgrund `task watchdog`; danach S0 |
| B6 | Diagnosezeile 10 min mitschreiben | `gaps=0`, `gapmax` < 12 ms |
| B7 | ADC-Pins mit Labornetzteil 0–2,5 V | Skalierte Werte plausibel (Rohabgleich, keine Kalibrierung) |

### C. Carrier-Messungen (erst am aufgebauten Carrier, später)

Diese Punkte lassen sich nicht auf dem Host oder dem nackten DevKit prüfen:

- **C1 ADC-Kalibrierung:** VBAT, VSERVO und ISERVO gegen Referenzmessgerät. Die Teilerfaktoren 7,0, 147/47 und 0,2 V/A sind Nennwerte.
- **C2 Schwellen:** Versorgungsschwellen 10,5/10,8 V mit dem Labornetzteil anfahren, Reaktionszeit messen.
- **C3 Reale Abschaltzeiten:** von der fallenden Flanke an `ACT_ARMED_FB` bzw. dem Versorgungseinbruch bis `SERVO_PWR_EN` = 0, bis die Servoschiene abgefallen ist und bis U201 gesperrt ist.
- **C4 Hardware-Rückfallebene:** U505/U506 ohne Firmware-Mitwirkung (ESP in Reset).
- **C5 Reglerverhalten:** LTC7803 beim Freigeben und Sperren, Überschwingen, Laststufen.
- **C6 ESC-/Servo-Reaktionen:** erst Stufe 4. Polarität nach der Invertierung, Failsafe bei RC-Ausfall, Begrenzungen; zuerst ohne Antrieb bzw. mit abgenommenem Rad.
- **C7 Erst danach** `ROVERCORE_ACTUATORS_PERMITTED=y`, nach dokumentierter Freigabe durch den Owner.
