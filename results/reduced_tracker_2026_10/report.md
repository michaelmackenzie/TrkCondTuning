# Study reduced_tracker_2026_10: reduced-tracker study of 2026-10 (the study this package generalizes), redone with the exploration

Configurations: `nominal`, `reduced`, `reduced_safe`, `reduced_recommended`, `reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr` (last: proposed). Nominal reference: `nominal`.

## 1. Takeaway: Offline reconstruction and trigger efficiency

### CeM

Percent of MC-triggerable events ± binomial error; (x%) = fraction of the nominal configuration. Offline: highest-nactive fit of pdg 11 with p > 75 MeV/c, matched to the primary; reconstructable = >= 15 active hits. Trigger rows: each configuration's own re-digitized events (`trig` jobs); 'of those' and 'AND' use the trigger bits of the Offline-job events.

| quantity | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| Offline track found | 90.8 ± 0.5 | 63.7 ± 0.8 (70%) | 65.5 ± 0.8 (72%) | 73.1 ± 0.7 (80%) | 73.1 ± 0.7 (80%) |
| Offline reconstructable (>= 15 active hits) | 87.6 ± 0.5 | 57.3 ± 0.8 (65%) | 58.0 ± 0.8 (66%) | 62.4 ± 0.8 (71%) | 62.4 ± 0.8 (71%) |
| Offline loose (>= 10 active hits) | 90.0 ± 0.5 | 62.7 ± 0.8 (70%) | 64.6 ± 0.8 (72%) | 71.4 ± 0.7 (79%) | 71.4 ± 0.7 (79%) |
| Offline quality (TrkQual-input box cuts) | 68.2 ± 0.7 | 40.3 ± 0.8 (59%) | 39.0 ± 0.8 (57%) | 45.8 ± 0.8 (67%) | 45.8 ± 0.8 (67%) |
| trigger cpr_TrkDe_75m70p | 72.8 ± 0.7 | 37.8 ± 0.8 (52%) | 57.0 ± 0.8 (78%) | 57.4 ± 0.8 (79%) | 56.4 ± 0.8 (78%) |
| trigger apr_TrkDe_75m70p | 82.7 ± 0.6 | 31.1 ± 0.7 (38%) | 45.1 ± 0.8 (55%) | 64.2 ± 0.8 (78%) | 46.9 ± 0.8 (57%) |
| trigger apr_TrkDe_75m70p_D0200 | 82.4 ± 0.6 | 30.6 ± 0.7 (37%) | 44.1 ± 0.8 (54%) | 62.2 ± 0.8 (76%) | 46.0 ± 0.8 (56%) |
| trigger cpr_TrkDe_75m70p OR apr_TrkDe_75m70p | 86.0 ± 0.5 | 46.0 ± 0.8 (54%) | 65.7 ± 0.8 (76%) | 72.1 ± 0.7 (84%) | 66.0 ± 0.7 (77%) |
| trigger cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 | 85.9 ± 0.5 | 45.8 ± 0.8 (53%) | 65.3 ± 0.8 (76%) | 71.5 ± 0.7 (83%) | 65.6 ± 0.8 (76%) |
| cpr_TrkDe_75m70p, of Offline reconstructable | 82.4 ± 0.6 | 63.8 ± 1.0 (78%) | 79.6 ± 0.8 (97%) | 78.7 ± 0.8 (96%) | 77.4 ± 0.8 (94%) |
| apr_TrkDe_75m70p, of Offline reconstructable | 93.8 ± 0.4 | 53.4 ± 1.0 (57%) | 71.8 ± 0.9 (77%) | 89.2 ± 0.6 (95%) | 70.9 ± 0.9 (76%) |
| apr_TrkDe_75m70p_D0200, of Offline reconstructable | 93.4 ± 0.4 | 52.6 ± 1.0 (56%) | 70.4 ± 0.9 (75%) | 86.9 ± 0.7 (93%) | 69.6 ± 0.9 (75%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p, of Offline reconstructable | 97.3 ± 0.3 | 77.8 ± 0.9 (80%) | 92.3 ± 0.6 (95%) | 95.6 ± 0.4 (98%) | 90.7 ± 0.6 (93%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200, of Offline reconstructable | 97.2 ± 0.3 | 77.5 ± 0.9 (80%) | 91.9 ± 0.6 (95%) | 94.8 ± 0.4 (98%) | 90.3 ± 0.6 (93%) |
| **Offline reconstructable AND cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200** | 85.2 ± 0.6 | 44.4 ± 0.8 (52%) | 53.3 ± 0.8 (63%) | 59.2 ± 0.8 (69%) | 56.3 ± 0.8 (66%) |
| **Offline reconstructable AND cpr_TrkDe_75m70p OR apr_TrkDe_75m70p** | 85.3 ± 0.6 | 44.6 ± 0.8 (52%) | 53.5 ± 0.8 (63%) | 59.6 ± 0.8 (70%) | 56.6 ± 0.8 (66%) |
| events (trigger jobs / Offline jobs) | 4000 / 4000 | 4000 / 4000 | 4000 / 4000 | 4000 / 4000 | 4000 / 4000 |


### CeP

Percent of MC-triggerable events ± binomial error; (x%) = fraction of the nominal configuration. Offline: highest-nactive fit of pdg -11 with p > 70 MeV/c, matched to the primary; reconstructable = >= 15 active hits. Trigger rows: each configuration's own re-digitized events (`trig` jobs); 'of those' and 'AND' use the trigger bits of the Offline-job events.

| quantity | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| Offline track found | 76.9 ± 0.7 | 35.9 ± 0.8 (47%) | 40.9 ± 0.8 (53%) | 51.4 ± 0.8 (67%) | 51.4 ± 0.8 (67%) |
| Offline reconstructable (>= 15 active hits) | 71.2 ± 0.7 | 29.2 ± 0.7 (41%) | 32.7 ± 0.7 (46%) | 36.7 ± 0.8 (52%) | 36.7 ± 0.8 (52%) |
| Offline loose (>= 10 active hits) | 76.1 ± 0.7 | 34.9 ± 0.8 (46%) | 39.7 ± 0.8 (52%) | 48.2 ± 0.8 (63%) | 48.2 ± 0.8 (63%) |
| Offline quality (TrkQual-input box cuts) | 50.9 ± 0.8 | 17.3 ± 0.6 (34%) | 18.3 ± 0.6 (36%) | 23.1 ± 0.7 (45%) | 23.1 ± 0.7 (45%) |
| trigger cpr_TrkDe_75m70p | 59.9 ± 0.8 | 16.8 ± 0.6 (28%) | 35.9 ± 0.8 (60%) | 38.0 ± 0.8 (63%) | 37.1 ± 0.8 (62%) |
| trigger apr_TrkDe_75m70p | 68.4 ± 0.7 | 12.2 ± 0.5 (18%) | 23.3 ± 0.7 (34%) | 41.4 ± 0.8 (60%) | 25.2 ± 0.7 (37%) |
| trigger apr_TrkDe_75m70p_D0200 | 67.9 ± 0.7 | 12.0 ± 0.5 (18%) | 22.7 ± 0.7 (33%) | 40.1 ± 0.8 (59%) | 24.5 ± 0.7 (36%) |
| trigger cpr_TrkDe_75m70p OR apr_TrkDe_75m70p | 75.1 ± 0.7 | 21.3 ± 0.6 (28%) | 42.5 ± 0.8 (57%) | 51.5 ± 0.8 (69%) | 44.7 ± 0.8 (60%) |
| trigger cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 | 74.9 ± 0.7 | 21.2 ± 0.6 (28%) | 42.2 ± 0.8 (56%) | 50.8 ± 0.8 (68%) | 44.3 ± 0.8 (59%) |
| cpr_TrkDe_75m70p, of Offline reconstructable | 74.2 ± 0.8 | 51.0 ± 1.5 (69%) | 70.6 ± 1.3 (95%) | 71.0 ± 1.2 (96%) | 69.3 ± 1.2 (93%) |
| apr_TrkDe_75m70p, of Offline reconstructable | 87.3 ± 0.6 | 38.9 ± 1.4 (45%) | 60.2 ± 1.4 (69%) | 83.1 ± 1.0 (95%) | 58.7 ± 1.3 (67%) |
| apr_TrkDe_75m70p_D0200, of Offline reconstructable | 86.7 ± 0.6 | 38.4 ± 1.4 (44%) | 58.7 ± 1.4 (68%) | 81.0 ± 1.0 (93%) | 57.3 ± 1.3 (66%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p, of Offline reconstructable | 94.4 ± 0.4 | 65.1 ± 1.4 (69%) | 86.2 ± 1.0 (91%) | 93.0 ± 0.7 (99%) | 84.9 ± 0.9 (90%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200, of Offline reconstructable | 94.1 ± 0.4 | 64.8 ± 1.4 (69%) | 85.4 ± 1.0 (91%) | 92.2 ± 0.7 (98%) | 84.3 ± 0.9 (90%) |
| **Offline reconstructable AND cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200** | 67.0 ± 0.7 | 18.9 ± 0.6 (28%) | 27.9 ± 0.7 (42%) | 33.8 ± 0.7 (51%) | 30.9 ± 0.7 (46%) |
| **Offline reconstructable AND cpr_TrkDe_75m70p OR apr_TrkDe_75m70p** | 67.2 ± 0.7 | 19.0 ± 0.6 (28%) | 28.2 ± 0.7 (42%) | 34.2 ± 0.8 (51%) | 31.1 ± 0.7 (46%) |
| events (trigger jobs / Offline jobs) | 3997 / 3997 | 3997 / 3997 | 3997 / 3997 | 3997 / 3997 | 3997 / 3997 |


## 2. Background trigger rates

### NoPrimary

Rate = passing microbunches / events x 590.0 kHz x duty factor 0.323; no passes -> upper limit with 3 events (95% CL). Cells: rate [Hz] (events passing); x nominal = ratio of passing events.

| path | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| cpr_TrkDe_75m70p | 21.9 Hz (23) | 1.9 Hz (2) x0.09 | 7.6 Hz (8) x0.35 | 6.7 Hz (7) x0.30 | 6.7 Hz (7) x0.30 |
| cpr_TrkDe_75m70p_D0200 | 21.0 Hz (22) | 1.9 Hz (2) x0.09 | 7.6 Hz (8) x0.36 | 6.7 Hz (7) x0.32 | 6.7 Hz (7) x0.32 |
| cpr_TrkDe_80m70p | 8.6 Hz (9) | 1.9 Hz (2) x0.22 | 4.8 Hz (5) x0.56 | 4.8 Hz (5) x0.56 | 4.8 Hz (5) x0.56 |
| cpr_TrkDe_80m70p_D0200 | 7.6 Hz (8) | 1.9 Hz (2) x0.25 | 4.8 Hz (5) x0.62 | 4.8 Hz (5) x0.62 | 4.8 Hz (5) x0.62 |
| apr_TrkDe_75m70p_D0200 | 26.7 Hz (28) | < 2.9 Hz (0) x0.00 | 4.8 Hz (5) x0.18 | 34.3 Hz (36) x1.29 | 4.8 Hz (5) x0.18 |
| apr_TrkDe_80m70p_D0200 | 4.8 Hz (5) | < 2.9 Hz (0) x0.00 | 2.9 Hz (3) x0.60 | 21.9 Hz (23) x4.60 | 3.8 Hz (4) x0.80 |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 | 34.3 Hz (36) | 1.9 Hz (2) x0.06 | 10.5 Hz (11) x0.31 | 35.3 Hz (37) x1.03 | 9.5 Hz (10) x0.28 |
| microbunches | 200000 | 200000 | 200000 | 200000 | 200000 |


## 3. Where the trigger loses Offline-reconstructable events

### CeM

Events with an Offline track of the same configuration (reconstructable level); each path classified by the last stage reached (stage jobs, debug output). Cells: events (percent).

| path: stage | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| apr_TrkDe_75m70p_D0200: pass | 3276 (93.4%) | 1207 (52.6%) | 1634 (70.4%) | 2170 (86.9%) | 1738 (69.6%) |
| apr_TrkDe_75m70p_D0200: TC | 2 (0.1%) | 1 (0.0%) | 4 (0.2%) | 10 (0.4%) | 10 (0.4%) |
| apr_TrkDe_75m70p_D0200: no helix | 160 (4.6%) | 841 (36.7%) | 487 (21.0%) | 35 (1.4%) | 539 (21.6%) |
| apr_TrkDe_75m70p_D0200: HS cuts | 49 (1.4%) | 113 (4.9%) | 165 (7.1%) | 235 (9.4%) | 192 (7.7%) |
| apr_TrkDe_75m70p_D0200: no fit | 3 (0.1%) | 4 (0.2%) | 9 (0.4%) | 18 (0.7%) | 4 (0.2%) |
| apr_TrkDe_75m70p_D0200: KS cuts | 16 (0.5%) | 127 (5.5%) | 21 (0.9%) | 28 (1.1%) | 13 (0.5%) |
| cpr_TrkDe_75m70p: pass | 2888 (82.4%) | 1464 (63.8%) | 1847 (79.6%) | 1965 (78.7%) | 1932 (77.4%) |
| cpr_TrkDe_75m70p: TC | 529 (15.1%) | 278 (12.1%) | 283 (12.2%) | 304 (12.2%) | 304 (12.2%) |
| cpr_TrkDe_75m70p: no helix | 31 (0.9%) | 168 (7.3%) | 46 (2.0%) | 55 (2.2%) | 55 (2.2%) |
| cpr_TrkDe_75m70p: HS cuts | 37 (1.1%) | 226 (9.9%) | 88 (3.8%) | 112 (4.5%) | 147 (5.9%) |
| cpr_TrkDe_75m70p: no fit | 3 (0.1%) | 7 (0.3%) | 28 (1.2%) | 33 (1.3%) | 31 (1.2%) |
| cpr_TrkDe_75m70p: KS cuts | 18 (0.5%) | 150 (6.5%) | 28 (1.2%) | 27 (1.1%) | 27 (1.1%) |
| **cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200: lost** | 99 (2.8%) | 517 (22.5%) | 187 (8.1%) | 130 (5.2%) | 243 (9.7%) |
| Offline events in the stage log | 3506 | 2293 | 2320 | 2496 | 2496 |

- nominal, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/no helix 12, KS cuts/KS cuts 3, KS cuts/no helix 5, TC/HS cuts 9, TC/no helix 43, no helix/no helix 10
- nominal, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 3, d0 12, lambda 3, lambda+p 15, nSH 3, nSH+hitRatio 5
- nominal, apr_TrkDe_75m70p_D0200, KS cuts: d0 1, nactive 15
- nominal, cpr_TrkDe_75m70p, HS cuts: chi2XY 5, hitRatio 3, nSH 15, nSH+chi2ZPhi+hitRatio 1, nSH+hitRatio 7, p 4
- nominal, cpr_TrkDe_75m70p, KS cuts: nactive 17, nactive+p 1
- reduced, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/KS cuts 17, HS cuts/no helix 112, KS cuts/KS cuts 17, KS cuts/no helix 98, TC/no helix 85, no helix/no helix 103
- reduced, apr_TrkDe_75m70p_D0200, HS cuts: d0 27, d0+hitRatio 5, lambda 12, lambda+p 4, nSH 37, nSH+hitRatio 7
- reduced, apr_TrkDe_75m70p_D0200, KS cuts: chi2dof 1, nactive 124, nactive+p+d0 1, nactive+p+momErr+d0 1
- reduced, cpr_TrkDe_75m70p, HS cuts: chi2XY 75, chi2ZPhi 9, nSH 74, nSH+chi2XY 6, nSH+hitRatio 29, p 6
- reduced, cpr_TrkDe_75m70p, KS cuts: nactive 149, nactive+p+momErr 1
- reduced_safe, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/HS cuts 8, HS cuts/no helix 38, KS cuts/no helix 14, TC/HS cuts 37, TC/no helix 46, no helix/no helix 16
- reduced_safe, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 14, d0 30, d0+lambda+p+hitRatio 15, hitRatio 5, lambda 46, lambda+p 25
- reduced_safe, apr_TrkDe_75m70p_D0200, KS cuts: nactive 15, nactive+d0 1, nactive+momErr 2, nactive+momErr+d0 2, p+d0 1
- reduced_safe, cpr_TrkDe_75m70p, HS cuts: chi2XY 16, hitRatio 30, nSH+hitRatio 4, nSH+p+hitRatio 4, p 18, p+hitRatio 9
- reduced_safe, cpr_TrkDe_75m70p, KS cuts: nactive 19, nactive+momErr 7, nactive+p 1, nactive+p+momErr 1
- reduced_recommended, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/HS cuts 25, KS cuts/KS cuts 6, TC/HS cuts 39, TC/no helix 5, no fit/HS cuts 7, no helix/HS cuts 17
- reduced_recommended, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 33, d0 53, d0+hitRatio 9, hitRatio 16, lambda 56, lambda+p 15
- reduced_recommended, apr_TrkDe_75m70p_D0200, KS cuts: d0 2, momErr 2, nactive 16, nactive+d0 2, nactive+momErr 3, p 1
- reduced_recommended, cpr_TrkDe_75m70p, HS cuts: chi2XY 22, hitRatio 31, nSH+hitRatio 10, nSH+p+hitRatio 6, p 18, p+hitRatio 11
- reduced_recommended, cpr_TrkDe_75m70p, KS cuts: chi2dof 1, momErr 1, nactive 17, nactive+momErr 6, nactive+p 2
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/HS cuts 15, HS cuts/no helix 51, KS cuts/no helix 14, TC/HS cuts 44, TC/no helix 58, no helix/no helix 25
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 24, d0 39, d0+hitRatio 7, d0+lambda+p+hitRatio 9, lambda 48, lambda+p 27
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, apr_TrkDe_75m70p_D0200, KS cuts: chi2dof 1, nactive 9, nactive+d0 1, nactive+p+d0 1, p 1
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, cpr_TrkDe_75m70p, HS cuts: chi2XY 49, chi2ZPhi 9, hitRatio 27, nSH+hitRatio 9, p 18, p+hitRatio 10
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, cpr_TrkDe_75m70p, KS cuts: chi2dof 1, momErr 1, nactive 17, nactive+momErr 6, nactive+p 2

### CeP

Events with an Offline track of the same configuration (reconstructable level); each path classified by the last stage reached (stage jobs, debug output). Cells: events (percent).

| path: stage | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| apr_TrkDe_75m70p_D0200: pass | 2466 (86.7%) | 449 (38.4%) | 768 (58.7%) | 1189 (81.0%) | 841 (57.3%) |
| apr_TrkDe_75m70p_D0200: TC | 9 (0.3%) | 1 (0.1%) | 5 (0.4%) | 10 (0.7%) | 10 (0.7%) |
| apr_TrkDe_75m70p_D0200: no helix | 264 (9.3%) | 571 (48.8%) | 419 (32.0%) | 45 (3.1%) | 476 (32.4%) |
| apr_TrkDe_75m70p_D0200: HS cuts | 70 (2.5%) | 56 (4.8%) | 102 (7.8%) | 190 (13.0%) | 131 (8.9%) |
| apr_TrkDe_75m70p_D0200: no fit | 4 (0.1%) | 3 (0.3%) | 7 (0.5%) | 12 (0.8%) | 2 (0.1%) |
| apr_TrkDe_75m70p_D0200: KS cuts | 31 (1.1%) | 89 (7.6%) | 7 (0.5%) | 20 (1.4%) | 7 (0.5%) |
| apr_TrkDe_75m70p_D0200: other | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 1 (0.1%) | 0 (0.0%) |
| cpr_TrkDe_75m70p: pass | 2111 (74.2%) | 596 (51.0%) | 923 (70.6%) | 1041 (71.0%) | 1016 (69.3%) |
| cpr_TrkDe_75m70p: TC | 601 (21.1%) | 187 (16.0%) | 194 (14.8%) | 219 (14.9%) | 219 (14.9%) |
| cpr_TrkDe_75m70p: no helix | 43 (1.5%) | 150 (12.8%) | 40 (3.1%) | 44 (3.0%) | 44 (3.0%) |
| cpr_TrkDe_75m70p: HS cuts | 57 (2.0%) | 141 (12.1%) | 110 (8.4%) | 104 (7.1%) | 131 (8.9%) |
| cpr_TrkDe_75m70p: no fit | 2 (0.1%) | 5 (0.4%) | 24 (1.8%) | 43 (2.9%) | 42 (2.9%) |
| cpr_TrkDe_75m70p: KS cuts | 30 (1.1%) | 90 (7.7%) | 17 (1.3%) | 15 (1.0%) | 14 (1.0%) |
| cpr_TrkDe_75m70p: other | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 1 (0.1%) | 1 (0.1%) |
| **cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200: lost** | 168 (5.9%) | 412 (35.2%) | 191 (14.6%) | 115 (7.8%) | 230 (15.7%) |
| Offline events in the stage log | 2844 | 1169 | 1308 | 1467 | 1467 |

- nominal, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/no helix 28, KS cuts/no helix 9, TC/HS cuts 25, TC/KS cuts 9, TC/no helix 62, no helix/no helix 13
- nominal, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 3, d0 8, lambda 19, lambda+p 17, nSH 10, p 4
- nominal, apr_TrkDe_75m70p_D0200, KS cuts: nactive 30, p 1
- nominal, cpr_TrkDe_75m70p, HS cuts: chi2XY 11, hitRatio 2, nSH 27, nSH+hitRatio 4, nSH+p 3, p 5
- nominal, cpr_TrkDe_75m70p, KS cuts: chi2dof 1, nactive 24, nactive+momErr 2, nactive+p 3
- reduced, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/no helix 94, KS cuts/KS cuts 17, KS cuts/no helix 57, TC/no helix 86, no helix/KS cuts 19, no helix/no helix 81
- reduced, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 3, d0 7, d0+p 2, lambda 4, lambda+p 5, nSH 24
- reduced, apr_TrkDe_75m70p_D0200, KS cuts: nactive 89
- reduced, cpr_TrkDe_75m70p, HS cuts: chi2XY 34, nSH 46, nSH+chi2XY 6, nSH+hitRatio 16, nSH+p+hitRatio 10, p 5
- reduced, cpr_TrkDe_75m70p, KS cuts: nactive 88, nactive+momErr 1, nactive+p 1
- reduced_safe, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/HS cuts 16, HS cuts/no helix 43, TC/HS cuts 26, TC/no helix 49, no fit/no helix 11, no helix/no helix 23
- reduced_safe, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 10, d0 16, d0+lambda+p+hitRatio 7, lambda 26, lambda+p 17, p 5
- reduced_safe, apr_TrkDe_75m70p_D0200, KS cuts: nactive 6, nactive+momErr 1
- reduced_safe, cpr_TrkDe_75m70p, HS cuts: chi2XY 18, chi2ZPhi+p+hitRatio 3, hitRatio 30, nSH+hitRatio 8, p 30, p+hitRatio 13
- reduced_safe, cpr_TrkDe_75m70p, KS cuts: nactive 11, nactive+momErr 5, nactive+p+momErr 1
- reduced_recommended, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/HS cuts 25, TC/HS cuts 33, TC/KS cuts 3, TC/no helix 4, no fit/HS cuts 10, no helix/HS cuts 11
- reduced_recommended, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 9, d0 30, hitRatio 14, lambda 62, lambda+hitRatio 12, lambda+p 16
- reduced_recommended, apr_TrkDe_75m70p_D0200, KS cuts: nactive 14, nactive+momErr 4, p 1, p+d0 1
- reduced_recommended, apr_TrkDe_75m70p_D0200, other: helix passes listed cuts 1
- reduced_recommended, cpr_TrkDe_75m70p, HS cuts: chi2XY 18, hitRatio 25, nSH+hitRatio 7, nSH+p+hitRatio 4, p 21, p+hitRatio 18
- reduced_recommended, cpr_TrkDe_75m70p, KS cuts: nactive 6, nactive+momErr 4, nactive+p 2, nactive+p+momErr 1, p 2
- reduced_recommended, cpr_TrkDe_75m70p, other: helix passes listed cuts 1
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 lost, stages (path 1/path 2): HS cuts/HS cuts 18, HS cuts/no helix 51, TC/HS cuts 29, TC/no helix 60, no fit/no helix 22, no helix/no helix 27
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, apr_TrkDe_75m70p_D0200, HS cuts: chi2XY 12, d0 22, d0+lambda+p+hitRatio 8, lambda 32, lambda+p 23, p 6
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, apr_TrkDe_75m70p_D0200, KS cuts: nactive 4, nactive+d0 1, nactive+momErr+d0 1, p+d0 1
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, cpr_TrkDe_75m70p, HS cuts: chi2XY 39, chi2ZPhi 6, chi2ZPhi+p+hitRatio 7, hitRatio 23, p 21, p+hitRatio 14
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, cpr_TrkDe_75m70p, KS cuts: nactive 6, nactive+momErr 3, nactive+p 2, nactive+p+momErr 1, p 2
- reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr, cpr_TrkDe_75m70p, other: helix passes listed cuts 1

## 4. Offline momentum resolution at the tracker entrance

### CeM

dp = p_fit - p_MC at TT_Front of the CE track; sigma68 = half the 16-84% range [MeV/c]; tail = fraction with |dp| > 1 MeV/c. Quality = nactive/nhits > 0.8, fitcon > 0.001, t0err < 0.9 ns, momerr < 0.5 MeV/c. Cells: sigma68 / tail (tracks).

| selection | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| all | 0.23 / 7.7% (3633) | 0.43 / 12.4% (2549) | 0.44 / 12.5% (2618) | 0.44 / 13.7% (2923) | 0.44 / 13.7% (2923) |
| quality | 0.19 / 3.2% (2763) | 0.32 / 5.0% (1648) | 0.32 / 4.9% (1590) | 0.31 / 4.6% (1876) | 0.31 / 4.6% (1876) |
| quality: fraction kept | 76% | 65% | 61% | 64% | 64% |

By N(active) region, all tracks:

| region | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| N(active) 15-19 | 0.41 / 10.1% (258) | 0.51 / 13.2% (554) | 0.56 / 13.9% (591) | 0.54 / 13.2% (619) | 0.54 / 13.2% (619) |
| N(active) 20-24 | 0.31 / 7.6% (384) | 0.43 / 9.9% (618) | 0.43 / 8.7% (621) | 0.41 / 10.4% (672) | 0.41 / 10.4% (672) |
| N(active) 25-29 | 0.26 / 7.3% (454) | 0.30 / 7.7% (507) | 0.33 / 7.0% (512) | 0.29 / 6.1% (526) | 0.29 / 6.1% (526) |
| N(active) 30-39 | 0.21 / 6.4% (983) | 0.26 / 6.0% (514) | 0.27 / 5.3% (491) | 0.25 / 5.2% (557) | 0.25 / 5.2% (557) |
| N(active) <15 | 2.03 / 45.5% (110) | 1.39 / 42.5% (252) | 1.60 / 40.5% (294) | 1.48 / 41.7% (422) | 1.48 / 41.7% (422) |
| N(active) >=40 | 0.19 / 5.3% (1444) | 0.26 / 5.8% (104) | 0.29 / 8.3% (109) | 0.31 / 7.9% (127) | 0.31 / 7.9% (127) |

By N(active) region, quality cuts:

| region | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| N(active) 15-19 | 0.28 / 3.1% (159) [62% kept] | 0.44 / 6.3% (303) [55% kept] | 0.43 / 7.7% (300) [51% kept] | 0.37 / 5.5% (366) [59% kept] | 0.37 / 5.5% (366) [59% kept] |
| N(active) 20-24 | 0.26 / 3.0% (298) [78% kept] | 0.38 / 5.4% (428) [69% kept] | 0.37 / 5.0% (418) [67% kept] | 0.36 / 5.4% (503) [75% kept] | 0.36 / 5.4% (503) [75% kept] |
| N(active) 25-29 | 0.20 / 3.5% (342) [75% kept] | 0.27 / 4.9% (387) [76% kept] | 0.29 / 4.3% (376) [73% kept] | 0.29 / 4.1% (415) [79% kept] | 0.29 / 4.1% (415) [79% kept] |
| N(active) 30-39 | 0.18 / 3.2% (784) [80% kept] | 0.22 / 4.3% (417) [81% kept] | 0.22 / 3.6% (387) [79% kept] | 0.22 / 3.7% (456) [82% kept] | 0.22 / 3.7% (456) [82% kept] |
| N(active) <15 | 0.37 / 8.7% (23) [21% kept] | 0.42 / 2.9% (35) [14% kept] | 0.38 / 0.0% (28) [10% kept] | 0.44 / 4.4% (45) [11% kept] | 0.44 / 4.4% (45) [11% kept] |
| N(active) >=40 | 0.15 / 3.1% (1157) [80% kept] | 0.21 / 2.6% (78) [75% kept] | 0.23 / 4.9% (81) [74% kept] | 0.24 / 3.3% (91) [72% kept] | 0.24 / 3.3% (91) [72% kept] |

### CeP

dp = p_fit - p_MC at TT_Front of the CE track; sigma68 = half the 16-84% range [MeV/c]; tail = fraction with |dp| > 1 MeV/c. Quality = nactive/nhits > 0.8, fitcon > 0.001, t0err < 0.9 ns, momerr < 0.5 MeV/c. Cells: sigma68 / tail (tracks).

| selection | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| all | 0.34 / 10.4% (3072) | 0.62 / 19.9% (1433) | 0.62 / 20.0% (1634) | 0.70 / 22.7% (2053) | 0.70 / 22.7% (2053) |
| quality | 0.24 / 2.5% (2058) | 0.36 / 5.0% (702) | 0.34 / 4.7% (745) | 0.35 / 4.6% (958) | 0.35 / 4.6% (958) |
| quality: fraction kept | 67% | 49% | 46% | 47% | 47% |

By N(active) region, all tracks:

| region | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| N(active) 15-19 | 0.68 / 19.0% (462) | 0.66 / 20.9% (478) | 0.66 / 19.2% (573) | 0.70 / 19.6% (627) | 0.70 / 19.6% (627) |
| N(active) 20-24 | 0.37 / 6.0% (514) | 0.42 / 9.0% (377) | 0.40 / 8.7% (415) | 0.39 / 7.2% (473) | 0.39 / 7.2% (473) |
| N(active) 25-29 | 0.27 / 6.5% (510) | 0.30 / 6.8% (206) | 0.34 / 6.6% (213) | 0.35 / 7.2% (236) | 0.35 / 7.2% (236) |
| N(active) 30-39 | 0.22 / 3.4% (825) | 0.26 / 6.8% (103) | 0.27 / 5.9% (101) | 0.22 / 4.8% (124) | 0.22 / 4.8% (124) |
| N(active) <15 | 1.82 / 53.3% (225) | 1.51 / 49.2% (264) | 1.84 / 49.1% (326) | 1.72 / 48.8% (586) | 1.72 / 48.8% (586) |
| N(active) >=40 | 0.20 / 3.9% (536) | 0.23 / 0.0% (5) | 0.17 / 0.0% (6) | 0.13 / 0.0% (7) | 0.13 / 0.0% (7) |

By N(active) region, quality cuts:

| region | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| N(active) 15-19 | 0.44 / 5.1% (215) [47% kept] | 0.48 / 8.6% (185) [39% kept] | 0.44 / 5.9% (205) [36% kept] | 0.47 / 6.2% (272) [43% kept] | 0.47 / 6.2% (272) [43% kept] |
| N(active) 20-24 | 0.30 / 2.2% (357) [69% kept] | 0.36 / 3.8% (260) [69% kept] | 0.37 / 4.9% (285) [69% kept] | 0.34 / 4.2% (355) [75% kept] | 0.34 / 4.2% (355) [75% kept] |
| N(active) 25-29 | 0.23 / 2.3% (388) [76% kept] | 0.28 / 4.3% (163) [79% kept] | 0.29 / 5.1% (157) [74% kept] | 0.28 / 3.2% (185) [78% kept] | 0.28 / 3.2% (185) [78% kept] |
| N(active) 30-39 | 0.19 / 1.9% (648) [79% kept] | 0.21 / 2.5% (80) [78% kept] | 0.24 / 1.2% (81) [80% kept] | 0.23 / 4.6% (109) [88% kept] | 0.23 / 4.6% (109) [88% kept] |
| N(active) <15 | 0.29 / 8.7% (23) [10% kept] | 0.31 / 0.0% (10) [4% kept] | 0.21 / 0.0% (13) [4% kept] | 0.33 / 3.0% (33) [6% kept] | 0.33 / 3.0% (33) [6% kept] |
| N(active) >=40 | 0.16 / 2.1% (427) [80% kept] | 0.12 / 0.0% (4) [80% kept] | 0.11 / 0.0% (4) [67% kept] | 0.13 / 0.0% (4) [57% kept] | 0.13 / 0.0% (4) [57% kept] |

## 5. Cosmic signal efficiency

### Cosmic

Signal particle p > 75 MeV/c; percent of the category's MC-triggerable events ± binomial error, (x%) = fraction of nominal.

| path | category | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|---|
| cpr_TrkDe_75m70p | all | 15.5 ± 0.3 | 6.2 ± 0.2 (40%) | 10.1 ± 0.3 (65%) | 10.3 ± 0.3 (66%) | 10.1 ± 0.3 (65%) |
| apr_TrkDe_75m70p | all | 48.2 ± 0.4 | 16.9 ± 0.3 (35%) | 26.3 ± 0.4 (55%) | 37.4 ± 0.4 (78%) | 26.6 ± 0.4 (55%) |
| apr_TrkDe_75m70p_D0200 | all | 11.4 ± 0.3 | 5.8 ± 0.2 (51%) | 8.0 ± 0.2 (71%) | 10.2 ± 0.3 (90%) | 8.1 ± 0.2 (71%) |
| apr_TrkUe_80m70p | all | 45.2 ± 0.4 | 15.7 ± 0.3 (35%) | 21.2 ± 0.4 (47%) | 27.8 ± 0.4 (62%) | 21.5 ± 0.4 (48%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 | electron down | 52.6 ± 1.4 | 25.1 ± 1.2 (48%) | 33.4 ± 1.3 (63%) | 37.4 ± 1.3 (71%) | 33.9 ± 1.3 (65%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 | electron up | 34.8 ± 1.9 | 17.1 ± 1.4 (49%) | 25.8 ± 1.6 (74%) | 27.5 ± 1.7 (79%) | 23.8 ± 1.6 (68%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 | muon down | 16.1 ± 0.5 | 7.1 ± 0.4 (44%) | 9.8 ± 0.4 (61%) | 11.9 ± 0.5 (74%) | 10.4 ± 0.5 (64%) |
| cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200 | muon up | 19.5 ± 0.5 | 8.4 ± 0.3 (43%) | 13.8 ± 0.4 (71%) | 15.4 ± 0.5 (79%) | 13.8 ± 0.4 (71%) |
| events (all / MC-triggerable) |  | 13283 / 16774 | 12953 / 16774 | 12953 / 16774 | 12953 / 16774 | 12953 / 16774 |

## 6. Trigger CPU time

### NoPrimary

Per-event time summed over the modules of the studied trigger paths, without the data read (Prefetch), the re-digitization emulation (makeSD, TriggerableTrigger), art's own modules and outputs; first event of the job skipped. Single thread.

| quantity | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| mean [ms] | 0.972 | 0.868 (x0.89) | 0.836 (x0.86) | 1.087 (x1.12) | 0.719 (x0.74) |
| median [ms] | 0.869 | 0.790 | 0.747 | 0.752 | 0.636 |
| p90 [ms] | 1.473 | 1.286 | 1.229 | 1.669 | 1.075 |
| p99 [ms] | 2.789 | 2.255 | 2.317 | 7.122 | 2.080 |
| max [ms] | 8.343 | 12.795 | 12.301 | 30.508 | 10.265 |
| events | 15999 | 15999 | 15999 | 15999 | 15999 |

Largest modules, mean per event [ms]:

| module | nominal | reduced | reduced_safe | reduced_recommended | reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr |
|---|---|---|---|---|---|
| TrigFlagPH | 0.201 | 0.155 | 0.156 | 0.157 | 0.135 |
| TrigMakeSH | 0.177 | 0.129 | 0.137 | 0.127 | 0.114 |
| TrigAprKSF | 0.010 | 0.004 | 0.010 | 0.137 | 0.008 |
| CaloHitMakerFast | 0.114 | 0.121 | 0.118 | 0.117 | 0.100 |
| TrigAprUeKSF | 0.007 | 0.004 | 0.007 | 0.104 | 0.007 |
| TrigTZClusterFinder | 0.075 | 0.072 | 0.064 | 0.065 | 0.057 |
| TrigAprHelixFinder | 0.071 | 0.069 | 0.041 | 0.062 | 0.037 |
| TrigMakePH | 0.066 | 0.053 | 0.049 | 0.046 | 0.042 |

## 7. Provenance and configurations

7 provenance record(s); last: 2026-11-06T14:22:33Z on mu2esrv01.fnal.gov (user mmackenz), muse build `al9-prof-e29-p109`.

Release backing chain of the work area: `/cvmfs/mu2e.opensciencegrid.org/Musings/AnalysisMDC2025/v02_03_01` -> `/cvmfs/mu2e.opensciencegrid.org/Musings/SimJob/MDC2025bb` -> `/cvmfs/mu2e.opensciencegrid.org/Musings/Offline/v13_43_00`

| repository | HEAD | branch | dirty | diff hash |
|---|---|---|---|---|
| TrkCondTuning | d49b1e5a23 | main | no |  |


Configurations:

| configuration | condition | settings |
|---|---|---|
| nominal | nominal (Sim_best v1_3) | - |
| reduced | reduced_tracker_2026 (Sim_best v1_5) | - |
| reduced_safe | reduced_tracker_2026 (Sim_best v1_5) | safe, tdres20, cprchi2 |
| reduced_recommended | reduced_tracker_2026 (Sim_best v1_5) | cpr_finder_minhits7, nsh10_cpr, nsh10_apr, apr_finder_minima, cprchi2, apr_cand3a20, apr_alias100, apr_phiz2, apr_tgtrep100, offline_helix_loose, calib |
| reduced_tracker_2026+calib+offline_helix_loose+nsh10_cpr+cpr_finder_minhits7+nsh10_apr | reduced_tracker_2026 (as baseline) | calib, offline_helix_loose, nsh10_cpr, cpr_finder_minhits7, nsh10_apr |

Study `reduced_tracker_2026_10`: trigger paths cpr_TrkDe_75m70p, cpr_TrkDe_75m70p_D0200, cpr_TrkDe_80m70p, cpr_TrkDe_80m70p_D0200, apr_TrkDe_75m70p, apr_TrkDe_75m70p_D0200, apr_TrkDe_80m70p, apr_TrkDe_80m70p_D0200, apr_TrkUe_80m70p; objective cpr_TrkDe_75m70p OR apr_TrkDe_75m70p_D0200.
