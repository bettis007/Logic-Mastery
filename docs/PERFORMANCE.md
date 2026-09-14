# Local performance evidence

Measured September 14, 2026. Synthetic inputs; Linux CPU process, not cloud, GPU or Jetson validation.

Environment: Python 3.12.14, numpy 2.3.5, scikit-learn 1.8.0, x86_64. Whole-process peak RSS: 122.44 MiB.

| Batch | Rebuild median ms (5 runs) | Warm median ms (9 runs) | Ratio | Serialization median ms |
|---|---:|---:|---:|---:|
| 13 | 154.583 | 0.381 | 405.66x | 0.045 |
| 100 | 148.749 | 1.351 | 110.11x | 0.304 |
| 1000 | 154.155 | 7.137 | 21.60x | 3.161 |

For each batch, the uncached and first/warm cached results are exactly equal. The ratio primarily removes repeated training/calibration/selection cost; classifier mathematics are unchanged. Initial model startup, imports, HTTP transfer, browser rendering and multi-user load are not represented by warm timings. These small timing samples do not establish statistical population confidence intervals.

RSS is a Linux whole-process high-water mark, not incremental model memory. Full timing samples and first cached request costs follow.

```json
{
  "scope": "Measured local CPU wall-clock timings; synthetic inputs; not Google Cloud or Jetson performance.",
  "python": "3.12.14",
  "numpy": "2.3.5",
  "scikit_learn": "1.8.0",
  "machine": "x86_64",
  "peak_process_rss_mib": 122.44140625,
  "note": "RSS is whole-process high-water mark on Linux; warm cache retains one model; timing samples are not independent population estimates.",
  "results": [
    {
      "cases": 13,
      "rebuild_each_request": {
        "median_ms": 154.5828270027414,
        "min_ms": 138.5041719986475,
        "max_ms": 155.70156399917323,
        "samples_ms": [
          155.70156399917323,
          154.5828270027414,
          155.54050500213634,
          149.83009599745856,
          138.5041719986475
        ]
      },
      "cached_request": {
        "median_ms": 0.38106100328150205,
        "min_ms": 0.3407990006962791,
        "max_ms": 1.0408599991933443,
        "samples_ms": [
          0.6224259996088222,
          0.47307799832196906,
          0.3734929996426217,
          0.38106100328150205,
          0.3407990006962791,
          1.0408599991933443,
          0.36900800114381127,
          0.5313250003382564,
          0.342973002261715
        ]
      },
      "first_cached_request_ms": 142.4587170004088,
      "serialization": {
        "median_ms": 0.04495100074564107,
        "min_ms": 0.041802999476203695,
        "max_ms": 0.17165900135296397,
        "samples_ms": [
          0.17165900135296397,
          0.05435999992187135,
          0.0706430000718683,
          0.04566599818645045,
          0.04495100074564107,
          0.043189997086301446,
          0.04262400034349412,
          0.041825001972028986,
          0.041802999476203695
        ]
      },
      "identical_records": true,
      "median_speedup": 405.6642523678711
    },
    {
      "cases": 100,
      "rebuild_each_request": {
        "median_ms": 148.74871099891607,
        "min_ms": 131.72913199741743,
        "max_ms": 155.952901001001,
        "samples_ms": [
          155.952901001001,
          131.72913199741743,
          143.45299799970235,
          148.94546900177374,
          148.74871099891607
        ]
      },
      "cached_request": {
        "median_ms": 1.350904996797908,
        "min_ms": 0.9866620021057315,
        "max_ms": 2.1024880006734747,
        "samples_ms": [
          1.6282729993690737,
          1.350904996797908,
          2.1024880006734747,
          1.692013000138104,
          1.1822839987871703,
          1.1802480003098026,
          0.9866620021057315,
          1.8219489975308534,
          1.116866998927435
        ]
      },
      "first_cached_request_ms": 134.27608300116844,
      "serialization": {
        "median_ms": 0.3039010007341858,
        "min_ms": 0.27567799770622514,
        "max_ms": 0.7660519986529835,
        "samples_ms": [
          0.3999450018454809,
          0.7660519986529835,
          0.2899569990404416,
          0.27882099675480276,
          0.3039010007341858,
          0.2777310000965372,
          0.31506400046055205,
          0.305266999930609,
          0.27567799770622514
        ]
      },
      "identical_records": true,
      "median_speedup": 110.11041587047183
    },
    {
      "cases": 1000,
      "rebuild_each_request": {
        "median_ms": 154.15451899752952,
        "min_ms": 152.13463899999624,
        "max_ms": 175.39167600261862,
        "samples_ms": [
          154.15451899752952,
          153.24078800040297,
          152.13463899999624,
          175.39167600261862,
          172.88538399952813
        ]
      },
      "cached_request": {
        "median_ms": 7.13719000123092,
        "min_ms": 6.623494999075774,
        "max_ms": 8.56464200114715,
        "samples_ms": [
          8.430586000031326,
          7.13719000123092,
          7.015705003141193,
          7.396663000690751,
          7.623883997439407,
          6.623494999075774,
          8.56464200114715,
          6.744338999851607,
          7.127034001314314
        ]
      },
      "first_cached_request_ms": 138.89305900011095,
      "serialization": {
        "median_ms": 3.1609700017725118,
        "min_ms": 2.9449730027408805,
        "max_ms": 3.696535000926815,
        "samples_ms": [
          3.0143360017973464,
          3.1609700017725118,
          3.4825399998226203,
          2.9449730027408805,
          3.696535000926815,
          3.113650996965589,
          3.3068699995055795,
          3.4581309992063325,
          3.0342820027726702
        ]
      },
      "identical_records": true,
      "median_speedup": 21.59876911935134
    }
  ]
}
```
