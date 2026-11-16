/*
 * Enable (Freigabe) state machine for the RoverCore VCU, Rev1 scope (O-35).
 *
 * Target-independent application logic: no HAL, no RTOS, no global state.
 * Requirement source: docs/vcu/rev1-versorgung-und-boardwahl.md 3.18 and 3.20.
 *
 *   S0 wait for release --(released >= T_LOS)--> S1 ready
 *   S1 ready            --(pressed)-----------> PRESSING
 *   PRESSING            --(released < T_EIN)--> S0 (aborted press)
 *   PRESSING            --(pressed >= T_EIN)--> PRESS_VALID
 *   PRESS_VALID         --(released)----------> S2 enabled (final release)
 *   S2                  --(ACT_ARMED fell)----> S0
 *   any                 --(supply fault)------> S0
 *
 * Button input is debounced first (stable for EN_FSM_DEBOUNCE_MS). The
 * effective output is enabled only in S2 AND while ACT_ARMED (hardware latch
 * U506 read back on GPIO18) is high AND the supply is good. ACT_ARMED low only
 * blocks the outputs while the sequence runs; a fall of ACT_ARMED after it was
 * seen high in S2 clears the enable; a later high alone never restores it.
 *
 * The caller must call en_fsm_step() with a worst-case interval below
 * EN_FSM_MAX_SAMPLE_GAP_MS (hardware guarantees ACT_ARMED stays low for at
 * least the U505 delay tD min = 12 ms after every clear). This is a software
 * property the integration has to prove (blocking calls, other tasks).
 *
 * No claim of independence from faulty firmware is made (Rev1 decision).
 */
#ifndef ROVERCORE_ENABLE_FSM_H
#define ROVERCORE_ENABLE_FSM_H

#include <stdbool.h>
#include <stdint.h>

#define EN_FSM_DEBOUNCE_MS 10u        /* raw button must be stable this long */
#define EN_FSM_T_LOS_MS 100u          /* release before a new press (band 50-200 ms incl. debounce) */
#define EN_FSM_T_EIN_MS 50u           /* press duration (band 20-100 ms incl. debounce) */
#define EN_FSM_HW_CONFIRM_MS 20u      /* ACT_ARMED must be seen high this soon after the final release */
#define EN_FSM_MAX_SAMPLE_GAP_MS 12u  /* exclusive upper bound for the step interval (U505 tD min) */

typedef enum {
    EN_S0_WAIT_RELEASE = 0,
    EN_S1_READY,
    EN_PRESSING,
    EN_PRESS_VALID,
    EN_S2_ENABLED
} en_state_t;

typedef struct {
    bool button_pressed; /* raw GPIO10 level interpreted as pressed (active low on the pin) */
    bool act_armed;      /* GPIO18 = ACT_ARMED_FB */
    bool supply_ok;      /* firmware view: VBAT_SENSE above limit, no brown-out, no detected fault */
} en_inputs_t;

typedef struct {
    en_state_t state;
    bool deb_pressed;      /* debounced button state */
    bool raw_last;
    uint32_t raw_since;    /* time of the last raw change */
    uint32_t deb_since;    /* time of the last debounced change */
    uint32_t state_since;  /* time of the last state change */
    bool hw_seen;          /* ACT_ARMED seen high since entering S2 */
} en_fsm_t;

/* Start in S0 with the button assumed pressed: a release has to be observed. */
void en_fsm_init(en_fsm_t *f, uint32_t now_ms);

/* Advance the machine; returns true if the effective outputs may be enabled. */
bool en_fsm_step(en_fsm_t *f, uint32_t now_ms, const en_inputs_t *in);

/* Immediate clear, e.g. from the fault handler or after a watchdog reset. */
void en_fsm_fault(en_fsm_t *f, uint32_t now_ms);

#endif
