# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25 – **ADDED FEATURE**: `temp_lag_1`, which is yesterday's temperature. It only uses information from the day before, making it available when we make a prediction. It also costs us no extra rows. **REASONING**: Weather tends to carry over from one day to the next. Yesterday's temperature may add context that today's temperature alone does not. **VALIDATION**: Ridge R^2 went from 0.6475 to 0.6951. Its average error went from 832.9 to 746.1 rides. Gradient boosting (hgb) R^2 went from 0.2185 to 0.1936. Its average error went from 1296.6 to 1321.1 rides. **DECISION**: Keep it. **JUSTIFICATION**: Ridge improved by far more than the 0.01 that could just be random noise. Hgb got a little worse, and I am reporting that instead of hiding it. Hgb was already struggling because 2012 ridership is higher than anything it saw in 2011.
