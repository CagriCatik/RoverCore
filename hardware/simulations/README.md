# Hardware simulations

Keep SPICE/thermal/copper-flow model source and inputs, solver version,
units, boundary conditions, material properties, assumptions and validation.
Generated plots should go to `qa/generated/`.

VCU: `power/servo_voltage_budget.py` estimates shared and individual wiring
losses up to external servo connectors. Inputs are explicit current scenarios,
not a validated servo model. See
[`docs/vcu/tooling-integration.md`](../../docs/vcu/tooling-integration.md)
for assumptions, invocation and verification limits.
