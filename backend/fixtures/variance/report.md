# Variance report

5 runs per query, cache disabled, run sequentially.

| query | verdict flips | empty runs | pulse spread | findings recurring in all runs | ratios >2x | unstable fields | median |
|---|---|---|---|---|---|---|---|
| Developer tools for edge functions | no | 0 | 0 | 2% | 13 | 28 | 29.8s |
| AI note-taking for clinicians | **YES** | 0 | 92 | 0% | 24 | 40 | 33.9s |
| Carbon accounting for SMBs | no | 2 | 75 | 0% | 14 | 35 | 27.8s |

Median of per-query medians: **29.8s**

> **The verdict flips between identical runs.** This is a product-level finding, not a rendering bug.

> **2 of 15 runs returned an empty briefing** and were served as a `Monitor` verdict with confidence 0. `Monitor` is the fallback default in `normalise_synthesis`, so a total parse failure is presented to the reader as a considered recommendation, with the full evidence list still rendered beneath it.

## Developer tools for edge functions

5 runs. 222 stable, 43 drifting, 28 unstable, of 293 leaf fields.

### The four questions

**1. Does the verdict flip?** No — decisions: ['Strong Yes', 'Strong Yes', 'Strong Yes', 'Strong Yes', 'Strong Yes']

All runs produced a real synthesis.

**2. Does market_pulse vary by more than 15 points?** No — values [76, 76, 76, 76, 76], spread 0

**3. Insight-list recurrence across all runs:**

Counted two ways. *Exact* is identical label text. *Findings* clusters labels that name the same thing in different words, which is the fairer measure -- the model rephrases every run.

| list | distinct findings | in all runs | in most runs | exact matches |
|---|---|---|---|---|
| customer_segments | 11 | 0 (0%) | 2 (18%) | 0 |
| desired_outcomes | 16 | 0 (0%) | 1 (6%) | 0 |
| behavior_patterns | 16 | 0 (0%) | 0 (0%) | 0 |
| opportunity_areas | 16 | 0 (0%) | 1 (6%) | 0 |
| key_trends | 16 | 0 (0%) | 1 (6%) | 0 |
| emerging_trends | 12 | 0 (0%) | 0 (0%) | 0 |
| market_drivers | 17 | 0 (0%) | 0 (0%) | 0 |
| competitors | 9 | 0 (0%) | 3 (33%) | 0 |
| competitive_threats | 11 | 0 (0%) | 2 (18%) | 0 |
| positioning_gaps | 13 | 0 (0%) | 1 (8%) | 0 |
| white_space_opportunities | 11 | 0 (0%) | 1 (9%) | 0 |
| key_opportunities | 12 | 0 (0%) | 1 (8%) | 0 |
| key_risks | 12 | 0 (0%) | 1 (8%) | 0 |
| execution_ideas | 15 | 0 (0%) | 0 (0%) | 0 |
| pain_points | 14 | 1 (7%) | 2 (14%) | 0 |
| differentiation_opportunities | 12 | 1 (8%) | 1 (8%) | 0 |
| why_now | 10 | 1 (10%) | 1 (10%) | 0 |
| potential_moats | 9 | 1 (11%) | 3 (33%) | 0 |

Mean recurrence in **all** 5 runs: **2%**
Mean recurrence in **most** runs: **10%**

**4. Fields with a max/min ratio above 2:**

