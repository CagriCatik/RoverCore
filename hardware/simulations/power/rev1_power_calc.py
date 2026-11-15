"""VCU Rev 1 power-stage dimensioning, 3S design basis (estimates only).

Active design: docs/vcu/rev1-versorgung-und-boardwahl.md sections 3-5.
Historical 2S numbers (appendix A of that document): run with --history-2s.

Inputs: LTC7803 Rev A, TPS54302 SLVSDG6C, INA240 SBOS662C, ESP32-S3 DS v2.2,
Savox SW-0231MG+ (CML distributor datasheet), Vishay SMBJ 88392, SiRA99DP.
Every result is an estimate and does not replace measurement.
"""
import sys
from math import sqrt

VBAT = {"min (3.0 V/cell)": 9.0, "fault (3.5 V/cell)": 10.5, "nominal": 11.1, "max": 12.6}
VFB = (0.788, 0.800, 0.812)          # LTC7803 VFB min/typ/max
RFB_TOL = 0.001                      # 0.1 % feedback resistors


def ltc_vout(ra, rb):
    k = rb / ra
    lo = VFB[0] * (1 + k * (1 - RFB_TOL) / (1 + RFB_TOL))
    hi = VFB[2] * (1 + k * (1 + RFB_TOL) / (1 - RFB_TOL))
    return VFB[1] * (1 + k), lo, hi


