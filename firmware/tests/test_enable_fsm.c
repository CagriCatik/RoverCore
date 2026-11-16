/*
 * Host sequence tests for firmware/app/enable_fsm.c (O-35 Rev1, docs/vcu 3.20).
 *
 * A 1 ms hardware model runs next to the firmware, which is sampled every P ms:
 *  - U505: CLR active while VBAT is low and for TD ms after it returns (tD min 12 ms).
 *  - U506: cleared while CLR is active; set by a release edge of the button node.
 *  - effective output = last firmware output AND the current latch state.
 * The model ignores the 1 ms RC filter and Schmitt delay of the button node.
 *
 * Build and run (host):  cc -std=c99 -Wall -Wextra -Werror -I firmware/app \
 *     firmware/app/enable_fsm.c firmware/tests/test_enable_fsm.c -o /tmp/t && /tmp/t
 */
#include <stdio.h>
#include <stdlib.h>
#include "enable_fsm.h"

static int failures;
#define CHECK(c, msg) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, msg); failures++; } } while (0)

typedef struct {
    uint32_t t, period, phase;
    uint32_t td;              /* U505 delay used by the model */
    bool vbat_ok, fw_sees_vbat;
    uint32_t vbat_ok_since;
    bool pressed, latch;
    bool fw_out;              /* firmware output (held between samples) */
    bool effective;
    bool ever_effective;
    en_fsm_t fsm;
} sim_t;

static void sim_init(sim_t *s, uint32_t t0, uint32_t period, uint32_t phase, bool pressed)
{
    s->t = t0; s->period = period; s->phase = phase; s->td = 12;
    s->vbat_ok = true; s->fw_sees_vbat = true; s->vbat_ok_since = t0 - 1000u;
    s->pressed = pressed; s->latch = false; s->fw_out = false; s->effective = false; s->ever_effective = false;
    en_fsm_init(&s->fsm, t0);
}

static bool clr_active(const sim_t *s) { return !s->vbat_ok || (uint32_t)(s->t - s->vbat_ok_since) < s->td; }

/* advance 1 ms of hardware; sample the firmware every `period` ms */
static void tick(sim_t *s)
{
    if (clr_active(s)) s->latch = false;
    if ((s->t % s->period) == s->phase) {
        en_inputs_t in = { s->pressed, s->latch, s->vbat_ok || !s->fw_sees_vbat };
        s->fw_out = en_fsm_step(&s->fsm, s->t, &in);
    }
    s->effective = s->fw_out && s->latch;
    if (s->effective) s->ever_effective = true;
    s->t++;
}

static void run(sim_t *s, uint32_t ms) { while (ms--) tick(s); }

static void set_button(sim_t *s, bool pressed)
{
    if (s->pressed && !pressed && !clr_active(s)) s->latch = true; /* U506: release edge sets */
    s->pressed = pressed;
}

static void vbat(sim_t *s, bool ok)
{
    if (ok && !s->vbat_ok) s->vbat_ok_since = s->t;
    s->vbat_ok = ok;
}

/* full valid sequence from S0: release, wait, press, release; returns enabled afterwards */
static bool sequence(sim_t *s, uint32_t wait_ms, uint32_t press_ms)
{
    set_button(s, false); run(s, wait_ms);
    set_button(s, true); run(s, press_ms);
    set_button(s, false); run(s, 40);
    return s->effective;
}

static void test_normal(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    run(&s, 150);
    CHECK(s.fsm.state == EN_S1_READY, "released 150 ms -> S1");
    set_button(&s, true); run(&s, 80);
    CHECK(!s.effective, "no enable while still pressed");
    set_button(&s, false); run(&s, 40);
    CHECK(s.effective, "enable after final release");
}

static void test_held_at_boot(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, true);
    run(&s, 500);
    set_button(&s, false); run(&s, 60);   /* release of a button held since boot */
    CHECK(!s.effective, "held at boot: release alone gives no enable");
    CHECK(s.latch, "model: hardware latch is set by that release");
    CHECK(sequence(&s, 150, 80), "new full sequence enables");
}

static void test_release_too_short(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    run(&s, 45);                          /* released only 45 ms (< 50 ms band) */
    set_button(&s, true); run(&s, 80); set_button(&s, false); run(&s, 40);
    CHECK(!s.ever_effective, "release < t_LOS before the press: no enable");
}

static void test_aborted_press(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    run(&s, 150);
    set_button(&s, true); run(&s, 30); set_button(&s, false); run(&s, 20);
    CHECK(s.fsm.state == EN_S0_WAIT_RELEASE, "aborted press -> S0");
    set_button(&s, true); run(&s, 80); set_button(&s, false); run(&s, 40);
    CHECK(!s.ever_effective, "press right after an abort (release < t_LOS): no enable");
    CHECK(sequence(&s, 150, 80), "full sequence after the abort enables");
}

static void test_press_too_short(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    run(&s, 150);
    set_button(&s, true); run(&s, 15); set_button(&s, false); run(&s, 40);
    CHECK(!s.ever_effective, "press of 15 ms (< 20 ms band) never enables");
}

