# MTCC backend benchmark: MIR/c2mir vs TinyCC

Baseline for ratio columns: **tcc** (current mtcc backend).

## 1. Synthetic build-time stress test (300 files, -c only)

| compiler | batch total (s) | avg/file (s) | peak RSS (MB) | vs tcc (batch) | failures |
|---|---|---|---|---|---|
| c2m | 19.819 | 0.0659 | 6.3 | 0.42x | 0 |
| tcc | 47.569 | 0.1584 | 8.1 | 1.00x | 0 |
| gcc | 86.356 | 0.2877 | 68.0 | 1.82x | 0 |
| clang | 47.317 | 0.1576 | 37.5 | 0.99x | 0 |

## 2. Interpreted/JIT micro-benchmarks

`jit` = single-shot build+run combined (c2m `-eg`, tcc `-run`). `build` / `run` = ahead-of-time compile step and standalone execution, timed separately (c2m via `-c` then `mir-bin-run`; tcc/gcc/clang via compile-to-binary then execute).

### fib

| compiler | jit (s) | build (s) | run (s) | build+run vs tcc jit | peak RSS build (MB) | peak RSS run (MB) |
|---|---|---|---|---|---|---|
| c2m | 0.2670 | 0.1074 | 0.2178 | 0.96x | 23.3 | 3.4 |
| tcc | 0.2787 | 0.2704 | 0.1811 | 1.00x | 10.5 | 1.9 |
| gcc | n/a | 1.0787 | 0.0928 | 4.20x | 67.6 | 1.9 |
| clang | n/a | 0.2572 | 0.1329 | 1.40x | 49.6 | 1.9 |

### mandelbrot

| compiler | jit (s) | build (s) | run (s) | build+run vs tcc jit | peak RSS build (MB) | peak RSS run (MB) |
|---|---|---|---|---|---|---|
| c2m | 0.7757 | 0.1065 | 0.7250 | 0.51x | 23.5 | 3.1 |
| tcc | 1.5115 | 0.2612 | 1.4185 | 1.00x | 10.5 | 1.9 |
| gcc | n/a | 0.7340 | 0.6010 | 0.88x | 67.7 | 1.9 |
| clang | n/a | 0.2322 | 0.5374 | 0.51x | 50.9 | 1.9 |

### quicksort

| compiler | jit (s) | build (s) | run (s) | build+run vs tcc jit | peak RSS build (MB) | peak RSS run (MB) |
|---|---|---|---|---|---|---|
| c2m | 0.5307 | 0.1081 | 0.4865 | 0.68x | 23.5 | 4.0 |
| tcc | 0.7853 | 0.2623 | 0.6874 | 1.00x | 10.5 | 2.8 |
| gcc | n/a | 0.7626 | 0.4169 | 1.50x | 67.7 | 2.7 |
| clang | n/a | 0.2302 | 0.4091 | 0.81x | 52.2 | 2.7 |

### sieve

| compiler | jit (s) | build (s) | run (s) | build+run vs tcc jit | peak RSS build (MB) | peak RSS run (MB) |
|---|---|---|---|---|---|---|
| c2m | 0.3481 | 0.1057 | 0.3043 | 0.47x | 23.4 | 4.1 |
| tcc | 0.7339 | 0.2608 | 0.6449 | 1.00x | 10.5 | 3.0 |
| gcc | n/a | 0.7442 | 0.2252 | 1.32x | 67.5 | 2.9 |
| clang | n/a | 0.2315 | 0.2632 | 0.67x | 52.5 | 2.9 |
