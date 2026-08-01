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
