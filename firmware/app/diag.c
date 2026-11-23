/* Diagnostic line, see diag.h. */
#include "diag.h"

#include <stdio.h>

const char *diag_state_name(en_state_t s)
{
    switch (s) {
    case EN_S0_WAIT_RELEASE: return "S0";
    case EN_S1_READY: return "S1";
    case EN_PRESSING: return "PR";
    case EN_PRESS_VALID: return "PV";
    case EN_S2_ENABLED: return "S2";
    }
    return "??";
}

bool diag_led(const sv_outputs_t *o, bool actuators_permitted, uint32_t now_ms)
{
    uint32_t ph = now_ms % 1000u;
    if (o->faults & (SV_FAULT_SUPPLY_LOW | SV_FAULT_SAMPLE_GAP)) return (now_ms % 200u) < 100u;
    switch (o->state) {
    case EN_S0_WAIT_RELEASE: return ph < 100u;
    case EN_S1_READY: return (now_ms % 500u) < 250u;
    case EN_PRESSING:
    case EN_PRESS_VALID: return true;
    case EN_S2_ENABLED:
        if (actuators_permitted && o->servo_pwr_en) return true;
        return ph < 100u || (ph >= 200u && ph < 300u);
    }
    return false;
}

int diag_format(char *buf, size_t len, uint32_t now_ms, const supervisor_t *s, const sv_inputs_t *in,
                const sv_outputs_t *o)
{
    char vbat[12];
    if (in->vbat_valid) {
        snprintf(vbat, sizeof vbat, "%lu", (unsigned long)in->vbat_mv);
    } else {
        snprintf(vbat, sizeof vbat, "-");
    }
    return snprintf(buf, len,
                    "RC t=%lu st=%s en=%d pwr=%d oe_n=%d btn=%d arm=%d vbat=%s vfilt=%lu vsv=%lu isv=%ld "
                    "flt=0x%lx latch=0x%lx gapmax=%lu gaps=%lu act=%d",
                    (unsigned long)now_ms, diag_state_name(o->state), o->fsm_enabled ? 1 : 0, o->servo_pwr_en ? 1 : 0,
                    o->act_oe_n ? 1 : 0, in->button_pressed ? 1 : 0, in->act_armed ? 1 : 0, vbat,
                    (unsigned long)s->vbat_filt_mv, (unsigned long)in->vservo_mv, (long)in->iservo_ma,
                    (unsigned long)o->faults, (unsigned long)s->fault_latch, (unsigned long)s->max_gap_ms,
                    (unsigned long)s->gap_faults, s->cfg.actuators_permitted ? 1 : 0);
}
