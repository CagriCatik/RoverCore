#!/usr/bin/env python3
"""Project symbol for the restart interlock (O-35): SN74LVC1G74 in DCU (VSSOP-8).

KiCad 10.0.7 has no 74LVC1G74 symbol. Pinout: TI SCES794G (Oct 2009, rev. Sep 2021) Figure 5-1, DCT/DCU top view:
1 CLK, 2 D, 3 Q-bar, 4 GND, 5 Q, 6 CLR-bar, 7 PRE-bar, 8 VCC. Function table 8-1: PRE low -> Q high, CLR low -> Q low,
both low -> Q and Q-bar high (non-stable), rising CLK edge -> Q = D.
The supervisor (TPS3808DBV) and the OR gate (74LVC1G32) come from the KiCad libraries; their pin numbers were
compared with TI SBVS050N Figure 5-1 (1 RESET, 2 GND, 3 MR, 4 CT, 5 SENSE, 6 VDD) and SCES219W Figure 4-1
(1 A, 2 B, 3 GND, 4 Y, 5 VCC).

Usage: python3 hardware/scripts/make_interlock_parts.py   (rewrites only this symbol)
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_lighting_parts import pin  # noqa: E402
from make_protection_parts import body, put, symbol  # noqa: E402

NAME = "SN74LVC1G74_DCU"

if __name__ == "__main__":
    pins = (pin("input", "2", "D", -10.16, 2.54, 0) + pin("input", "1", "CLK", -10.16, -2.54, 0)
            + pin("power_in", "8", "VCC", -2.54, 10.16, 270) + pin("input", "7", "~{PRE}", 2.54, 10.16, 270)
            + pin("power_in", "4", "GND", -2.54, -10.16, 90) + pin("input", "6", "~{CLR}", 2.54, -10.16, 90)
            + pin("output", "5", "Q", 10.16, 2.54, 180) + pin("output", "3", "~{Q}", 10.16, -2.54, 180))
    put(symbol(NAME, "U", "Package_SO:VSSOP-8_2.3x2mm_P0.5mm", "https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf",
               "Single D flip-flop with preset and clear, positive edge; DCU pinout 1 CLK, 2 D, 3 Q-bar, 4 GND, 5 Q, "
               "6 CLR-bar, 7 PRE-bar, 8 VCC (TI SCES794G); Ioff partial power-down",
               pins, body(NAME, (-7.62, 7.62), (7.62, -7.62)), ref_at=(-7.62, 12.7), val_at=(5.08, 12.7)), NAME)
    print("wrote", NAME)