def active_3s():
    print("== Servo rail setpoint (LTC7803) ==")
    ra, rb = 10.0e3, 75.0e3
    vnom, vlo, vhi = ltc_vout(ra, rb)
    print(f"RA 10.0k / RB 75.0k: {vnom:.3f} V, band {vlo:.3f}..{vhi:.3f} V")
    print(f"OV comparator (VFB +7..13 %): up to {VFB[2]*1.13*(1+rb/ra*(1+RFB_TOL)/(1-RFB_TOL)):.2f} V (fault case only)")

    print("\n== Voltage at the servo connector (JR plug), both steering servos stalled ==")
    # Simplified load estimate only: a stalled digital servo is not a constant resistor.
    r_stall = 6.0 / 4.8                # = 1.250 Ohm; 7.4/5.9 = 1.254 Ohm
    r_common = 2e-3 + 3e-3             # output shunt + common trunk (+ and GND) -> total rail current
    r_branch = {"new": 2e-3 + 20e-3 + 2 * 0.2 * 33.3e-3 + 20e-3,
                "aged": 2e-3 + 40e-3 + 2 * 0.2 * 33.3e-3 + 20e-3}   # PCB branch, Micro-Fit, 20 AWG adapter, JR
    i_res = 2 * 0.5
    for vreg_name, vreg in (("band min", vlo), ("nominal", vnom)):
        for c, rb_ in r_branch.items():
            i_s = 0.0
            for _ in range(60):
                vnode = vreg - (2 * i_s + i_res) * r_common
                i_s = vnode / (rb_ + r_stall)
            print(f"  Vreg {vreg_name} {vreg:.2f} V, {c:4s} contacts (branch {rb_*1e3:.0f} mOhm): "
                  f"rail {2*i_s+i_res:.2f} A, servo {i_s:.2f} A, at plug {vnode - i_s*rb_:.2f} V")
    vnode = vlo - 6.0 * r_common
    print(f"  running 2 x 2.5 A, aged, Vreg min: at plug {vnode - 2.5*r_branch['aged']:.2f} V")
    print(f"  no load: up to {vhi:.2f} V at plug")
    # Load-dump overshoot estimate: dV ~ dI / (2 pi fc C); fc unknown -> assume 10..30 kHz
    co = 2 * 270e-6 + 3 * 22e-6
    for fc in (10e3, 20e3, 30e3):
        print(f"  load step -11 A, fc {fc/1e3:.0f} kHz (assumed): overshoot ~{11/(2*3.1416*fc*co):.2f} V -> {vhi + 11/(2*3.1416*fc*co):.2f} V")

    print("\n== LTC7803 stage at 3S ==")
    vo, i_max_load, f, fmin = vnom, 11.2, 375e3, 340e3
    for L in (2.2e-6, 3.3e-6):
        for vin in (9.0, 12.6):
            dI = vo * (1 - vo / vin) / (f * L)
            dIw = vo * (1 - vo / vin) / (fmin * L * 0.8)
            print(f"  L {L*1e6:.1f} uH, Vin {vin}: dIL nom {dI:.2f} A, worst {dIw:.2f} A")
        dIw = vo * (1 - vo / 12.6) / (fmin * L * 0.8)
        for rs in (3e-3,):
            imin = 0.045 / (rs * 1.01) - dIw / 2
            ipk = 0.055 / (rs * 0.99)
            irms = sqrt(i_max_load**2 + (vo * (1 - vo / 12.6) / (f * L))**2 / 12)
            print(f"    Rs {rs*1e3:.0f} mOhm: Iout,min {imin:.2f} A (load {i_max_load} A), peak limit max {ipk:.1f} A, "
                  f"inductor Irms @11.2 A {irms:.2f} A, dVsense @12.6 V {vo*(1-vo/12.6)/(f*L)*rs*1e3:.1f} mV")
    rds_hot = 3.6e-3 * 1.4
    for vin in (9.0, 12.6):
        d = vo / vin
        print(f"  Vin {vin}: D {d:.2f}, top FET cond {d*i_max_load**2*rds_hot:.2f} W, bottom {(1-d)*i_max_load**2*rds_hot:.2f} W (RDS 3.6 mOhm x1.4)")
    print(f"  shunt 3 mOhm @11.2 A {i_max_load**2*3e-3:.2f} W")
    for vin in (12.6,):
        print(f"  Cin Irms @ {vin} V, 11.2 A: {i_max_load*sqrt(vo*(vin-vo))/vin:.2f} A")
    run_b, run_a = 140e3, 20e3
    print(f"  RUN {run_b/1e3:.0f}k/{run_a/1e3:.0f}k: on {1.2*(1+run_b/run_a):.2f} V ({1.15*(1+run_b/run_a):.2f}..{1.25*(1+run_b/run_a):.2f}), "
          f"off {1.1*(1+run_b/run_a):.2f} V; at 21.5 V {21.5*run_a/(run_a+run_b):.2f} V (abs max 40 V)")
    print(f"  soft-start 33 nF: {33e-9*0.8/12.5e-6*1e3:.1f} ms, charge current {co*vo/(33e-9*0.8/12.5e-6):.2f} A")

    print("\n== TPS54302 5 V at 3S ==")
    vo5, L5 = 0.596 * (1 + 100e3 / 13.7e3), 10e-6  # R3 13.7k since 2026-11-15 (WS2812B abs max 5.3 V)
    dI5 = vo5 * (12.6 - vo5) / (12.6 * L5 * 290e3 * 0.8)
    print(f"  Vout {vo5:.3f} V; dIL worst @12.6 V {dI5:.2f} A, Ipk @2 A {2+dI5/2:.2f} A")
    Ip, Ih, Vf, Vr = 0.7e-6, 1.55e-6, 1.16, 1.23
    R4, R5 = 69.8e3, 11.5e3
    for vs, vp in ((8.6, 8.0),):
        r4 = (vs * (Vf / Vr) - vp) / (Ip * (1 - Vf / Vr) + Ih)
        r5 = r4 * Vf / (vp - Vf + r4 * (Ip + Ih))
        print(f"  EN target {vs}/{vp} V -> R4 {r4/1e3:.1f}k, R5 {r5/1e3:.2f}k (chosen 69.8k/11.5k); EN at 21.5 V ~{21.5*R5/(R4+R5):.2f} V")

    print("\n== Battery input (3S) ==")
    p = vo * 11.2 / 0.90 + 5.65 / 0.85
    p_run = vo * 6.0 / 0.90 + 5.65 / 0.85
    for name, pw in (("running 6 A", p_run), ("worst 11.2 A", p)):
        print(f"  {name}: {pw:.0f} W -> " + ", ".join(f"{k} {v} V: {pw/v:.1f} A" for k, v in VBAT.items()))
    r_in = {"XT30": 2.4e-3, "fuse 15 A (0297015, 4.58 mOhm cold, mirror DS)": 4.58e-3, "SiRA99DP hot": 2.65e-3 * 1.5}
    i_in = p / 9.0
    print("  path:", ", ".join(f"{k} {i_in**2*v:.2f} W" for k, v in r_in.items()), f"@ {i_in:.1f} A")
    print(f"  fuse 15 A: {i_in/15*100:.0f} % at 9.0 V; with -0.15 %/K derating at 60 C: {i_in/(15*(1-0.0015*37))*100:.0f} %")

    print("\n== Protection and sense nets ==")
    print("  SMBJ13A (Vishay 88392, 10/1000 us): VRWM 13 V, VBR 14.4..15.9 V, VC 21.5 V @ 27.9 A -- test-condition value")
    rg = 10e3
    for vz_max in (15.6,):
        iz = (21.5 - vz_max) / rg
        print(f"  gate zener (example BZT52C15, Vz 13.8..15.6 V): at 12.6 V no conduction if Vz,min > 12.6; "
              f"at 21.5 V Iz {iz*1e3:.2f} mA via {rg/1e3:.0f}k -> |VGS| ~ {vz_max:.1f} V + Iz*Rz (< 20 V)")
    for rt, rbt in ((120e3, 20e3),):
        for v in (12.6, 21.5):
            nom = v * rbt / (rt + rbt)
            hi = v * rbt * 1.01 / (rt * 0.99 + rbt * 1.01)
            print(f"  VBAT divider {rt/1e3:.0f}k/{rbt/1e3:.0f}k 1 %: {v} V -> {nom:.2f} V (max {hi:.2f} V)")
        print(f"  ADC +-50 mV -> +-{0.05*(rt+rbt)/rbt:.2f} V at battery, plus divider tolerance")
        print(f"  ESP32 unpowered, battery 12.6 V: source impedance {rt*rbt/(rt+rbt)/1e3:.1f}k, open-circuit {12.6*rbt/(rt+rbt):.2f} V "
              f"-> current into an unpowered pin up to ~{(12.6*rbt/(rt+rbt)-0.5)/(rt*rbt/(rt+rbt))*1e6:.0f} uA (estimate)")
    print("  INA240A3, 2 mOhm: " + ", ".join(f"{i} A -> {i*0.2:.2f} V" for i in (1, 6, 11.2, 14.5)),
          "| ADC-only error +-0.25 A")