| field | min | max | ratio |
|---|---|---|---|
| `report.signals.virality.avg_views_per_day.value` | 2 | 280 | 140.0x |
| `signals.virality.avg_views_per_day` | 2.05 | 279.51 | 136.35x |
| `signals.customer.comment_volume` | 13 | 534 | 41.08x |
| `report.signals.customer.comment_volume.value` | 13 | 534 | 41.08x |
| `signals.market_opportunity.market_size_mentions` | 1 | 4 | 4.0x |
| `signals.market_size.market_reports` | 1 | 4 | 4.0x |
| `report.signals.market_size.market_reports.value` | 1 | 4 | 4.0x |
| `report.signals.market_opportunity.mentions.counts.market_size_mentions` | 1 | 4 | 4.0x |
| `signals.market_opportunity.forecast_mentions` | 2 | 5 | 2.5x |
| `signals.market_opportunity.cagr_mentions` | 2 | 5 | 2.5x |
| `report.signals.market_opportunity.mentions.counts.forecast_mentions` | 2 | 5 | 2.5x |
| `report.signals.market_opportunity.mentions.counts.cagr_mentions` | 2 | 5 | 2.5x |
| `signals.virality.avg_engagement_rate` | 1.8 | 3.77 | 2.09x |

### Executive summary, first 80 chars per run

1. The market for developer tools for edge functions is experiencing exponential gr
2. The market for developer tools for edge functions is robust and growing, driven 
3. The market for developer tools for edge functions is in a strong growth phase, d
4. The market for developer tools for edge functions is in a growth stage with high
5. The developer tools for edge functions market is in a strong growth phase, proje

### Unstable fields

- `intelligence.market.growth_rate.confidence` — {"min": 75, "max": 90, "spread": 15, "ratio": 1.2}
- `intelligence.market.market_maturity.confidence` — {"min": 75, "max": 90, "spread": 15, "ratio": 1.2}
- `intelligence.market.market_size.confidence` — {"min": 50, "max": 90, "spread": 40, "ratio": 1.8}
- `report.market.future_outlook.source_count` — {"min": 3, "max": 6, "spread": 3, "ratio": 2.0}
- `report.market.growth_rate.confidence` — {"min": 75, "max": 90, "spread": 15, "ratio": 1.2}
- `report.market.growth_rate.source_count` — {"min": 3, "max": 6, "spread": 3, "ratio": 2.0}
- `report.market.market_maturity.confidence` — {"min": 75, "max": 90, "spread": 15, "ratio": 1.2}
- `report.market.market_maturity.source_count` — {"min": 3, "max": 6, "spread": 3, "ratio": 2.0}
- `report.market.market_size.confidence` — {"min": 50, "max": 90, "spread": 40, "ratio": 1.8}
- `report.market.market_size.source_count` — {"min": 3, "max": 6, "spread": 3, "ratio": 2.0}
- `report.signals.customer.comment_volume.value` — {"min": 13, "max": 534, "spread": 521, "ratio": 41.08}
- `report.signals.market_opportunity.mentions.counts.billion_mentions` — {"min": 0, "max": 4, "spread": 4, "ratio": null}
- `report.signals.market_opportunity.mentions.counts.cagr_mentions` — {"min": 2, "max": 5, "spread": 3, "ratio": 2.5}
- `report.signals.market_opportunity.mentions.counts.forecast_mentions` — {"min": 2, "max": 5, "spread": 3, "ratio": 2.5}
- `report.signals.market_opportunity.mentions.counts.market_size_mentions` — {"min": 1, "max": 4, "spread": 3, "ratio": 4.0}
- `report.signals.market_opportunity.mentions.counts.million_mentions` — {"min": 0, "max": 1, "spread": 1, "ratio": null}
- `report.signals.market_size.market_reports.value` — {"min": 1, "max": 4, "spread": 3, "ratio": 4.0}
- `report.signals.virality.avg_engagement_rate.value` — {"min": 2, "max": 4, "spread": 2, "ratio": 2.0}
- `report.signals.virality.avg_views_per_day.value` — {"min": 2, "max": 280, "spread": 278, "ratio": 140.0}
- `signals.customer.comment_volume` — {"min": 13, "max": 534, "spread": 521, "ratio": 41.08}
- `signals.market_opportunity.billion_mentions` — {"min": 0, "max": 4, "spread": 4, "ratio": null}
- `signals.market_opportunity.cagr_mentions` — {"min": 2, "max": 5, "spread": 3, "ratio": 2.5}
- `signals.market_opportunity.forecast_mentions` — {"min": 2, "max": 5, "spread": 3, "ratio": 2.5}
- `signals.market_opportunity.market_size_mentions` — {"min": 1, "max": 4, "spread": 3, "ratio": 4.0}
- `signals.market_opportunity.million_mentions` — {"min": 0, "max": 1, "spread": 1, "ratio": null}
- `signals.market_size.market_reports` — {"min": 1, "max": 4, "spread": 3, "ratio": 4.0}
- `signals.virality.avg_engagement_rate` — {"min": 1.8, "max": 3.77, "spread": 1.97, "ratio": 2.09}
- `signals.virality.avg_views_per_day` — {"min": 2.05, "max": 279.51, "spread": 277.46, "ratio": 136.35}

