# Superseded adjudication rows — 2026-09 coding-scheme revision

Moved out of `clinical_adjudication.md` on 2026-09-02 because `apply_adjudication.py` parses
*every* well-formed `| Study | Field | Old | New | Decision | Rationale |` row in that file
regardless of which heading it sits under — an "Archived" section inside `clinical_adjudication.md`
still fed live rows into the merge and made `merge_validate.py` fail with "no master column for
field" once `ConfoundYN`/`PVal` were dropped from the schema. This file is not read by any script
(per the `archived/` convention — see the root `CLAUDE.md`/`AGENTS.md`: "archived/ is historical.
Nothing in it runs in place and nothing in it is needed to reproduce the manuscript"), so the rows
can sit here as history without being re-parsed.

The `ConfoundYN` and `PVal` columns no longer exist in `clinical_master` (`clinical_codebook.md`
§11, `clinical_system_design.md` §10): `ConfoundYN` was dropped entirely and split into
`MediatingYN`/`ModeratingYN`; `PVal` was replaced by `HypothesisTestReportedYN`. The 31 adjudication
rows below (11 `ConfoundYN`, 20 `PVal`) are kept here rather than deleted, since they remain the
record of what the source text actually said under the old scheme — but they no longer correct
anything in the live master, and `clinical_adjudication.md`'s **Totals** line excludes them. New
adjudication for `MediatingYN`, `ModeratingYN`, and `HypothesisTestReportedYN` happens after
re-extraction against the revised codebook surfaces disagreements; it is not derived from these
rows, since the old fields asked different questions than the new ones.

## ConfoundYN (superseded)

| Study | Field | Old | New | Decision | Rationale |
|---|---|---|---|---|---|
| Denson 1970 | ConfoundYN | `0` | `1` | New | The paper itself acknowledges: "these results indicated that the matching of Treatment and Control samples was not perfect," in addition to alcoholics/neurotics being pooled. |
| Heinzerling 2023 | ConfoundYN | `1` | `0` | Unclear | The Week 3 randomized comparison showed no baseline differences (p>0.05 all), arguing for "0"; but the Week 7 dosing condition was self-selected rather than randomized, a genuine confound the text doesn't resolve for the field as a whole. |
| MacLean 1961 | ConfoundYN | `0` | `1` | New | No control group, no randomization, no blinding, and subjective composite ratings by the treating team — substantial confounding evident. |
| Sessa 2019 | ConfoundYN | `0` | `1` | New | Uncontrolled, unblinded, open-label case series with n=4 and no comparator group — clear confounding potential. |
| Sessa 2021 | ConfoundYN | `0` | `1` | New | Open-label, single-arm, no randomization/blinding, and most participants concurrently on SSRIs/other psychiatric medications — clear confounding potential. |
| Thurgur 2025 | ConfoundYN | `0` | `1` | Unclear | The paper acknowledges it could not control for confounds in the SF-36 QOL results, which supports either reading depending on whether the field means "confounding present" (New) or "confounding controlled for" (Old); text doesn't disambiguate. |
| Garcia-Romeu 2015 | ConfoundYN | `3` | `1` | New | The abstainer-vs-smoker groups compared were defined post hoc by the outcome itself, which the authors flag as limiting causal interpretation — a genuine confound rather than "does not apply." |
| Johnson 2014 | ConfoundYN | `0` | `1` | New | The open-label, uncontrolled design is itself an acknowledged confound, and participants "received substantially more contact with study staff" than comparator treatments — a further confound. |
| Johnson 2016 | ConfoundYN | `0` | `1` | New | Text explicitly flags selection bias: "participant self-selection bias may have played a role...as the study enrolled only individuals motivated to quit and willing to undergo a time-intensive experimental treatment for no monetary compensation." |
| Krupitsky 2002 | ConfoundYN | `0` | `1` | Old | Double-blind, randomized, active-placebo-controlled design (both psychotherapist and subject blind to dose; independent blind rater) with exclusion of comorbid psychiatric/polydrug/alcohol dependence — a well-controlled design with low confounding risk. |
| P.L. Prior 2014 | ConfoundYN | `0` | `1` | New | Text explicitly reports baseline-comparability testing between groups ("no statistically significant differences...regarding age, demographic, ethnicity or physical comorbidities"), indicating confounding was assessed. |

## PVal (superseded)

| Study | Field | Old | New | Decision | Rationale |
|---|---|---|---|---|---|
| Bowen 1970 | PVal | `>0.05` | `NS` | Equivalent | Table 4's χ²=1.468 falls well below the .05 critical value (5.991) — both notations describe the same non-significant result. |
| Dusen 1967 | PVal | `>0.05` | `NS` | Equivalent | "At the 5% level there was no significant difference between any of these groups" — same result, both notations. |
| Gent 2024 | PVal | `0.003` | `0.014` | Old | Consistent with Outcome=interaction statistic (F(2,52)=6.45), its p-value is p=0.003; p=0.014 belongs to the group main effect. |
| Grabski 2022 | PVal | `<0.05` | `None` | New | The primary outcome is reported only as a CI not crossing zero; no explicit numeric p-value is printed for this comparison anywhere in the text. |
| Heinzerling 2023 | PVal | `<0.001` | `0.02` | New | Same sentence gives "p = 0.02" for the systolic BP group difference; <0.001 belongs to a different within-group analysis. |
| Hollister 1969 | PVal | `<0.01` | `NS` | New | Consistent with the six-month primary-endpoint result: "Not significant, analysis of variance"; <0.01 belongs only to the transient two-month comparison. |
| Jensen 1963 | PVal | `<0.1` | `>.01` | New | Verbatim: "significantly more of the alcoholics treated with LSD were dry or improved...(P> .01)." New is a literal transcription; Old changes the value's order of magnitude with no textual basis. |
| Luquiens 2025 | PVal | `0.043` | `0.031` | Old | Old's 0.043 pairs with the abstinence-rate CI also captured in the SD field; New's 0.031 belongs to the separate feasibility completion-rate result, unpaired with any SD in the new extraction. |
| O'Reilly 1964 | PVal | `<0.01` | `None` | New | The ".01 level" applies only to a secondary correlate (depression/transcendental experience), not to the primary 38% abstinence figure, which is purely descriptive. |
| Pagni 2024 | PVal | `0.0114` | `<0.005` | New | The primary significance threshold used was "p-uncorrected < 0.005, k = 10" for the whole-brain interactions; 0.0114 is the secondary craving t-test's p-value. |
| Pagni 2025 | PVal | `0.01` | `0.03` | Unclear | Mirrors the Outcome/SD ambiguity: p=.01 belongs to Openness, p=.03 to Neuroticism. |
| Pahnke 1970 | PVal | `0.025` | `None` | Old | Same Table 1 row: F=4.43 paired with "0.025" for the Drinking Behavior comparison. |
| Smart 1966 | PVal | `>0.05` | `>.05` | Equivalent | Same non-significant ANOVA result in both notations. |
| Thurgur 2025 | PVal | `0.423` | `None` | Old | "binomial test did not reject the null hypothesis...(k = .64, P = .423)" — explicitly reported. |
| Tomsovic 1970 | PVal | `<0.01` | `<.01` | Equivalent | Same value ("Significant at .01 level of confidence"); only decimal-point formatting differs. |
| D.C. Mash 2000 | PVal | `0.0005` | `0.0001` | Old | Table 1 BDI result: p=.0005, pairing with the BDI Outcome/SD rows; p=.0001 belongs to the opiate-craving subscale. |
| Jovaisa T 2006 | PVal | `<0.001` | `<0.05` | New | Paired with the Outcome decision: "difference between groups significant for hourly OOWS-A score, p<0.05." The <0.001 figure belongs to the Table 3 MAP comparison, a different secondary outcome. |
| Krupitsky 2002 | PVal | `<0.01` | `<0.05` | Unclear | Fig. 1's legend marks significance at both "* p<.05" and "** p<.01" across different months of follow-up; the text gives no single overall p-value for the finding as a whole. |
| Krupitsky 2007 | PVal | `<0.01` | `<0.05` | New | "13 out of 26 participants (50%)...compared to six out of 27 participants (22.2%)...(p < 0.05)" — the paper reports p<0.05, not p<0.01, for this comparison. |
| Savage 1973 | PVal | `0.05` | `<.05` | Equivalent | Table 3 prints "3.86 .05"; the narrative separately states "(P<.05; see Table 3)." Both text-supported, same result. |