def logic_5v_capacitance():
    """5 V rail output capacitance and transient checks (2026-11-15c). Estimates only."""
    print("\n== +5V output capacitance (3 x Murata GRM32ER71E226KE15L) ==")
    c_nom, n = 22e-6, 3
    tol = 0.10                 # initial tolerance +-10 % (Murata)
    bias_typ = {4.74: 0.178, 5.0: 0.201, 5.16: 0.215}  # Murata SimSurfing, typical, 25 degC, part-specific
    temp = 0.15                # X7R bound +-15 % (guaranteed class limit; part curve at 0 V: -7 % at -20 degC)
    aging = 0.05               # generic X7R ~2.5 %/decade, 2 decades after reference (not part-specific)
    c_min = n * c_nom * (1 - tol) * (1 - bias_typ[5.16]) * (1 - temp) * (1 - aging)
    c_typ = n * c_nom * (1 - bias_typ[5.0])
    print(f"  C_eff min {c_min*1e6:.1f} uF (tol, typ. DC bias @5.16 V, X7R temp bound, generic aging), "
          f"typ {c_typ*1e6:.1f} uF (25 degC, 5 V)")
    vlo, vhi, vnom = 4.738, 5.161, 4.946
    fsw_min, l_max = 290e3, 10e-6 * 1.2
    fo_req = 5.1 / (vlo * 40e3)
    print(f"  Eq.14 (fo < 40 kHz): needs >= {fo_req*1e6:.1f} uF; fo at C_min {5.1/(vnom*c_min)/1e3:.1f} kHz, "
          f"at C_typ {5.1/(vnom*c_typ)/1e3:.1f} kHz")
    for c, name in ((c_min, "C_min"), (c_typ, "C_typ")):
        fo = 5.1 / (vnom * c)
        print(f"  Eq.16 C6 at {name}: {1/(2*3.1416*fo*100e3)*1e12:.0f} pF (fitted 75 pF)")
    floor, ceil = 4.5, 5.5     # design floor (margin above receiver 4.0 V); ceiling: SK6812MINI-E / LVC8T245 5.5 V
    for di in (0.6, 1.0):
        dv = 2 * di / (fsw_min * c_min)   # Eq.11, step faster than ~2 switching periods (worst case)
        e = (vhi**2 + l_max * di**2 / c_min) ** 0.5 - vhi
        print(f"  step {di} A: Eq.11 dV {dv*1e3:.0f} mV -> load increase min {vlo-dv:.3f} V (floor {floor}), "
              f"load release max {vhi+dv:.3f} V (ceiling {ceil}); inductor-energy bound {e*1e3:.0f} mV")
    print(f"  ripple Eq.12 at C_min: {1.31/(8*fsw_min*c_min)*1e3:.1f} mV")
    print(f"  buzzer 0.15 A steps at 4 kHz: ~{2*0.15/(fsw_min*c_min)*1e3:.0f} mV per step (Eq.11 form)")