### Timing

per-run total: [31.8, 31.9, 27.0, 29.8, 29.8]
median: **29.8s**

## AI note-taking for clinicians

5 runs. 203 stable, 50 drifting, 40 unstable, of 293 leaf fields.

### The four questions

**1. Does the verdict flip?** YES — decisions: ['Strong Yes', 'Strong Yes', 'Yes', 'Strong Yes', 'Strong Yes']

All runs produced a real synthesis.

**2. Does market_pulse vary by more than 15 points?** YES — values [8, 100, 100, 94, 100], spread 92

**3. Insight-list recurrence across all runs:**

Counted two ways. *Exact* is identical label text. *Findings* clusters labels that name the same thing in different words, which is the fairer measure -- the model rephrases every run.

| list | distinct findings | in all runs | in most runs | exact matches |
|---|---|---|---|---|
| customer_segments | 10 | 0 (0%) | 1 (10%) | 0 |
| pain_points | 15 | 0 (0%) | 1 (7%) | 0 |
| desired_outcomes | 15 | 0 (0%) | 2 (13%) | 0 |
| behavior_patterns | 18 | 0 (0%) | 0 (0%) | 0 |
| opportunity_areas | 25 | 0 (0%) | 0 (0%) | 0 |
| key_trends | 18 | 0 (0%) | 1 (6%) | 0 |
| emerging_trends | 14 | 0 (0%) | 1 (7%) | 0 |
| market_drivers | 14 | 0 (0%) | 3 (21%) | 0 |
| competitors | 16 | 0 (0%) | 3 (19%) | 0 |
| competitive_threats | 15 | 0 (0%) | 1 (7%) | 0 |
| positioning_gaps | 13 | 0 (0%) | 0 (0%) | 0 |
| white_space_opportunities | 13 | 0 (0%) | 0 (0%) | 0 |
| differentiation_opportunities | 18 | 0 (0%) | 0 (0%) | 0 |
| why_now | 12 | 0 (0%) | 1 (8%) | 0 |
| key_opportunities | 12 | 0 (0%) | 1 (8%) | 0 |
| key_risks | 14 | 0 (0%) | 0 (0%) | 0 |
| potential_moats | 10 | 0 (0%) | 1 (10%) | 0 |
| execution_ideas | 14 | 0 (0%) | 0 (0%) | 0 |

Mean recurrence in **all** 5 runs: **0%**
Mean recurrence in **most** runs: **6%**

**4. Fields with a max/min ratio above 2:**

