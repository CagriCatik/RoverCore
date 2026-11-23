/*
 * Host tests for firmware/app/supervisor.c, diag.c and sense.h (first firmware stage, 2026-11-23).
 * Build: cc -std=c99 -Wall -Wextra -Werror -I firmware/app firmware/app/enable_fsm.c firmware/app/supervisor.c
 *        firmware/app/diag.c firmware/tests/test_supervisor.c
 * The enable sequence itself is covered by test_enable_fsm.c; here: output locking, supply handling,
 * sampling-gap fault, ACT_ARMED edge, no automatic re-enable, diagnostics line, scaling.
 */
#include <stdio.h>
#include <string.h>

#include "diag.h"
#include "sense.h"
#include "supervisor.h"

static int failures;
#define CHECK(c, msg)                                                                          \
    do {                                                                                       \
        if (!(c)) {                                                                            \
            printf("FAIL %s:%d %s\n", __FILE__, __LINE__, msg);                                \
            failures++;                                                                        \
        }                                                                                      \
    } while (0)

static const sv_config_t CFG_LOCKED = {10500u, 10800u, 200u, 3u, false};
static const sv_config_t CFG_ACT = {10500u, 10800u, 200u, 3u, true};

typedef struct {
    supervisor_t s;
    sv_inputs_t in;
    sv_outputs_t o;
    uint32_t t;
} rig_t;

static void rig_init(rig_t *r, const sv_config_t *cfg)
{
    memset(r, 0, sizeof *r);
    sv_init(&r->s, cfg, 0);
    r->in.vbat_valid = true;
    r->in.vbat_mv = 12000;
    r->in.button_pressed = false;
}

/* advance in 5 ms steps; the latch U506 is modelled simply: it sets on the release after a press */
static void run(rig_t *r, uint32_t ms)
{
    for (uint32_t k = 0; k < ms; k += 5) {
        r->t += 5;
        r->o = sv_step(&r->s, r->t, &r->in);
        r->in.act_armed_fell = false;
    }
}

static void enable_sequence(rig_t *r)
{
    run(r, 200);                 /* released >= t_LOS -> S1 */
    r->in.button_pressed = true;
    run(r, 100);                 /* press >= t_EIN */
    r->in.button_pressed = false;
    r->in.act_armed = true;      /* latch sets on the release */
    run(r, 50);
}

static void test_locked_by_default(void)
{
    sv_outputs_t o = sv_locked_outputs();
    CHECK(!o.servo_pwr_en && o.act_oe_n, "locked outputs: SERVO_PWR_EN low, ACT_OE_N high");
    rig_t r;
    rig_init(&r, &CFG_LOCKED);
    enable_sequence(&r);
    CHECK(r.o.fsm_enabled, "fsm reaches S2 with a valid sequence");
    CHECK(!r.o.servo_pwr_en && r.o.act_oe_n, "actuators not permitted: outputs stay locked in S2");
}

static void test_enable_when_permitted(void)
{
    rig_t r;
    rig_init(&r, &CFG_ACT);
    run(&r, 50);
    CHECK(!r.o.servo_pwr_en && r.o.act_oe_n, "locked before the sequence");
    enable_sequence(&r);
    CHECK(r.o.state == EN_S2_ENABLED && r.o.servo_pwr_en && !r.o.act_oe_n, "enabled after the sequence");
}

static void test_supply_fault_no_auto_reenable(void)
{
    rig_t r;
    rig_init(&r, &CFG_ACT);
    enable_sequence(&r);
    r.in.vbat_mv = 10000;        /* below the error threshold */
    run(&r, 5);
    CHECK(!r.o.servo_pwr_en && r.o.act_oe_n && r.o.state == EN_S0_WAIT_RELEASE, "supply low: locked at once, S0");
    CHECK(r.o.faults & SV_FAULT_SUPPLY_LOW, "supply fault flagged");
    r.in.vbat_mv = 12000;
    run(&r, 1000);
    CHECK(!r.o.servo_pwr_en && r.o.state != EN_S2_ENABLED, "no automatic re-enable after the supply recovers");
    enable_sequence(&r);
    CHECK(r.o.servo_pwr_en, "re-enable only with a new full sequence");
}