static void test_bounce(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    run(&s, 150);
    for (int i = 0; i < 4; i++) { set_button(&s, i % 2 == 0); run(&s, 2); } /* 8 ms bounce */
    set_button(&s, true); run(&s, 80);
    for (int i = 0; i < 4; i++) { set_button(&s, i % 2 != 0); run(&s, 2); }
    set_button(&s, false); run(&s, 40);
    CHECK(s.effective, "bounce shorter than the debounce time is filtered");
}

static void test_dip_seen_by_firmware(void)
{
    sim_t s; sim_init(&s, 1000, 5, 0, false);
    CHECK(sequence(&s, 150, 80), "enabled");
    set_button(&s, true);                 /* operator holds the button through the fault */
    vbat(&s, false); run(&s, 30); vbat(&s, true); run(&s, 30);
    CHECK(!s.effective, "dip clears the enable");
    set_button(&s, false); run(&s, 60);
    CHECK(!s.effective, "release of the held button does not re-enable");
    CHECK(s.latch, "model: hardware latch was re-set by that release");
    CHECK(sequence(&s, 150, 80), "full sequence needed and sufficient");
}

/* dip the firmware does not see: only ACT_ARMED tells it; operator holds through and
 * releases right after CLR ends (shortest possible ACT_ARMED low phase = tD) */
static bool dip_unseen(uint32_t period, uint32_t phase, uint32_t dip_ms)
{
    sim_t s; sim_init(&s, 1000, period, phase, false);
    s.fw_sees_vbat = false;
    if (!sequence(&s, 150, 80)) return false;
    set_button(&s, true); run(&s, 50);
    vbat(&s, false); run(&s, dip_ms); vbat(&s, true);
    run(&s, s.td);                        /* CLR ends now */
    set_button(&s, false);                /* release immediately: hardware latch sets again */
    s.ever_effective = false;
    run(&s, 200);
    return !s.ever_effective && s.fsm.state != EN_S2_ENABLED;
}

static void test_dip_unseen_polling(void)
{
    for (uint32_t p = 1; p < EN_FSM_MAX_SAMPLE_GAP_MS; p++)
        for (uint32_t ph = 0; ph < p; ph++)
            for (uint32_t d = 0; d <= 3; d++)
                CHECK(dip_unseen(p, ph, d), "sample interval < 12 ms detects every clear");
    int missed = 0;
    for (uint32_t ph = 0; ph < 20; ph++) if (!dip_unseen(20, ph, 0)) missed++;
    CHECK(missed > 0, "a 20 ms interval can miss a clear (requirement is real)");
}

static void test_act_armed_alone_never_restores(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    s.fw_sees_vbat = false;
    CHECK(sequence(&s, 150, 80), "enabled");
    vbat(&s, false); run(&s, 2); vbat(&s, true); run(&s, 40); /* clear, no release yet */
    CHECK(!s.effective && s.fsm.state == EN_S0_WAIT_RELEASE, "clear seen -> S0");
    set_button(&s, true); run(&s, 30); set_button(&s, false); run(&s, 60); /* latch high again */
    CHECK(s.latch && !s.effective, "ACT_ARMED high alone does not restore the enable");
}

static void test_hw_refuses(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    s.fw_sees_vbat = false; s.td = 400;   /* CLR stays active through the whole sequence */
    vbat(&s, false); run(&s, 1); vbat(&s, true);
    sequence(&s, 150, 80);
    CHECK(!s.ever_effective, "no effective output while the latch cannot set");
    run(&s, EN_FSM_HW_CONFIRM_MS + 5);
    CHECK(s.fsm.state == EN_S0_WAIT_RELEASE, "firmware drops S2 if ACT_ARMED never comes");
}

static void test_fault_during_press(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    run(&s, 150);
    set_button(&s, true); run(&s, 30);
    vbat(&s, false); run(&s, 5); vbat(&s, true); run(&s, 100);
    set_button(&s, false); run(&s, 40);
    CHECK(!s.ever_effective, "fault during the press: no enable at release");
}

static void test_release_counted_after_supply_return(void)
{
    sim_t s; sim_init(&s, 1000, 1, 0, false);
    vbat(&s, false); run(&s, 300); vbat(&s, true);  /* button released throughout */
    run(&s, 60);
    CHECK(s.fsm.state == EN_S0_WAIT_RELEASE, "t_LOS restarts when the supply returns");
    run(&s, 60);
    CHECK(s.fsm.state == EN_S1_READY, "S1 after >= 100 ms of good supply");
}

static void test_wraparound(void)
{
    sim_t s; sim_init(&s, 0xFFFFFF00u, 1, 0, false);
    s.vbat_ok_since = 0xFFFFFF00u - 1000u;
    CHECK(sequence(&s, 150, 80), "sequence across the 32-bit wrap");
}

int main(void)
{
    test_normal();
    test_held_at_boot();
    test_release_too_short();
    test_aborted_press();
    test_press_too_short();
    test_bounce();
    test_dip_seen_by_firmware();
    test_dip_unseen_polling();
    test_act_armed_alone_never_restores();
    test_hw_refuses();
    test_fault_during_press();
    test_release_counted_after_supply_return();
    test_wraparound();
    if (failures) { printf("%d failure(s)\n", failures); return EXIT_FAILURE; }
    printf("enable_fsm: all tests passed\n");
    return EXIT_SUCCESS;
}