| field | min | max | ratio |
|---|---|---|---|
| `synthesis.market_pulse` | 8 | 100 | 12.5x |
| `report.verdict.market_pulse.value` | 8 | 100 | 12.5x |
| `report.market.market_maturity.source_count` | 1 | 8 | 8.0x |
| `report.market.future_outlook.source_count` | 1 | 8 | 8.0x |
| `signals.virality.avg_views_per_day` | 159.5 | 1222.11 | 7.66x |
| `report.signals.virality.avg_views_per_day.value` | 160 | 1200 | 7.5x |
| `signals.market_opportunity.billion_mentions` | 1 | 6 | 6.0x |
| `report.signals.market_opportunity.mentions.counts.billion_mentions` | 1 | 6 | 6.0x |
| `signals.market_opportunity.market_size_mentions` | 1 | 5 | 5.0x |
| `signals.market_opportunity.forecast_mentions` | 1 | 5 | 5.0x |
| `signals.market_opportunity.cagr_mentions` | 1 | 5 | 5.0x |
| `signals.market_size.market_reports` | 1 | 5 | 5.0x |
| `report.signals.market_size.market_reports.value` | 1 | 5 | 5.0x |
| `report.signals.market_opportunity.mentions.counts.market_size_mentions` | 1 | 5 | 5.0x |
| `report.signals.market_opportunity.mentions.counts.forecast_mentions` | 1 | 5 | 5.0x |
| `report.signals.market_opportunity.mentions.counts.cagr_mentions` | 1 | 5 | 5.0x |
| `report.signals.virality.avg_engagement_rate.value` | 1 | 4 | 4.0x |
| `signals.customer.comment_volume` | 411 | 1534 | 3.73x |
| `report.signals.customer.comment_volume.value` | 411 | 1534 | 3.73x |
| `signals.market_opportunity.growth_mentions` | 2 | 6 | 3.0x |
| `report.signals.market_opportunity.mentions.counts.growth_mentions` | 2 | 6 | 3.0x |
| `signals.virality.avg_engagement_rate` | 1.48 | 3.71 | 2.51x |
| `signals.virality.momentum` | 8 | 19 | 2.38x |
| `report.signals.virality.momentum.value` | 8 | 19 | 2.38x |

### Executive summary, first 80 chars per run

1. The AI note-taking market for clinicians is rapidly growing, fueled by substanti
2. The AI note-taking market for clinicians is booming, driven by the critical need
3. The AI note-taking market for clinicians is experiencing robust growth, driven b
4. The AI note-taking market for clinicians presents a strong opportunity due to hi
5. The market for AI note-taking for clinicians is robust and growing, driven by th

### Unstable fields