def servo_stage_parts():
    """LTC7803 stage with the selected parts and tolerances (2026-11-15d). Estimates only."""
    print("\n== Servo stage with selected parts ==")
    vo_lo, vo_hi = 6.686, 6.914
    f_min, f_nom = 340e3, 375e3
    i_load = 11.2
    for name, l_nom, isat_30, dcr_max in (("XAL1010-222ME 2.2 uH", 2.2e-6, 34.0, 2.80e-3),
                                          ("XAL1010-332MED 3.3 uH", 3.3e-6, 27.4, 4.10e-3)):
        l_min = l_nom * 0.8                         # +-20 % inductance tolerance
        worst = max(((v, vin) for v in (vo_lo, vo_hi) for vin in (9.0, 12.6)),
                    key=lambda p: p[0] * (1 - p[0] / p[1]))
        di_w = worst[0] * (1 - worst[0] / worst[1]) / (f_min * l_min)
        di_n = 6.8 * (1 - 6.8 / 12.6) / (f_nom * l_nom)
        rs_hi = 3e-3 * 1.01 * (1 + 100e-6 * 60)      # +1 % tolerance, +100 ppm/K over +60 K (WSL1020 TCR)
        rs_lo = 3e-3 * 0.99
        i_out_min = 0.045 / rs_hi - di_w / 2
        i_pk_max = 0.055 / rs_lo
        irms = (i_load ** 2 + di_n ** 2 / 12) ** 0.5
        p_cu = irms ** 2 * dcr_max * 1.3             # copper +30 % hot (estimate); core loss not included
        print(f"  {name}: dIL nom {di_n:.2f} A, worst {di_w:.2f} A (Vout {worst[0]}, Vin {worst[1]}, f {f_min/1e3:.0f} kHz, L-20 %)")
        print(f"     Iout,min {i_out_min:.2f} A vs {i_load} A load -> margin {i_out_min-i_load:+.2f} A; "
              f"peak limit max {i_pk_max:.1f} A vs Isat(30 %, 25 degC) {isat_30} A; "
              f"sense ripple {di_n*3e-3*1e3:.1f} mV (datasheet target 10-20 mV)")
        print(f"     inductor Irms {irms:.2f} A, copper loss {p_cu:.2f} W (DCR max, hot)")
    rds = 3.6e-3 * 1.4
    for vin in (9.0, 12.6):
        d = 6.914 / vin
        qg, vdrv, rdr = 16e-9, 5.15, 2.0               # BSC026N04LS Qg@4.5 V typ, INTVCC, LTC driver ~2 Ohm
        t_sw = qg / (vdrv / rdr) * 0.5                  # rough transition time estimate
        p_sw = 0.5 * vin * i_load * 2 * t_sw * f_nom
        print(f"  Vin {vin}: top FET cond {d*i_load**2*rds:.2f} W + switching ~{p_sw:.2f} W (rough), "
              f"bottom cond {(1-d)*i_load**2*rds:.2f} W")
    print(f"  RS401 3 mOhm @ {i_load} A: {i_load**2*3e-3:.2f} W, at peak limit 18.5 A: {18.5**2*3e-3:.2f} W (2 W rated at 70 degC)")
    print(f"  RS402 2 mOhm @ {i_load} A: {i_load**2*2e-3:.2f} W; drop {i_load*2e-3*1e3:.1f} mV (outside feedback)")


