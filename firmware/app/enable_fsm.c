/* Enable state machine, see enable_fsm.h. */
#include "enable_fsm.h"

static uint32_t elapsed(uint32_t now, uint32_t since) { return (uint32_t)(now - since); } /* wrap-safe */

static void enter(en_fsm_t *f, en_state_t s, uint32_t now_ms)
{
    f->state = s;
    f->state_since = now_ms;
    f->hw_seen = false;
}

void en_fsm_init(en_fsm_t *f, uint32_t now_ms)
{
    f->deb_pressed = true;
    f->raw_last = true;
    f->raw_since = now_ms;
    f->deb_since = now_ms;
    enter(f, EN_S0_WAIT_RELEASE, now_ms);
}

void en_fsm_fault(en_fsm_t *f, uint32_t now_ms) { enter(f, EN_S0_WAIT_RELEASE, now_ms); }

static void debounce(en_fsm_t *f, uint32_t now_ms, bool raw)
{
    if (raw != f->raw_last) {
        f->raw_last = raw;
        f->raw_since = now_ms;
    }
    if (raw != f->deb_pressed && elapsed(now_ms, f->raw_since) >= EN_FSM_DEBOUNCE_MS) {
        f->deb_pressed = raw;
        f->deb_since = now_ms;
    }
}

bool en_fsm_step(en_fsm_t *f, uint32_t now_ms, const en_inputs_t *in)
{
    debounce(f, now_ms, in->button_pressed);

    if (!in->supply_ok) {
        /* keep re-entering S0: the release time starts only once the supply is good again */
        enter(f, EN_S0_WAIT_RELEASE, now_ms);
        return false;
    }

    switch (f->state) {
    case EN_S0_WAIT_RELEASE:
        /* released time counts from the later of: debounced release, entry into S0 */
        if (!f->deb_pressed) {
            uint32_t since = elapsed(now_ms, f->deb_since) < elapsed(now_ms, f->state_since) ? f->deb_since
                                                                                              : f->state_since;
            if (elapsed(now_ms, since) >= EN_FSM_T_LOS_MS) enter(f, EN_S1_READY, now_ms);
        }
        break;
    case EN_S1_READY:
        if (f->deb_pressed) enter(f, EN_PRESSING, f->deb_since);
        break;
    case EN_PRESSING:
        if (!f->deb_pressed) enter(f, EN_S0_WAIT_RELEASE, now_ms); /* aborted press */
        else if (elapsed(now_ms, f->state_since) >= EN_FSM_T_EIN_MS) enter(f, EN_PRESS_VALID, now_ms);
        break;
    case EN_PRESS_VALID:
        if (!f->deb_pressed) enter(f, EN_S2_ENABLED, now_ms); /* final release */
        break;
    case EN_S2_ENABLED:
        if (in->act_armed) {
            f->hw_seen = true;
        } else if (f->hw_seen || elapsed(now_ms, f->state_since) >= EN_FSM_HW_CONFIRM_MS) {
            enter(f, EN_S0_WAIT_RELEASE, now_ms); /* hardware cleared or never armed */
        }
        break;
    }
    return f->state == EN_S2_ENABLED && in->act_armed;
}
