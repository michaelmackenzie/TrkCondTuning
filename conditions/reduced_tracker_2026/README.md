# reduced_tracker_2026

The 2026 commissioning-tracker condition studied in the 2026-10 reduced-tracker study
(main/trigger/reduced_tracker/notes.org): about 31% of the straws dead (44 NoHV panels
including all of station 7, plus disabled straws), a lower gas gain (5.53e4 vs 7.0e4) and
about 3x the threshold noise (3.5 vs 1.25). Median CE helix hits: 35 -> 22.

Files
- `Sim_commissioning.txt`: DbService text table with the dead / disabled straws (loaded on top
  of Sim_best v1_5 via `Condition.text_tables`).
- `conditions.fcl`: the ProditionsService overrides (wire voltage, gas gain, threshold noise)
  used by `Condition.fcl`. It has no DbService lines: the DB purpose/version and the text
  table are set by the Condition fields, so the job generator can place them itself.

Use
- Re-digitization from the MDC2025au mixes (made with Sim_best v1_3) is valid: the condition
  only lowers the straw hit efficiency (`redigi_ok = True`).
- The straw-response calibration `fragments/response/calib_reduced_tracker_2026.fcl` is specific
  to this condition.
- Study: `studies/reduced_tracker_2026_10.py`.
