/*
 * Board I/O of the RoverCore carrier on the ESP32-S3-DevKitC-1 N16R8 v1.1 (ESP-IDF). The only place that touches
 * GPIO / ADC registers; the application (firmware/app) sees sv_inputs_t / sv_outputs_t only.
 * Pins: rovercore_pins.h, generated from hardware/interfaces/pinmap.csv.
 */
#ifndef ROVERCORE_BOARD_IO_H
#define ROVERCORE_BOARD_IO_H

#include <stdbool.h>
#include <stdint.h>

#include "supervisor.h"

typedef struct {
    bool bench_pulls;      /* bare DevKit without carrier: internal pull-up on GPIO10, pull-down on GPIO18 */
    bool bench_supply;     /* bare DevKit: VBAT reported as 12.0 V (only allowed with actuators not permitted) */
} bio_config_t;

/* First call at start-up: drives the locked output levels (SERVO_PWR_EN low, ACT_OE_N high, LED/buzzer off),
 * leaves every pulse line (GPIO13-17), LED data line (GPIO39-42), IMU_INT1 and the UART/I2C pins in their
 * reset Hi-Z state, configures the inputs without internal pulls (unless bench_pulls) and the ADC.
 * Returns 0 or an ESP-IDF error code. Outputs are set even if the ADC set-up fails. */
int bio_safe_init(const bio_config_t *cfg);

/* Reads button, ACT_ARMED level and edge flag, and the three analog values (scaled with sense.h). */
void bio_read(sv_inputs_t *in);

/* Applies SERVO_PWR_EN and ACT_OE_N. */
void bio_apply(const sv_outputs_t *o);

void bio_status_led(bool on);
uint32_t bio_now_ms(void);
const char *bio_reset_reason(void);

#endif
