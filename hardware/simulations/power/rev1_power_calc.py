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
    vo5, L5 = 0.596 * (1 + 100e3 / 13.3e3), 10e-6
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


if __name__ == "__main__":
    history_2s() if "--history-2s" in sys.argv else active_3s()
