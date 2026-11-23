/*
 * Diagnostic line for the serial console - target-independent (snprintf only).
 * One line per call, key=value, stable field order, so it can be logged and parsed on the host:
 *   RC t=<ms> st=<S0|S1|PR|PV|S2> en=<0|1> pwr=<0|1> oe_n=<0|1> btn=<0|1> arm=<0|1> vbat=<mV|-> vfilt=<mV>
 *      vsv=<mV> isv=<mA> flt=0x<hex> latch=0x<hex> gapmax=<ms> gaps=<n> act=<0|1>
 * act = actuators permitted by the build. Values are raw-scaled estimates (nominal dividers), not calibrated.
 */
#ifndef ROVERCORE_DIAG_H
#define ROVERCORE_DIAG_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "supervisor.h"

const char *diag_state_name(en_state_t s);

/* Status LED (GPIO11, D502) level for time now_ms:
 *   supply fault or sampling-gap fault: 5 Hz blink;  S0: 1 Hz short flash;  S1: 2 Hz blink;
 *   press in progress (PR/PV): on;  S2 with outputs locked by the build: double flash every second;
 *   S2 with outputs enabled: on. */
bool diag_led(const sv_outputs_t *o, bool actuators_permitted, uint32_t now_ms);

/* Returns the number of characters written (without the terminating zero), like snprintf. */
int diag_format(char *buf, size_t len, uint32_t now_ms, const supervisor_t *s, const sv_inputs_t *in,
                const sv_outputs_t *o);

#endif
