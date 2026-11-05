# Result summary

MPKI = conditional-branch mispredictions per 1000 instructions (trace-driven, 20M warmup + 100M measured). IPC from ChampSim (10M warmup + 10M simulated).

## Baseline MPKI

| trace | bimodal | gshare | TAGE | TAGE vs gshare |
|---|---|---|---|---|
| perlbench | 3.31 | 2.92 | 0.90 | -69% |
| gcc | 12.28 | 0.37 | 0.29 | -21% |
| mcf | 27.76 | 22.34 | 19.14 | -14% |
| xalancbmk | 6.59 | 4.57 | 0.79 | -83% |
| x264 | 4.83 | 0.85 | 0.14 | -83% |
| deepsjeng | 13.59 | 10.18 | 5.51 | -46% |
| leela | 20.48 | 18.52 | 13.11 | -29% |
| xz | 10.78 | 12.31 | 6.19 | -50% |
| **mean** | **12.45** | **9.00** | **5.76** | **-36%** |

## Storage budget (mean MPKI)

| predictor | storage KB | mean MPKI |
|---|---|---|
| bimodal | 2.00 | 12.50 |
| bimodal | 4.00 | 12.45 |
| bimodal | 8.00 | 12.41 |
| bimodal | 16.00 | 12.39 |
| bimodal | 32.00 | 12.39 |
| bimodal | 64.00 | 12.39 |
| gshare | 2.00 | 8.73 |
| gshare | 4.00 | 8.04 |
| gshare | 8.00 | 7.51 |
| gshare | 16.00 | 7.19 |
| gshare | 32.00 | 6.91 |
| gshare | 64.00 | 6.76 |
| TAGE | 2.25 | 6.34 |
| TAGE | 4.50 | 6.00 |
| TAGE | 9.00 | 5.76 |
| TAGE | 18.00 | 5.58 |
| TAGE | 36.00 | 5.44 |
| TAGE | 72.00 | 5.33 |

## Number of tagged tables

| config | tables | storage KB | mean MPKI |
|---|---|---|---|
| tage_n1 | 1 | 3.75 | 7.59 |
| tage_n2 | 2 | 5.50 | 6.74 |
| tage_n3 | 3 | 7.25 | 6.05 |
| tage | 4 | 9.00 | 5.76 |
| tage_n6 | 6 | 12.50 | 5.53 |
| tage_n8 | 8 | 16.00 | 5.45 |
| tage_16k_n1 | 1 | 16.00 | 6.62 |
| tage_16k_n2 | 2 | 16.00 | 6.46 |
| tage_16k_n4 | 4 | 16.00 | 5.58 |
| tage_16k_n8 | 8 | 16.00 | 5.45 |
| tage_16k_n16 | 16 | 16.00 | 5.52 |

## History lengths (4 tables, 9 KB)

| config | lengths | mean MPKI |
|---|---|---|
| tage_lmax16 | 5,7,11,16 | 6.42 |
| tage_lmax32 | 5,9,17,32 | 6.03 |
| tage_lmax64 | 5,12,27,64 | 5.84 |
| tage | 5,15,44,130 | 5.76 |
| tage_lmax256 | 5,19,69,256 | 5.82 |
| tage_lmax512 | 5,23,109,512 | 5.92 |
| tage_lmax1024 | 5,29,174,1024 | 6.04 |
| tage_lmin2 | 2,8,32,130 | 5.89 |
| tage | 5,15,44,130 | 5.76 |
| tage_lmin10 | 10,24,55,130 | 5.80 |
| tage_lmin20 | 20,37,70,130 | 6.18 |
| tage_linear | 5,47,88,130 | 6.19 |

## Partial tag width

| tag bits | storage KB | mean MPKI |
|---|---|---|
| 4 | 6.50 | 6.99 |
| 6 | 7.50 | 6.03 |
| 8 | 8.50 | 5.80 |
| 9 | 9.00 | 5.76 |
| 11 | 10.00 | 5.73 |
| 13 | 11.00 | 5.73 |
