/*
 * Scaling of the analog measurements from ADC pin millivolts - target-independent.
 * Nominal values from the board (RoverCore.kicad_pcb / schematic), ESTIMATES until calibrated on the carrier:
 *  - VBAT_SENSE  (GPIO4): R505 120k / R506 20k  -> factor 140/20 = 7.0; R507 10k series, C504 1 nF.
 *    The divider is switched by Q505 only while P3V3_OK; its R_DS(on) and leakage are not included.
 *  - VSERVO_SENSE (GPIO5): R410 100k / R411 47k -> factor 147/47; R417 10k series; Q405 switch not included.
 *  - ISERVO_SENSE (GPIO1): INA240A3 (gain 100) on RS402 2 mOhm -> 0.2 V/A, REF at GND (no negative current).
 */
#ifndef ROVERCORE_SENSE_H
#define ROVERCORE_SENSE_H

#include <stdint.h>

static inline uint32_t sense_vbat_mv(uint32_t pin_mv) { return pin_mv * 7u; }

static inline uint32_t sense_vservo_mv(uint32_t pin_mv) { return (pin_mv * 147u + 23u) / 47u; }

static inline int32_t sense_iservo_ma(uint32_t pin_mv) { return (int32_t)(pin_mv * 5u); } /* mV / 0.2 V/A */

#endif
