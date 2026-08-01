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
