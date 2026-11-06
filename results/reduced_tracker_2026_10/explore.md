# Exploration: reduced_tracker_2026_10

Phases: reco, trigger.
Proposed: `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr` (added: calib, offline_helix_loose, nsh10_cpr, cpr_finder_minhits7, nsh10_apr)

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

- nsh10_cpr: gain +0.0574, z 21.4 [459/0] -> accepted
- nsh10_apr: gain +0.0288, z 15.2 [230/0] -> pass (passes the gates, not the best / not screened)
- cpr_finder_minhits7: gain +0.0144, z 8.2 [157/42] -> pass (passes the gates, not the best / not screened)
- cprchi2: gain +0.0024, z 4.4 [19/0] -> fail (gain +0.0024 < min_gain 0.005)
- apr_finder_minima: gain +0.0031, z 1.6 [141/116] -> fail (gain +0.0031 < min_gain 0.005)
- apr_cand3a20: gain +0.0023, z 3.7 [21/3] -> fail (gain +0.0023 < min_gain 0.005)
- apr_alias100: gain +0.0025, z 4.1 [22/2] -> fail (gain +0.0025 < min_gain 0.005)
- apr_phiz2: gain +0.0115, z 6.0 [165/73] -> pass (passes the gates, not the best / not screened)
- apr_ks8: gain +0.0218, z 13.2 [174/0] -> pass (passes the gates, not the best / not screened)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: nsh10_cpr

## trigger round 2 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr`, objective 0.4755)

- nsh10_apr: gain +0.0183, z 12.1 [146/0] -> pass (passes the gates, not the best / not screened)
- cpr_finder_minhits7: gain +0.0600, z 19.4 [546/66] -> accepted
- cprchi2: gain +0.0035, z 5.3 [28/0] -> fail (gain +0.0035 < min_gain 0.005)
- apr_finder_minima: gain +0.0021, z 1.1 [125/108] -> fail (gain +0.0021 < min_gain 0.005)
- apr_cand3a20: gain +0.0020, z 3.4 [19/3] -> fail (gain +0.0020 < min_gain 0.005)
- apr_alias100: gain +0.0024, z 4.0 [21/2] -> fail (gain +0.0024 < min_gain 0.005)
- apr_phiz2: gain +0.0098, z 5.4 [144/66] -> pass (passes the gates, not the best / not screened)
- apr_ks8: gain +0.0146, z 10.8 [117/0] -> pass (passes the gates, not the best / not screened)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: cpr_finder_minhits7

## trigger round 3 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7`, objective 0.5355)

- nsh10_apr: gain +0.0143, z 10.7 [114/0] -> accepted
- cprchi2: gain +0.0051, z 6.4 [41/0] -> pass (passes the gates, not the best / not screened)
- apr_finder_minima: gain +0.0016, z 0.9 [113/100] -> fail (gain +0.0016 < min_gain 0.005)
- apr_cand3a20: gain +0.0020, z 3.4 [19/3] -> fail (gain +0.0020 < min_gain 0.005)
- apr_alias100: gain +0.0024, z 4.0 [21/2] -> fail (gain +0.0024 < min_gain 0.005)
- apr_phiz2: gain +0.0088, z 5.2 [125/55] -> pass (passes the gates, not the best / not screened)
- apr_ks8: gain +0.0116, z 9.6 [93/0] -> pass (passes the gates, not the best / not screened)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- accepted: nsh10_apr

## trigger round 4 (current `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr`, objective 0.5498)

- cprchi2: gain +0.0048, z 6.2 [38/0] -> fail (gain +0.0048 < min_gain 0.005)
- apr_finder_minima: gain +0.0253, z 9.9 [310/108] -> fail (rate: apr_TrkDe_75m70p_D0200: 41 > 33.3 (nom 28, cur 5); apr_TrkDe_80m70p_D0200: 26 > 7.2 (nom 5, cur 4))
- apr_cand3a20: gain +0.0018, z 3.0 [18/4] -> fail (gain +0.0018 < min_gain 0.005)
- apr_alias100: gain +0.0026, z 4.0 [24/3] -> fail (gain +0.0026 < min_gain 0.005)
- apr_phiz2: gain +0.0144, z 7.3 [183/68] -> fail (rate: apr_TrkDe_80m70p_D0200: 8 > 7.2 (nom 5, cur 4))
- apr_ks8: gain +0.0016, z 3.6 [13/0] -> fail (gain +0.0016 < min_gain 0.005)
- apr_tgtrep100: skipped (requires ['apr_cand3a20'])
- stop: no candidate passes

CPU: proposal 0.7187043620851303 ms vs nominal 0.9718880951309457 ms (x0.74, limit x1.2)
