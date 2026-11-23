/*
 * Supervisor around the enable state machine (enable_fsm) - target-independent, no HAL, no RTOS.
 *
 * Owns, per control step:
 *  - the firmware supply view (VBAT filtered, error / warning thresholds with hysteresis),
 *  - the sampling-gap check required by enable_fsm.h (largest step interval < EN_FSM_MAX_SAMPLE_GAP_MS),
 *  - the ACT_ARMED fall event from an edge interrupt (so a short clear is never missed between samples),
 *  - the output decision: SERVO_PWR_EN and ACT_OE_N follow the effective enable ONLY when actuators are
 *    permitted by the build (sv_config_t.actuators_permitted). In every other case the outputs stay locked:
 *    SERVO_PWR_EN low, ACT_OE_N high (pulse buffers U201 disabled).
 * There is no automatic re-enable: every fault ends in S0 and a new full button sequence is needed.
 *
 * Thresholds are the proposals of docs/vcu/rev1-versorgung-und-boardwahl.md 3.7 (error 10.5 V, warning 10.8 V),
 * not verified values. Scaling of the measurements is done by the BSP (millivolt / milliampere at the source).
 */
#ifndef ROVERCORE_SUPERVISOR_H
#define ROVERCORE_SUPERVISOR_H

#include <stdbool.h>
#include <stdint.h>

#include "enable_fsm.h"

#define SV_FAULT_SUPPLY_LOW    (1u << 0)  /* VBAT below the error threshold (or not measurable) */
#define SV_FAULT_SAMPLE_GAP    (1u << 1)  /* a step interval reached EN_FSM_MAX_SAMPLE_GAP_MS */
#define SV_FAULT_ARMED_FELL    (1u << 2)  /* ACT_ARMED fell while enabled (hardware latch cleared) */
#define SV_WARN_SUPPLY         (1u << 8)  /* VBAT below the warning threshold */

typedef struct {
    uint32_t vbat_error_mv;     /* below: fault, outputs locked */
    uint32_t vbat_warn_mv;      /* below: warning only */
    uint32_t vbat_hyst_mv;      /* the fault clears only above error + hysteresis */
    uint8_t vbat_filter_shift;  /* exponential filter, alpha = 1 / 2^shift per step */
    bool actuators_permitted;   /* false: outputs never leave the locked state (first firmware stage) */
} sv_config_t;

typedef struct {
    bool vbat_valid;        /* the measurement exists (divider switched on, ADC read ok) */
    uint32_t vbat_mv;
    uint32_t vservo_mv;
    int32_t iservo_ma;
    bool button_pressed;    /* GPIO10 low = pressed */
    bool act_armed;         /* GPIO18 level */
    bool act_armed_fell;    /* a falling edge was seen since the last step (interrupt flag) */
} sv_inputs_t;

typedef struct {
    bool servo_pwr_en;      /* GPIO7, active high */
    bool act_oe_n;          /* GPIO2, high = pulse buffers disabled */
    bool fsm_enabled;       /* enable_fsm says outputs may be enabled (S2 and ACT_ARMED) */
    en_state_t state;
    uint32_t faults;        /* SV_FAULT_* / SV_WARN_* active in this step */
} sv_outputs_t;

typedef struct {
    sv_config_t cfg;
    en_fsm_t fsm;
    bool started;
    uint32_t last_step_ms;
    uint32_t max_gap_ms;        /* since start */
    uint32_t gap_faults;        /* count */
    uint32_t vbat_filt_mv;
    bool supply_low;            /* hysteresis state */
    uint32_t fault_latch;       /* OR of all faults since start (diagnostics only, does not block) */
} supervisor_t;

/* Locked outputs; to be applied by the BSP before anything else at start-up. */
sv_outputs_t sv_locked_outputs(void);

void sv_init(supervisor_t *s, const sv_config_t *cfg, uint32_t now_ms);

/* One control step. Returns the outputs to apply. */
sv_outputs_t sv_step(supervisor_t *s, uint32_t now_ms, const sv_inputs_t *in);

#endif
