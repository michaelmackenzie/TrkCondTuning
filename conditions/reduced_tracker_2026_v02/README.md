# reduced_tracker_2026_v02

The official reduced-tracker DB version **Sim_best v2_0** (created 2026-11-06 by R. Bonventre,
"Tracker conditions based on expectations from KPP") with the commissioning gas gain and
threshold noise. Successor of `reduced_tracker_2026` (Sim_best v1_5 + Sim_commissioning.txt).

Files
- `conditions.fcl`: ProditionsService overrides (wire voltage 1400, gas gain 5.53e4, threshold
  noise 3.5; the same values as reduced_tracker_2026). The tracker tables (straw / panel status,
  preamp thresholds and delays, panel delays, reco straw alignment) come from the DB version.
- `source_settings_2026-11-06.fcl`: the settings as received (gain/noise + straw-response
  calibration). The calibration part is `fragments/response/calib_reduced_tracker_2026_v02.fcl`,
  a `scope="both"` candidate (it changes the reco only; the digitization does not use
  StrawResponse).

Use: `studies/reduced_tracker_2026_v02.py`. Compare the conditions with
`tct conditions reduced_tracker_2026_v02 --add reduced_tracker_2026_10`.
