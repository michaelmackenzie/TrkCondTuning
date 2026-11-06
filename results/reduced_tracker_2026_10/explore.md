# Exploration: reduced_tracker_2026_10

Phases: reco, trigger.
Proposed: `reduced_tracker_2026+9settings-50f4241a66` (added: calib, offline_helix_loose, nsh10_cpr, cpr_finder_minhits7, nsh10_apr, apr_phiz2, apr_finder_minima, apr_cand3a20, apr_tgtrep100)

## reco round 1 (current `reduced`, objective 0.4329)

- offline_helix_loose: gain +0.0195, z 6.5 [367/211] -> pass (passes the gates, not the best / not screened)
- tdres20: gain +0.0208, z 5.9 [475/309] -> pass (passes the gates, not the best / not screened)
- calib: gain +0.0409, z 10.6 [636/309] -> accepted
- accepted: calib

## reco round 2 (current `reduced_tracker_2026+calib`, objective 0.4738)

- offline_helix_loose: gain +0.0218, z 7.9 [328/154] -> accepted
- tdres20: skipped (group straw_response occupied)
- accepted: offline_helix_loose

## reco round 3 (current `reduced_tracker_2026+calib+offline_helix_loose`)

- tdres20: skipped (group straw_response occupied)
- stop: no eligible candidates

## trigger round 1 (current `reduced_tracker_2026+calib+offline_helix_loose`, objective 0.4181)

- nsh10_cpr: gain +0.0574, z 21.4 [459/0] -> accepted; bkg total 5.7 Hz (+1.0 ± 1.0, allowed +114.8), utility +0.0569
- nsh10_apr: gain +0.0288, z 15.2 [230/0] -> pass; bkg total 6.7 Hz (+1.9 ± 1.3, allowed +57.5), utility +0.0278 (passes the gates, not the best / not screened)
- cpr_finder_minhits7: gain +0.0144, z 8.2 [157/42] -> pass (passes the gates, not the best / not screened)
- cprchi2: gain +0.0024, z 4.4 [19/0] -> fail (gain +0.0024 < min_gain 0.005)
- apr_finder_minima: gain +0.0031, z 1.6 [141/116] -> fail (gain +0.0031 < min_gain 0.005)
- apr_cand3a20: gain +0.0023, z 3.7 [21/3] -> fail (gain +0.0023 < min_gain 0.005)
- apr_alias100: gain +0.0025, z 4.1 [22/2] -> fail (gain +0.0025 < min_gain 0.005)
- apr_phiz2: gain +0.0115, z 6.0 [165/73] -> pass (passes the gates, not the best / not screened)
- apr_ks8: gain +0.0218, z 13.2 [174/0] -> pass; bkg total 10.5 Hz (+5.7 ± 2.3, allowed +43.5), utility +0.0189 (passes the gates, not the best / not screened)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: nsh10_cpr

## trigger round 2 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr`, objective 0.4755)

- nsh10_apr: gain +0.0183, z 12.1 [146/0] -> pass; bkg total 7.6 Hz (+1.9 ± 1.3, allowed +36.5), utility +0.0173 (passes the gates, not the best / not screened)
- cpr_finder_minhits7: gain +0.0600, z 19.4 [546/66] -> accepted; bkg total 7.6 Hz (+1.9 ± 1.3, allowed +120.1), utility +0.0591
- cprchi2: gain +0.0035, z 5.3 [28/0] -> fail (gain +0.0035 < min_gain 0.005)
- apr_finder_minima: gain +0.0021, z 1.1 [125/108] -> fail (gain +0.0021 < min_gain 0.005)
- apr_cand3a20: gain +0.0020, z 3.4 [19/3] -> fail (gain +0.0020 < min_gain 0.005)
- apr_alias100: gain +0.0024, z 4.0 [21/2] -> fail (gain +0.0024 < min_gain 0.005)
- apr_phiz2: gain +0.0098, z 5.4 [144/66] -> pass (passes the gates, not the best / not screened)
- apr_ks8: gain +0.0146, z 10.8 [117/0] -> pass; bkg total 11.4 Hz (+5.7 ± 2.3, allowed +29.3), utility +0.0118 (passes the gates, not the best / not screened)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: cpr_finder_minhits7

## trigger round 3 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7`, objective 0.5355)

- nsh10_apr: gain +0.0143, z 10.7 [114/0] -> accepted; bkg total 9.5 Hz (+1.9 ± 1.3, allowed +28.5), utility +0.0133
- cprchi2: gain +0.0051, z 6.4 [41/0] -> pass (passes the gates, not the best / not screened)
- apr_finder_minima: gain +0.0016, z 0.9 [113/100] -> fail (gain +0.0016 < min_gain 0.005)
- apr_cand3a20: gain +0.0020, z 3.4 [19/3] -> fail (gain +0.0020 < min_gain 0.005)
- apr_alias100: gain +0.0024, z 4.0 [21/2] -> fail (gain +0.0024 < min_gain 0.005)
- apr_phiz2: gain +0.0088, z 5.2 [125/55] -> pass; bkg total 6.7 Hz (-1.0 ± 1.0, allowed +17.5), utility +0.0092 (passes the gates, not the best / not screened)
- apr_ks8: gain +0.0116, z 9.6 [93/0] -> pass; bkg total 13.3 Hz (+5.7 ± 2.3, allowed +23.3), utility +0.0088 (passes the gates, not the best / not screened)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: nsh10_apr

