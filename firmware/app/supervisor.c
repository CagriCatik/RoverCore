/* Supervisor around enable_fsm, see supervisor.h. */
#include "supervisor.h"

sv_outputs_t sv_locked_outputs(void)
{
    sv_outputs_t o = {false, true, false, EN_S0_WAIT_RELEASE, 0u};
    return o;
}

void sv_init(supervisor_t *s, const sv_config_t *cfg, uint32_t now_ms)
{
    s->cfg = *cfg;
    en_fsm_init(&s->fsm, now_ms);
    s->started = false;
    s->last_step_ms = now_ms;
    s->max_gap_ms = 0;
    s->gap_faults = 0;
    s->vbat_filt_mv = 0;
    s->supply_low = true;   /* the supply is only good after it has been measured good */
    s->fault_latch = 0;
}

static bool supply_good(supervisor_t *s, const sv_inputs_t *in, uint32_t *flags)
{
    if (!in->vbat_valid) {
        s->supply_low = true;
        *flags |= SV_FAULT_SUPPLY_LOW;
        return false;
    }
    if (s->vbat_filt_mv == 0u) {
        s->vbat_filt_mv = in->vbat_mv;          /* first valid sample seeds the filter */
    } else {
        int32_t d = (int32_t)in->vbat_mv - (int32_t)s->vbat_filt_mv;
        s->vbat_filt_mv = (uint32_t)((int32_t)s->vbat_filt_mv + d / (1 << s->cfg.vbat_filter_shift));
    }
    /* an instantaneous sample below the error threshold counts at once (fault has priority, R1) */
    uint32_t v = in->vbat_mv < s->vbat_filt_mv ? in->vbat_mv : s->vbat_filt_mv;
    if (v < s->cfg.vbat_error_mv) {
        s->supply_low = true;
    } else if (s->vbat_filt_mv >= s->cfg.vbat_error_mv + s->cfg.vbat_hyst_mv) {
        s->supply_low = false;
    }
    if (s->supply_low) *flags |= SV_FAULT_SUPPLY_LOW;
    if (s->vbat_filt_mv < s->cfg.vbat_warn_mv) *flags |= SV_WARN_SUPPLY;
    return !s->supply_low;
}

sv_outputs_t sv_step(supervisor_t *s, uint32_t now_ms, const sv_inputs_t *in)
{
    uint32_t flags = 0;
    if (s->started) {
        uint32_t gap = (uint32_t)(now_ms - s->last_step_ms);
        if (gap > s->max_gap_ms) s->max_gap_ms = gap;
        if (gap >= EN_FSM_MAX_SAMPLE_GAP_MS) {
            /* a clear of ACT_ARMED could have been missed: back to S0 */
            flags |= SV_FAULT_SAMPLE_GAP;
            s->gap_faults++;
            en_fsm_fault(&s->fsm, now_ms);
        }
    }
    s->started = true;
    s->last_step_ms = now_ms;

    bool good = supply_good(s, in, &flags);
    en_state_t before = s->fsm.state;
    en_inputs_t fi = {in->button_pressed, in->act_armed && !in->act_armed_fell, good};
    bool enabled = en_fsm_step(&s->fsm, now_ms, &fi);
    if (in->act_armed_fell && before == EN_S2_ENABLED) flags |= SV_FAULT_ARMED_FELL;

    s->fault_latch |= flags;
    sv_outputs_t o = sv_locked_outputs();
    o.fsm_enabled = enabled;
    o.state = s->fsm.state;
    o.faults = flags;
    if (enabled && s->cfg.actuators_permitted && !(flags & (SV_FAULT_SUPPLY_LOW | SV_FAULT_SAMPLE_GAP))) {
        o.servo_pwr_en = true;
        o.act_oe_n = false;
    }
    return o;
}