def history_2s():
    """Superseded 2S numbers, kept for appendix A traceability."""
    print("== HISTORY 2S (superseded 2026-11-15) ==")
    vo = 6.25
    for rs in (4e-3, 3e-3):
        dIw = vo * (1 - vo / 8.4) / (340e3 * 2.2e-6 * 0.8)
        print(f"Rs {rs*1e3:.0f} mOhm: Iout,min {0.045/(rs*1.01)-dIw/2:.1f} A, peak max {0.055/(rs*0.99):.1f} A")
    rt = 31.6e-3
    for i in (5.0, 11.0):
        print(f"{i} A: regulates down to Vin {vo + i*rt:.2f} V; Vservo at 6.0 V in {6.0-i*rt:.2f} V")
    p = vo * 11.0 / 0.9 + 5.65 / 0.85
    print("worst input:", ", ".join(f"{v} V: {p/v:.1f} A" for v in (7.4, 6.6, 6.0)))


def controller_checks():
    """Controller sheet: DevKit 5 V feed via D501, Q403/Q404 default OFF, O-21 shunts (all estimates).

    Sources: PMEG4010CEH Nexperia v.3 (2023-10-12; VF max at 25 degC, pulsed), SGM2212
    Rev A.2 (07/2023, LCSC copy), ESP32-S3-WROOM-1 DS v1.8, ESP32-S3 DS v2.2, NTR4003N/D Rev 6,
    LTC7803 Rev B, DevKitC-1 v1.1 schematic.
    """
    print("\n== Controller: DevKit 5 V feed (estimates) ==")
    i_load = 0.50 + 0.05            # module supply requirement >= 0.5 A (WROOM-1 Tab 6-2) + carrier 3V3 budget
    vdrop = 0.380 + (i_load - 0.5) / 0.3 * (0.610 - 0.380)   # SGM2212-3.3 max over temp, linear interpolation
    vf25 = 0.490 + (i_load - 0.5) / 0.2 * (0.520 - 0.490)    # PMEG4010CEH max at 25 degC, pulsed
    vf_cold = vf25 + 45 * 0.002                               # -20 degC, generic Schottky TC 2 mV/K (assumption)
    v5_min, v5_dip, path = 4.74, 0.02 * 5.0, 0.05            # +5V static min, load-step allowance, socket + traces
    vin = v5_min - v5_dip - vf_cold - path
    need_reg = 3.349 + vdrop
    need_module = 3.0 + vdrop
    print("  design load %.2f A, LDO dropout max %.0f mV, D501 VF %.0f mV (25 degC) / %.0f mV (-20 degC)"
          % (i_load, vdrop * 1e3, vf25 * 1e3, vf_cold * 1e3))
    print("  LDO input min %.2f V; needed for regulation %.2f V (margin %.2f V), for VDD >= 3.0 V %.2f V"
          % (vin, need_reg, vin - need_reg, need_module))
    for name, i, vf, rth in (("average 0.20 A, 1 cm2 pad", 0.20, 0.45, 150), ("continuous 0.55 A, 1 cm2 pad", 0.55, vf25, 150),
                             ("continuous 0.55 A, standard pad", 0.55, vf25, 330)):
        pd = i * vf
        print("  D501 %-32s P = %.0f mW, dT = %.0f K, Tj at 65 degC = %.0f degC" % (name, pd * 1e3, pd * rth, 65 + pd * rth))

    print("\n== Q403/Q404 default OFF (static, estimates) ==")
    tol = 0.02                                                # 1 % + 100 ppm/K over 85 K
    r414, r407 = 100e3, 220e3
    k_min = r407 * (1 - tol) / (r414 * (1 + tol) + r407 * (1 - tol))
    r_th = 1 / (1 / (r414 * (1 + tol)) + 1 / (r407 * (1 - tol)))
    for vbat in (9.2, 12.6, 21.5):
        vg = vbat * k_min - 1e-6 * r_th                       # Q404 IDSS 1 uA (25 degC max) + Q403 IGSS
        print("  rail OFF: VBAT %.1f V -> Q403 VGS min %.2f V (needs >= 4.0 V for the 1.5 Ohm spec)" % (vbat, vg))
    i_on = 21.5 / (r414 * (1 - tol))
    rds_hot = 2.0 * 1.6                                       # 2.0 Ohm at 2.5 V, x1.6 at 125 degC (Fig. 5, typical)
    print("  rail ON: GPIO VOH min 0.8 x 3.251 = %.2f V >= 2.5 V; Q404 current max %.0f uA; Q403 VGS <= %.2f mV"
          % (0.8 * 3.251, i_on * 1e6, i_on * rds_hot * 1e3))
    run_th = 17.5e3
    print("  Q403 off-leakage 1 uA (25 degC max) shifts RUN by %.1f mV (RUN thresholds 1.2 V level)" % (1e-6 * run_th * 1e3))
    tau_g = r_th * (42e-12 + 40e-12 + 5e-12)
    print("  transient: Q403 gate tau %.1f us; RUN tau with C420 %.2f ms" % (tau_g * 1e6, run_th * 100e-9 * 1e3))

    print("\n== O-21 input protection (estimates) ==")
    # TLV809E (SLVSES2J): VIT- 2.93 V +-2 %, hysteresis 0.9-1.5 %, tPD_HL <= 50 us, tD 33-67 ms (variant D)
    vit_min, vit_max = 2.93 * 0.98, 2.93 * 1.02
    print("  P3V3_OK low below %.2f-%.2f V within 50 us; high again %.0f-%.0f ms after VDD > VIT+" % (vit_min, vit_max, 33, 67))
    print("  ADC limit while P3V3_OK high: VIH max = VDD + 0.3 >= %.2f V; VBAT_DIV max 3.07 V at the TVS clamp" % (vit_min + 0.3))
    for name, k in (("VBAT  (Q505, 100k/100k)", 0.5), ("VSERVO (Q405, 100k/22k)", 100 / 122)):
        for v in ((9.0, 12.6, 21.5) if "VBAT" in name else (6.8, 7.81)):
            print("  %s: VGS at %.2f V = -%.2f V (NTR4171P: spec -4.5 V, limit -12 V)" % (name, v, v * k))
    for name, r, c in (("VBAT_DIV", 17.1e3, 1e-9), ("VSERVO_DIV", 32e3, 1e-9), ("ISERVO_FILT", 10e3, 10e-9)):
        i_clamp = c * 10.0 / 1e-3        # rail falling at <= 10 V/ms (assumption, 3 V/ms estimated from 32 uF and 0.1 A)
        print("  %-11s tau %5.1f us; BAT54 current at 10 V/ms <= %.0f uA -> VF <= 240 mV (spec point 0.1 mA)"
              % (name, r * c * 1e6, i_clamp * 1e6))
    print("  divider switch off-leakage 1 uA (NTR4171P, 25 degC max) -> VBAT_DIV 20 mV, VSERVO_DIV 47 mV")

    print("\n== Actuators open-drain outputs (estimates) ==")
    for vext in (7.4, 7.81):
        print("  foreign %.2f V on the signal pin: Q on -> %.1f mA through 470 Ohm into Q; Q off -> BAT54 reverse %.2f V, "
              "current into +5V = IR only (<= 2 uA at 25 V)" % (vext, vext / 470 * 1e3, vext - 4.74))
    for rin in (10e3, 50e3, 1e9):
        i = (5.16 - 0.3) / (2.2e3 + 470 + rin)
        print("  high level into a %s input: %.2f V" % ("open" if rin > 1e8 else "%.0fk" % (rin / 1e3), 4.74 - 0.32 - i * 2.2e3 if rin < 1e8 else 4.74 - 0.24))
    print("  pull-up current while low: %.1f mA per channel, %.1f mA for 5 channels" % (4.86 / 2.2e3 * 1e3, 5 * 4.86 / 2.2e3 * 1e3))


if __name__ == "__main__":
    if "--history-2s" in sys.argv:
        history_2s()
    elif "--controller" in sys.argv:
        controller_checks()
    else:
        active_3s()
        logic_5v_capacitance()
        servo_stage_parts()