## trigger round 4 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr`, objective 0.5498)

- cprchi2: gain +0.0048, z 6.2 [38/0] -> fail (gain +0.0048 < min_gain 0.005)
- apr_finder_minima: gain +0.0253, z 9.9 [310/108] -> pass; bkg total 41.0 Hz (+31.4 ± 5.6, allowed +50.5), utility +0.0095 (passes the gates, not the best / not screened)
- apr_cand3a20: gain +0.0018, z 3.0 [18/4] -> fail (gain +0.0018 < min_gain 0.005)
- apr_alias100: gain +0.0026, z 4.0 [24/3] -> fail (gain +0.0026 < min_gain 0.005)
- apr_phiz2: gain +0.0144, z 7.3 [183/68] -> accepted; bkg total 10.5 Hz (+1.0 ± 2.1, allowed +28.8), utility +0.0139
- apr_ks8: gain +0.0016, z 3.6 [13/0] -> fail (gain +0.0016 < min_gain 0.005)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: apr_phiz2

## trigger round 5 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr+apr_phiz2`, objective 0.5642)

- cprchi2: gain +0.0046, z 6.1 [37/0] -> fail (gain +0.0046 < min_gain 0.005)
- apr_finder_minima: gain +0.0211, z 8.3 [293/124] -> accepted; bkg total 35.3 Hz (+24.8 ± 5.4, allowed +42.3), utility +0.0087
- apr_cand3a20: gain +0.0018, z 2.1 [29/15] -> fail (gain +0.0018 < min_gain 0.005)
- apr_alias100: gain +0.0031, z 4.6 [27/2] -> fail (gain +0.0031 < min_gain 0.005)
- apr_ks8: gain +0.0019, z 3.9 [15/0] -> fail (gain +0.0019 < min_gain 0.005)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: apr_finder_minima

## trigger round 6 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr+apr_phiz2+apr_finder_minima`, objective 0.5853)

- cprchi2: gain +0.0039, z 5.6 [31/0] -> fail (gain +0.0039 < min_gain 0.005)
- apr_cand3a20: gain +0.0110, z 6.7 [129/41] -> accepted; bkg total 34.3 Hz (-1.0 ± 3.9, allowed +22.0), utility +0.0115
- apr_alias100: gain +0.0039, z 4.6 [38/7] -> fail (gain +0.0039 < min_gain 0.005)
- apr_ks8: gain +0.0075, z 7.7 [60/0] -> fail; bkg total 88.6 Hz (+53.4 ± 7.1, allowed +15.0), utility -0.0192 (rate: total rate +53.4 ± 7.1 Hz > 15.0 Hz allowed for gain +0.0075)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: apr_cand3a20

## trigger round 7 (current `reduced_tracker_2026+8settings-0d8d3ff4b5`, objective 0.5963)

- cprchi2: gain +0.0039, z 5.6 [31/0] -> fail (gain +0.0039 < min_gain 0.005)
- apr_alias100: gain +0.0024, z 3.0 [30/11] -> fail (gain +0.0024 < min_gain 0.005)
- apr_tgtrep100: gain +0.0104, z 8.4 [90/7] -> accepted; bkg total 35.3 Hz (+1.0 ± 1.7, allowed +20.8), utility +0.0099
- apr_ks8: gain +0.0075, z 7.7 [60/0] -> fail; bkg total 85.8 Hz (+51.5 ± 7.0, allowed +15.0), utility -0.0182 (rate: total rate +51.5 ± 7.0 Hz > 15.0 Hz allowed for gain +0.0075)
- accepted: apr_tgtrep100

## trigger round 8 (current `reduced_tracker_2026+9settings-50f4241a66`, objective 0.6067)

- cprchi2: gain +0.0036, z 5.4 [29/0] -> fail (gain +0.0036 < min_gain 0.005)
- apr_alias100: gain +0.0014, z 1.8 [24/13] -> fail (gain +0.0014 < min_gain 0.005)
- apr_ks8: gain +0.0078, z 7.9 [62/0] -> fail; bkg total 84.8 Hz (+49.5 ± 6.9, allowed +15.5), utility -0.0170 (rate: total rate +49.5 ± 6.9 Hz > 15.5 Hz allowed for gain +0.0078)
- stop: no candidate passes

CPU: proposal 1.1227855637852366 ms vs nominal 0.9718880951309457 ms (x1.16, limit x1.2)