static void test_supply_hysteresis_and_warning(void)
{
    rig_t r;
    rig_init(&r, &CFG_ACT);
    r.in.vbat_mv = 10600;        /* above error, below error + hysteresis: not good yet at start */
    run(&r, 300);
    CHECK(r.o.faults & SV_FAULT_SUPPLY_LOW, "start in supply-low until error + hysteresis is reached");
    r.in.vbat_mv = 10750;
    run(&r, 300);
    CHECK(!(r.o.faults & SV_FAULT_SUPPLY_LOW) && (r.o.faults & SV_WARN_SUPPLY), "good, but warning below 10.8 V");
    r.in.vbat_valid = false;
    run(&r, 5);
    CHECK(r.o.faults & SV_FAULT_SUPPLY_LOW, "missing VBAT measurement counts as supply fault");
}

static void test_sample_gap(void)
{
    rig_t r;
    rig_init(&r, &CFG_ACT);
    enable_sequence(&r);
    r.t += EN_FSM_MAX_SAMPLE_GAP_MS;  /* one late step */
    r.o = sv_step(&r.s, r.t, &r.in);
    CHECK(r.o.faults & SV_FAULT_SAMPLE_GAP, "gap >= 12 ms flagged");
    CHECK(!r.o.servo_pwr_en && r.o.state == EN_S0_WAIT_RELEASE, "gap fault locks and returns to S0");
    CHECK(r.s.max_gap_ms >= EN_FSM_MAX_SAMPLE_GAP_MS && r.s.gap_faults == 1, "gap statistics");
    run(&r, 500);
    CHECK(!r.o.servo_pwr_en, "no re-enable after a gap fault");
}

static void test_armed_edge(void)
{
    rig_t r;
    rig_init(&r, &CFG_ACT);
    enable_sequence(&r);
    /* a short clear between two samples: the level is high again, only the edge flag tells */
    r.in.act_armed_fell = true;
    run(&r, 5);
    CHECK(r.o.state == EN_S0_WAIT_RELEASE && !r.o.servo_pwr_en, "edge flag alone clears the enable");
    CHECK(r.s.fault_latch & SV_FAULT_ARMED_FELL, "armed-fell recorded");
    run(&r, 500);
    CHECK(!r.o.servo_pwr_en, "ACT_ARMED high again does not restore the enable");
}

static void test_diag_and_scaling(void)
{
    rig_t r;
    rig_init(&r, &CFG_LOCKED);
    run(&r, 10);
    char buf[256];
    int n = diag_format(buf, sizeof buf, r.t, &r.s, &r.in, &r.o);
    CHECK(n > 0 && (size_t)n < sizeof buf, "diag line fits");
    CHECK(strncmp(buf, "RC t=10 st=S0 en=0 pwr=0 oe_n=1", 31) == 0, "diag line prefix");
    CHECK(strstr(buf, " act=0") != NULL, "diag shows actuators not permitted");
    r.in.vbat_valid = false;
    diag_format(buf, sizeof buf, r.t, &r.s, &r.in, &r.o);
    CHECK(strstr(buf, "vbat=- ") != NULL, "missing VBAT shown as -");
    CHECK(sense_vbat_mv(1800) == 12600, "VBAT 1.80 V at the pin = 12.6 V (factor 7.0)");
    CHECK(sense_vservo_mv(2210) == 6912, "VSERVO 2.21 V at the pin = 6.91 V (factor 147/47)");
    CHECK(sense_iservo_ma(2240) == 11200, "ISERVO 2.24 V = 11.2 A (0.2 V/A)");
}

static void test_led(void)
{
    sv_outputs_t o = sv_locked_outputs();
    CHECK(diag_led(&o, false, 50) && !diag_led(&o, false, 500), "S0: short flash once per second");
    o.faults = SV_FAULT_SUPPLY_LOW;
    CHECK(diag_led(&o, false, 50) && !diag_led(&o, false, 150), "fault: 5 Hz");
    o.faults = 0;
    o.state = EN_S2_ENABLED;
    CHECK(diag_led(&o, false, 250) && !diag_led(&o, false, 150) && !diag_led(&o, false, 600),
          "S2 locked by the build: double flash");
    o.servo_pwr_en = true;
    CHECK(diag_led(&o, true, 600), "S2 enabled: steady on");
}

int main(void)
{
    test_locked_by_default();
    test_enable_when_permitted();
    test_supply_fault_no_auto_reenable();
    test_supply_hysteresis_and_warning();
    test_sample_gap();
    test_armed_edge();
    test_diag_and_scaling();
    test_led();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("all tests passed\n");
    return 0;
}