- `intelligence.market.growth_rate.confidence` — {"min": 0, "max": 90, "spread": 90, "ratio": null}
- `intelligence.market.market_maturity.confidence` — {"min": 75, "max": 90, "spread": 15, "ratio": 1.2}
- `intelligence.market.market_size.confidence` — {"min": 0, "max": 90, "spread": 90, "ratio": null}
- `report.market.future_outlook.source_count` — {"min": 1, "max": 8, "spread": 7, "ratio": 8.0}
- `report.market.growth_rate.source_count` — {"min": 0, "max": 8, "spread": 8, "ratio": null}
- `report.market.market_maturity.confidence` — {"min": 75, "max": 90, "spread": 15, "ratio": 1.2}
- `report.market.market_maturity.source_count` — {"min": 1, "max": 8, "spread": 7, "ratio": 8.0}
- `report.market.market_size.source_count` — {"min": 0, "max": 8, "spread": 8, "ratio": null}
- `report.signals.customer.comment_volume.source_count` — {"min": 3, "max": 6, "spread": 3, "ratio": 2.0}
- `report.signals.customer.comment_volume.value` — {"min": 411, "max": 1534, "spread": 1123, "ratio": 3.73}
- `report.signals.market_opportunity.mentions.counts.billion_mentions` — {"min": 1, "max": 6, "spread": 5, "ratio": 6.0}
- `report.signals.market_opportunity.mentions.counts.cagr_mentions` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `report.signals.market_opportunity.mentions.counts.forecast_mentions` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `report.signals.market_opportunity.mentions.counts.growth_mentions` — {"min": 2, "max": 6, "spread": 4, "ratio": 3.0}
- `report.signals.market_opportunity.mentions.counts.market_size_mentions` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `report.signals.market_opportunity.mentions.counts.million_mentions` — {"min": 0, "max": 5, "spread": 5, "ratio": null}
- `report.signals.market_opportunity.sizing_language_density.value` — {"min": 63, "max": 100, "spread": 37, "ratio": 1.59}
- `report.signals.market_size.market_reports.value` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `report.signals.virality.avg_engagement_rate.source_count` — {"min": 3, "max": 6, "spread": 3, "ratio": 2.0}
- `report.signals.virality.avg_engagement_rate.value` — {"min": 1, "max": 4, "spread": 3, "ratio": 4.0}
- `report.signals.virality.avg_views_per_day.source_count` — {"min": 3, "max": 6, "spread": 3, "ratio": 2.0}
- `report.signals.virality.avg_views_per_day.value` — {"min": 160, "max": 1200, "spread": 1040, "ratio": 7.5}
- `report.signals.virality.momentum.value` — {"min": 8, "max": 19, "spread": 11, "ratio": 2.38}
- `report.verdict.decision` — {"distinct": ["Strong Yes", "Yes"]}
- `report.verdict.market_pulse.value` — {"min": 8, "max": 100, "spread": 92, "ratio": 12.5}
- `signals.customer.comment_volume` — {"min": 411, "max": 1534, "spread": 1123, "ratio": 3.73}
- `signals.market_opportunity.billion_mentions` — {"min": 1, "max": 6, "spread": 5, "ratio": 6.0}
- `signals.market_opportunity.cagr_mentions` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `signals.market_opportunity.forecast_mentions` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `signals.market_opportunity.growth_mentions` — {"min": 2, "max": 6, "spread": 4, "ratio": 3.0}
- `signals.market_opportunity.market_size_mentions` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `signals.market_opportunity.million_mentions` — {"min": 0, "max": 5, "spread": 5, "ratio": null}
- `signals.market_opportunity.opportunity_score` — {"min": 63, "max": 100, "spread": 37, "ratio": 1.59}
- `signals.market_size.market_reports` — {"min": 1, "max": 5, "spread": 4, "ratio": 5.0}
- `signals.virality.avg_engagement_rate` — {"min": 1.48, "max": 3.71, "spread": 2.23, "ratio": 2.51}
- `signals.virality.avg_views_per_day` — {"min": 159.5, "max": 1222.11, "spread": 1062.61, "ratio": 7.66}
- `signals.virality.momentum` — {"min": 8, "max": 19, "spread": 11, "ratio": 2.38}
- `synthesis.build_recommendation.decision` — {"distinct": ["Strong Yes", "Yes"]}
- `synthesis.market_pulse` — {"min": 8, "max": 100, "spread": 92, "ratio": 12.5}
- `synthesis.opportunity_score` — {"min": 63, "max": 100, "spread": 37, "ratio": 1.59}

### Timing

per-run total: [31.1, 35.8, 35.9, 31.0, 33.9]
median: **33.9s**

## Carbon accounting for SMBs

5 runs. 200 stable, 58 drifting, 35 unstable, of 293 leaf fields.

### The four questions

**1. Does the verdict flip?** No — decisions: ['Strong Yes', 'Strong Yes', 'Strong Yes', 'Monitor', 'Monitor']

