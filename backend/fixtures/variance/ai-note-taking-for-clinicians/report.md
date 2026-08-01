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