> 2 of 5 runs (#4, #5) returned an **empty synthesis** and were served as `Monitor` with confidence 0 — that is the fallback default, not a judgement. Those runs are excluded from the flip test above.

**2. Does market_pulse vary by more than 15 points?** YES — values [75, 67, 75, 0, 0], spread 75

**3. Insight-list recurrence across all runs:**

Counted two ways. *Exact* is identical label text. *Findings* clusters labels that name the same thing in different words, which is the fairer measure -- the model rephrases every run.

| list | distinct findings | in all runs | in most runs | exact matches |
|---|---|---|---|---|
| customer_segments | 7 | 0 (0%) | 0 (0%) | 0 |
| pain_points | 10 | 0 (0%) | 0 (0%) | 0 |
| desired_outcomes | 13 | 0 (0%) | 0 (0%) | 0 |
| behavior_patterns | 9 | 0 (0%) | 0 (0%) | 0 |
| opportunity_areas | 13 | 0 (0%) | 0 (0%) | 0 |
| key_trends | 9 | 0 (0%) | 0 (0%) | 0 |
| emerging_trends | 7 | 0 (0%) | 0 (0%) | 0 |
| market_drivers | 9 | 0 (0%) | 0 (0%) | 0 |
| competitors | 5 | 0 (0%) | 0 (0%) | 0 |
| competitive_threats | 5 | 0 (0%) | 0 (0%) | 0 |
| positioning_gaps | 8 | 0 (0%) | 0 (0%) | 0 |
| white_space_opportunities | 6 | 0 (0%) | 0 (0%) | 0 |
| differentiation_opportunities | 10 | 0 (0%) | 0 (0%) | 0 |
| why_now | 7 | 0 (0%) | 1 (14%) | 0 |
| key_opportunities | 7 | 0 (0%) | 0 (0%) | 0 |
| key_risks | 7 | 0 (0%) | 0 (0%) | 0 |
| potential_moats | 7 | 0 (0%) | 1 (14%) | 0 |
| execution_ideas | 8 | 0 (0%) | 0 (0%) | 0 |

Mean recurrence in **all** 5 runs: **0%**
Mean recurrence in **most** runs: **2%**

**4. Fields with a max/min ratio above 2:**

| field | min | max | ratio |
|---|---|---|---|
| `signals.market_opportunity.cagr_mentions` | 1 | 7 | 7.0x |
| `report.signals.market_opportunity.mentions.counts.cagr_mentions` | 1 | 7 | 7.0x |
| `signals.market_opportunity.market_size_mentions` | 1 | 6 | 6.0x |
| `signals.market_size.market_reports` | 1 | 6 | 6.0x |
| `report.signals.market_size.market_reports.value` | 1 | 6 | 6.0x |
| `report.signals.market_opportunity.mentions.counts.market_size_mentions` | 1 | 6 | 6.0x |
| `signals.virality.avg_views_per_day` | 0.16 | 0.9 | 5.62x |
| `report.signals.virality.avg_views_per_day.value` | 0.16 | 0.9 | 5.62x |
| `signals.market_opportunity.billion_mentions` | 2 | 10 | 5.0x |
| `report.signals.market_opportunity.mentions.counts.billion_mentions` | 2 | 10 | 5.0x |
| `signals.market_opportunity.forecast_mentions` | 2 | 7 | 3.5x |
| `report.signals.market_opportunity.mentions.counts.forecast_mentions` | 2 | 7 | 3.5x |
| `signals.market_opportunity.million_mentions` | 1 | 3 | 3.0x |
| `report.signals.market_opportunity.mentions.counts.million_mentions` | 1 | 3 | 3.0x |

### Executive summary, first 80 chars per run

1. The carbon accounting market for SMBs is a high-growth opportunity, propelled by
2. The carbon accounting market for SMBs is rapidly emerging, driven by regulatory 
3. The carbon accounting market for SMBs is poised for significant growth, driven b
4. 
5. 

### Unstable fields

- `intelligence.market.future_outlook.confidence` — {"min": 0, "max": 90, "spread": 90, "ratio": null}
- `intelligence.market.growth_rate.confidence` — {"min": 0, "max": 95, "spread": 95, "ratio": null}
- `intelligence.market.market_maturity.confidence` — {"min": 0, "max": 90, "spread": 90, "ratio": null}
- `intelligence.market.market_maturity.stage` — {"distinct": ["Growth", "Emerging", ""]}
- `intelligence.market.market_size.confidence` — {"min": 0, "max": 95, "spread": 95, "ratio": null}
- `report.market.future_outlook.source_count` — {"min": 0, "max": 7, "spread": 7, "ratio": null}
- `report.market.growth_rate.source_count` — {"min": 0, "max": 7, "spread": 7, "ratio": null}
- `report.market.market_maturity.source_count` — {"min": 0, "max": 7, "spread": 7, "ratio": null}
- `report.market.market_maturity.value` — {"distinct": ["Growth", "Emerging", null]}
- `report.market.market_size.source_count` — {"min": 0, "max": 7, "spread": 7, "ratio": null}
- `report.signals.market_opportunity.mentions.counts.billion_mentions` — {"min": 2, "max": 10, "spread": 8, "ratio": 5.0}
- `report.signals.market_opportunity.mentions.counts.cagr_mentions` — {"min": 1, "max": 7, "spread": 6, "ratio": 7.0}
- `report.signals.market_opportunity.mentions.counts.forecast_mentions` — {"min": 2, "max": 7, "spread": 5, "ratio": 3.5}
- `report.signals.market_opportunity.mentions.counts.growth_mentions` — {"min": 5, "max": 10, "spread": 5, "ratio": 2.0}
- `report.signals.market_opportunity.mentions.counts.market_size_mentions` — {"min": 1, "max": 6, "spread": 5, "ratio": 6.0}
- `report.signals.market_opportunity.mentions.counts.million_mentions` — {"min": 1, "max": 3, "spread": 2, "ratio": 3.0}
- `report.signals.market_size.market_reports.value` — {"min": 1, "max": 6, "spread": 5, "ratio": 6.0}
- `report.signals.virality.avg_engagement_rate.value` — {"min": 0, "max": 1, "spread": 1, "ratio": null}
- `report.signals.virality.avg_views_per_day.value` — {"min": 0.16, "max": 0.9, "spread": 0.74, "ratio": 5.62}
- `report.verdict.confidence.confidence` — {"min": 0, "max": 90, "spread": 90, "ratio": null}
- `report.verdict.confidence.value` — {"min": 0, "max": 90, "spread": 90, "ratio": null}
- `report.verdict.decision` — {"distinct": ["Strong Yes", "Monitor"]}
- `report.verdict.market_pulse.value` — {"min": 0, "max": 75, "spread": 75, "ratio": null}
- `signals.market_opportunity.billion_mentions` — {"min": 2, "max": 10, "spread": 8, "ratio": 5.0}
- `signals.market_opportunity.cagr_mentions` — {"min": 1, "max": 7, "spread": 6, "ratio": 7.0}
- `signals.market_opportunity.forecast_mentions` — {"min": 2, "max": 7, "spread": 5, "ratio": 3.5}
- `signals.market_opportunity.growth_mentions` — {"min": 5, "max": 10, "spread": 5, "ratio": 2.0}
- `signals.market_opportunity.market_size_mentions` — {"min": 1, "max": 6, "spread": 5, "ratio": 6.0}
- `signals.market_opportunity.million_mentions` — {"min": 1, "max": 3, "spread": 2, "ratio": 3.0}
- `signals.market_size.market_reports` — {"min": 1, "max": 6, "spread": 5, "ratio": 6.0}
- `signals.virality.avg_views_per_day` — {"min": 0.16, "max": 0.9, "spread": 0.74, "ratio": 5.62}
- `synthesis.build_recommendation.decision` — {"distinct": ["Strong Yes", "Monitor"]}
- `synthesis.confidence` — {"min": 0, "max": 90, "spread": 90, "ratio": null}
- `synthesis.market_pulse` — {"min": 0, "max": 75, "spread": 75, "ratio": null}
- `synthesis.opportunity_score` — {"min": 0, "max": 100, "spread": 100, "ratio": null}

### Timing

per-run total: [30.9, 29.1, 27.8, 10.2, 10.7]
median: **27.8s**
