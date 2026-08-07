# Manuscript corrections — new extraction pipeline

Target file: `USPSTF Manuscript and Outline_USPS.md`
Data as of: rebuild after `output.md` adjudication was applied to `clinical_master.csv`.

Every number below comes from the rebuilt artifacts in `tables/`, `figures/`, and
`clinical_trials/outputs/`. All four gates pass: `merge_validate` (49 articles,
193 AE events, 0 blocking), `gate_rebuild` (32/7/4 eligible, 0 issues),
`visual_regression` (0 unexplained), and the config/master cross-check.

Line numbers refer to the current file and will drift as you edit — work top-down.

---

## 0. The one thing to read first

**The headline N moves 44 → 43, and it is not because the pipeline lost anything.**

The new corpus is 49 articles: the frozen 44 plus 5 that were newly screened.
All 5 new ones failed the eligibility screen (2 study protocols, 2 narrative
reviews, 1 unusable scan). Of the original 44, exactly one now fails: **Denson
1970**, which pools alcoholics with neurotic patients and reports no
alcohol-consumption, abstinence, craving, or validated SUD outcome anywhere.
The independent adjudication in `output.md` reached the same conclusion and
recommended excluding it.

So: `44 − Denson 1970 = 43`. Nothing else left the evidence base.

> **Ludwig 1969 correction to my earlier report.** I previously flagged Ludwig
> 1969 as a study whose PDF is unusable. That is still true — the file contains
> unrelated book-review pages. But Ludwig was **never in the frozen 44**; its
> `old_row_match` is `NEW`, meaning I added it to the corpus during
> reconciliation. There is no hand-extracted row to fall back on, so it cannot
> be restored from the frozen records as you asked. It has never contributed to
> any manuscript number, and dropping it changes nothing. It only matters if you
> want it *added*, which needs a usable PDF.

---

## 1. Methods §2.1 — Extraction procedure (lines 75, 77)

This section is now factually wrong about the clinical-trial pipeline. It
describes clinical trials as extracted by **Claude Opus** via a fixed system
prompt with human review of "selected outputs", and presents the
subagent/Sonnet architecture as belonging only to observational studies. Both
pipelines now use the same subagent architecture.

**Replace line 75 entirely** with:

> Each included article was coded according to these indicators through a
> structured, AI-augmented protocol with a deterministic validation gate. Each
> article's source PDF was first converted to Markdown by a fixed preprocessing
> script, subject to a four-check fidelity gate (text-retention ratio,
> runaway-expansion ratio, heading recovery, and table-row recovery); files
> failing any check were demoted to plain text, and optical character
> recognition was applied at 300 dpi where a scan yielded no usable text. Data
> extraction followed a one-article-per-model-call design: each article was
> assigned to an isolated Claude Sonnet 5 subagent that saw only that article,
> preventing cross-article contamination — in particular, preventing the
> methodological or demographic profile of one study from anchoring the coding
> of another. Because the review's primary comparison is between pre-1980 and
> post-2010 eras, this isolation is load-bearing rather than incidental. Each
> subagent returned a single JSON object containing both the coded values and a
> mandatory free-text rationale for every non-obvious decision. Extraction was
> performed under a pinned prompt version (v1.2) and a pinned severity rubric
> (v1), both recorded per article so that any value can be traced to the exact
> instructions that produced it.

**Then insert a new paragraph after line 75**, describing the eligibility screen
and the human adjudication — neither of which the manuscript currently mentions:

> Each article was first screened against two eligibility criteria: (a) that it
> reported an original clinical trial rather than a protocol, review, or
> commentary, and (b) that it reported at least one substance-use outcome.
> Articles failing either criterion were retained in the dataset with an
> explicit failure code and reason, but excluded from all analyses. Of 49
> articles screened, 43 were eligible; the 6 exclusions comprised two study
> protocols, two narrative reviews, one pooled re-analysis without an original
> trial, and one article whose only available scan did not contain the target
> text. Following extraction, every field on which the automated extraction
> disagreed with the prior hand extraction was independently re-adjudicated
> against the source text by trained reviewers, who recorded a decision and a
> written justification for each. Of 281 adjudicated fields, the automated value
> was upheld in 144 (51%), the hand-extracted value in 74 (26%), 34 (12%) were
> judged equivalent notations of the same fact, and 29 (10%) were judged
> unresolvable from the source text. All 74 fields decided in favour of the hand
> extraction were written back into the analytic dataset.

**Line 77** — delete the clause that makes Sonnet the observational-only model.
Change *"processed using Claude Sonnet 5 rather than the Opus API used for the
clinical-trial dataset"* to *"processed using Claude Sonnet 5, the same model and
isolation design used for the clinical-trial dataset"*.

---

## 2. Methods §3.1 — Tier assignment (line 91)

Three numbers change.

| Current text | Replace with |
|---|---|
| "Each of the 44 included studies, comprising 33 alcohol studies, 4 smoking studies, and 7 opioid studies" | "Each of the 43 eligible studies, comprising 32 alcohol studies, 4 smoking studies, and 7 opioid studies" |
| "These 16 studies were placed on a common numeric scale" | "These 16 studies were placed on a common numeric scale" — *count is unchanged, but membership changed; see §7* |
| "Rather than excluding these 28 studies" | "Rather than excluding these 27 studies" |

---

## 3. Results opening (line 109)

**Current:** "identified 82 relevant peer-reviewed studies of psychedelics: 44
clinical trials (33 alcohol, 7 opioid, 4 smoking)"

**Replace with:** "identified 87 relevant peer-reviewed studies of psychedelics:
49 clinical trial articles screened for eligibility, of which 43 were eligible
(32 alcohol, 7 opioid, 4 smoking), and 38 observational studies."

**Substance sentences in the same paragraph** — every figure changes, and one
claim reverses:

| Current | Replace with |
|---|---|
| "For smoking, 100% of trials used psilocybin." | unchanged — still 100% |
| "For alcohol trials, 39% used LSD, 24% psilocybin, another 24% used ketamine, and 12% used MDMA." | "For alcohol trials, 38% used LSD, 25% psilocybin, 25% ketamine, and 12% MDMA." |
| "For opioid trials, 57% used ibogaine, 29% used ketamine, and 14% used LSD." | "For opioid trials, 43% used ibogaine, 43% ketamine, and 14% LSD." |
| **"While multiple observational studies did so, no trials included ayahuasca, mescaline, or a combination of psychedelics."** | **"While multiple observational studies did so, no trial included ayahuasca. One alcohol trial (Smith 1958) administered both LSD and mescaline, and is the sole trial in the sample using mescaline or more than one psychedelic."** |

> The mescaline reversal comes from an adjudicated correction: Smith 1958
> explicitly reports dosing patients with "Mescaline, 0.5 g" alongside LSD, with
> at least one patient receiving both. The frozen dataset coded both flags 0.
> The opioid ibogaine/ketamine shift comes from Jovaisa 2006, which the frozen
> dataset coded as an ibogaine study; the paper is entirely about intravenous
> ketamine and never mentions ibogaine.

---

## 4. Table 2 (lines 113–123) — replace the body

Denominators change: n = 43 trials (32 alcohol, 7 opioid, 4 smoking).
Update the header row `n = 44 / 33 / 7 / 4` accordingly.

| Substance | % of Trials (n=43) | Alcohol (n=32) | Opioids (n=7) | Smoking (n=4) |
| ----- | :---: | :---: | :---: | :---: |
| Psilocybin | 28% | 25% | 0% | 100% |
| Ayahuasca | 0% | 0% | 0% | 0% |
| LSD | 30% | 38% | 14% | 0% |
| Mescaline/peyote | 2% | 3% | 0% | 0% |
| Ibogaine | 7% | 0% | 43% | 0% |
| MDMA | 9% | 12% | 0% | 0% |
| Ketamine | 26% | 25% | 43% | 0% |
| > 1 psychedelic | 2% | 3% | 0% | 0% |

---

## 5. Table 3 (lines 141–183) — replace the body

n = 43 (32 alcohol, 7 opioid, 4 smoking). Update the column headers.

| Domain | Indicator | All (n=43) | Alcohol (n=32) | Opioids (n=7) | Smoking (n=4) |
| ----- | ----- | :---: | :---: | :---: | :---: |
| **Study Identification & Design** | Were subjects randomized? | 58% | 59% | 71% | 25% |
|  | Were participants blinded? | 51% | 53% | 71% | 0% |
|  | Was the study double-blinded? | 37% | 38% | 57% | 0% |
|  | Did the study include a control or comparison group? | 65% | 66% | 86% | 25% |
|  | Interfaces with primary care | 5% | 3% | 14% | 0% |
|  | Power reported or discussed | 23% | 28% | 14% | 0% |
|  | Percent retention ≥ 80% | 74% | 75% | 57% | 100% |
|  | Validated scale or measure used | 77% | 72% | 86% | 100% |
|  | Assessed Confounding, Moderating or Mediating | 84% | 84% | 71% | 100% |
|  | Were inclusion/exclusion criteria clearly stated? | 84% | 81% | 100% | 75% |
|  | Were funding sources and COIs disclosed? | 86% | 84% | 86% | 100% |
| **Population & Generalizability** | Was baseline status reported? | 70% | 69% | 57% | 100% |
|  | Age range reported | 88% | 88% | 86% | 100% |
|  | Average Percent of Participants = Female | 28% | 31% | 13% | 35% |
|  | Average Percent of Participants = BIPOC | 21% | 20% | 51% | 8% |
|  | Are low SES participants included? | 19% | 19% | 14% | 25% |
|  | Country of study is the US | 47% | 47% | 14% | 100% |
|  | Recruitment reflective of community/clinical populations | 14% | 19% | 0% | 0% |
| **Intervention & Safety** | Description of intervention content / delivery? | 100% | 100% | 100% | 100% |
|  | Was therapy / counseling / integration / prep included? | 81% | 88% | 43% | 100% |
|  | Were harms or AEs assessed? | 86% | 81% | 100% | 100% |
| **Equity\*** | Was a cultural frame used | 2% | 0% | 14% | 0% |
|  | Were Indigenous frameworks referenced? | 0% | 0% | 0% | 0% |
|  | Did the study address reciprocity for Indigenous groups? | 0% | 0% | 0% | 0% |
| **Outcomes & Follow-Up** | Was psychedelic intervention associated with improvement of behavior? | 81% | 78% | 86% | 100% |
|  | Largest or Main Effect Size/Outcome reported | 100% | 100% | 100% | 100% |
|  | P-value reported | 72% | 75% | 86% | 25% |
|  | Median longest follow-up in months | 6 | 6 | 6 | 6 |
|  | Were behavioral changes measured? | 100% | 100% | 100% | 100% |
|  | Were physical/biological outcomes measured? | 65% | 53% | 100% | 100% |
|  | Were mental health outcomes measured? | 56% | 56% | 57% | 50% |
|  | Was quality of life measured? | 14% | 19% | 0% | 0% |
|  | Were implementation outcomes measured? | 28% | 38% | 0% | 0% |
|  | Was a partial behavioral reduction reported? | 77% | 84% | 29% | 100% |
|  | Was a complete cessation reported? | 72% | 69% | 71% | 100% |
|  | Was relapse tracked? | 63% | 56% | 86% | 75% |
|  | Was mortality measured? | 12% | 6% | 43% | 0% |

### Five rows that change the argument, not just the digits

1. **"Country of study is the US" 98% → 47%.** The old row was mislabelled: it
   reported whether *a country was recorded*, not whether that country was the
   US. Corrected to the stated metric, fewer than half the trials are US-based
   (opioid trials: 14%). This **strengthens** the external-validity gap you argue
   in the Discussion — USPSTF's remit is US primary care.
2. **"Were physical/biological outcomes measured?" 34% → 65%.** Driven by
   adjudicated corrections crediting vital-sign monitoring, ECG, bloods, and
   biomarker assays that the frozen extraction coded as absent. Alcohol 30% → 53%,
   opioid 29% → 100%, smoking 75% → 100%.
3. **"Was baseline status reported?" 89% → 70%, and smoking 0% → 100%.** The
   frozen data carried severity labels for studies whose text states none;
   the adjudication removed those and added the FTCD-based severity the smoking
   trials do report. This is a genuine reversal of the claim at line 131 that
   "tobacco studies lacked this characterization (0%)".
4. **"Was a cultural frame used" 0% → 2%.** No longer a clean zero. Savage 1973
   frames its treatment paradigm explicitly around mystical/transcendental
   experience. The Indigenous-framework and reciprocity rows remain 0%.
5. **"Power reported or discussed" 18% → 23%.** This one is *upward* only because
   the analytic denominator shrank; the adjudication actually removed six
   spurious Power=1 codings. See §9.

---

## 6. Results prose (lines 127–137) — figure-by-figure

Replace each figure in place; the surrounding argument survives unchanged unless noted.

**Line 127:** "61% of trials involved randomization" → **58%**; "higher in opioid
(71%) and alcohol (64%)" → "opioid (71%) and alcohol (59%)"; "tobacco trials
(25%)" unchanged. "Participant blinding was reported in 50%" → **51%**;
"71% of opioid trials utilized blinding" unchanged; "double-blinding was used in
57% of opioid trials" unchanged.

**Line 129:** "77% of all trials used validated outcome measurement scales" →
unchanged; "compared to 73% for alcohol and 86% for opioids" → "**72%** for
alcohol and 86% for opioids". "Only 18% of the total sample reported the results
of power calculations" → **23%**. "only two (5%) of all trials included any
interface with primary care (Grabski, 2022; Prior, 2014)" → unchanged.

**Line 131 — needs rewriting, not just renumbering.** Current text says baseline
severity was reported in 89% but "tobacco studies lacked this characterization
(0%)". Both halves are now wrong. Suggested replacement:

> ***Population & Generalizability*** indicators were a primary deficiency.
> Baseline severity was reported in 70% of trials overall, and in all four
> tobacco trials, but in only 57% of opioid and 69% of alcohol trials. Female
> representation averaged 28% overall (alcohol 31%; opioids 13%; tobacco 35%),
> while BIPOC representation was highest in opioid trials (51%) compared to
> alcohol (20%) and tobacco (8%). Only 14% of trials recruited a participant
> pool reflective of real-world community or primary care populations, and no
> opioid or tobacco trial did so. Inclusion of low-SES participants was limited
> (19% overall). Fewer than half of trials (47%) were conducted in the United
> States, and only one of seven opioid trials (14%) was, further limiting
> applicability to US primary care.

**Line 133:** "which involved therapeutic support in 100% of tobacco and alcohol
and 43% of opioid studies" → "100% of tobacco, **88%** of alcohol, and 43% of
opioid studies". "Overall, 80% of trials provided a summary of adverse events
(100% tobacco; 86% of opioid; 76% of alcohol)" → "**86%** of trials … (100%
tobacco; **100%** opioid; **81%** alcohol)".

**Line 135 — the absolute claim no longer holds.** Current: "measurement of
equity and cultural framing … was absent, with 0% of studies including cultural
context, Indigenous frameworks, or reciprocity". Replace with:

> ***Equity & Cultural Framing*** indicators were near-absent. No study
> referenced Indigenous frameworks or addressed reciprocity for Indigenous
> communities (0% for both). A single trial (Savage 1973, 2% of the sample)
> employed an explicit cultural or spiritual frame. The sentence also has an
> unterminated word — "marginalized grou" — that needs completing.

**Line 137:** "Complete cessation was reported in 70%" → **72%**. "Relapse was
tracked in 86% of opioid trials and 50% in tobacco, but only 33% of alcohol" →
"86% of opioid trials and **75%** in tobacco, but only **56%** of alcohol". "75%
of tobacco studies measured physical/biological outcomes, for opioid (29%) and
alcohol (30%)" → "**100%** of tobacco and **100%** of opioid studies measured
physical/biological outcomes, compared with **53%** of alcohol studies" — note
this **inverts** the direction of the original sentence. "implementation outcomes
(23%), quality of life (16%) and mortality (5%)" → "**28%**, **14%** and **12%**".

---

## 7. Figures 2A / 2B and Tier membership (lines 206–214)

Tier 1 remains **k = 16**, but two members changed, and the figures are already
regenerated in `figures/`.

- **Added:** none.
- **Removed: Jovaisa 2006.** Its only convertible statistic (d = 1.39) came from
  peak mean arterial pressure — a cardiovascular safety parameter, not a
  substance-use outcome. The adjudication designates OOWS-A withdrawal severity
  as its primary outcome, and that is reported only as "p<0.05" with no test
  statistic. Now classified Tier 2, `moderate_positive`.
- **Sign corrected: Rothberg 2021, g = −0.59 → +0.59.** See §9; this was a
  double-negation bug that plotted a beneficial result as harmful.
- **Effect corrected: Das 2019, g = 1.05 → 0.80.** The conversion had been keyed
  to ηp² = 0.219 from a secondary cue-reactivity measure; the adjudicated primary
  drinking outcome is ηp² = 0.14.

**Figure 2A caption (line 206)** says "among double-blinded clinical trials".
That is inaccurate and always was — Tier 1 membership is determined by whether a
convertible statistic was reported, not by blinding (8 of the 16 are not
double-blind). Suggested caption:

> **Figure 2A.** Standardized effect sizes (Hedges' g) for psychedelic
> interventions targeting smoking, alcohol, and opioid use, among the 16 trials
> reporting a statistic convertible to a between-groups standardized effect size.
> Filled squares denote clean conversions; hollow squares denote approximate
> conversions. Where a trial reported only a total sample size, equal group sizes
> were assumed for variance estimation.

**Figure 2B caption (line 210)** says "among single-arm and open label clinical
trials". Also inaccurate: Tier 2 holds 27 trials excluded from Tier 1 for any
reason, including two-arm trials that reported no convertible statistic (Jovaisa
2006, Krupitsky 2002, P.L. Prior 2014). Suggested:

> **Figure 2B.** Qualitative classification of effect direction and approximate
> magnitude for the 27 trials whose reported results could not be converted to a
> common standardized scale, whether because no comparator arm existed, no test
> statistic was reported, or the reported statistic was not reducible to a
> one-degree-of-freedom between-groups comparison.

Tier 2 distribution, if you want it in text: single-arm positive 13, moderate
positive 6, large positive 3, negative 1, remainder unclassifiable.

---

## 8. Table 4 (lines 193–202) and the Net-benefits paragraph (line 189)

The clinical-trial rows are currently empty and the paragraph carries an `XX%`
placeholder. The new AE dataset fills both. Note the two editorial queries in
the current header ("Should this say serious?") — the answer is **no**: the
pipeline records CTCAE-graded severity, and "Severe" is not synonymous with FDA
"serious". Retitle those columns to say severity, and add a separate serious-AE
column only if you want to report the FDA cross-walk, which is available in
`ae_events.csv` as `MeetsFDASerious`.

**Replacement Table 4:**

| Study Type (N) | N | Studies with positive result in primary outcome | Studies assessing AEs | Studies reporting ≥1 AE | AE events by worst severity |
| ----- | ----- | ----- | ----- | ----- | ----- |
| Clinical Trial (43) | 2,118 | 81% | 37 (86%) | 31 (72%) | Mild 145 · Moderate 17 · Severe 24 |
| Tobacco (4) | 127 | 100% | 4 (100%) | 4 (100%) | Mild 23 · Moderate 2 · Severe 0 |
| Opioids (7) | 320 | 86% | 7 (100%) | 6 (86%) | Mild 6 · Moderate 3 · Severe 6 |
| Alcohol (32) | 1,671 | 78% | 26 (81%) | 21 (66%) | Mild 116 · Moderate 12 · Severe 18 |
| Observational (38) | 979,865 | — | 10 | — | *(unchanged — from the observational pipeline)* |
| Tobacco (3) | | | 2 | 2 | Mild 43 · Moderate 3 |
| Opioids (11) | | | 7 | 6 | Severe 24 |
| Alcohol (14) | | | 9 | 9 | Mild 3 · Moderate 18 |

**Line 189 replacements:**

| Current | Replace with |
|---|---|
| "The majority of trials (77%) reported improvement in problematic substance use (tobacco: 100%; opioids: 86%; alcohol: 73%)." | "The majority of trials (**81%**) reported improvement in problematic substance use (tobacco: 100%; opioids: 86%; alcohol: **78%**)." |
| "only XX% of clinical trial studies had participants who experienced serious adverse events" | "**28% (12 of 43) of clinical trials reported at least one severe adverse event, and 186 discrete adverse events were recorded across the 43 trials, of which 78% (145) were mild and 13% (24) severe**" |
| "compared to 2,338 in the 44 clinical trials" | "compared to **2,118 in the 43 clinical trials**" |

**Caveat to add as a Table 4 footnote:** 89 of the 186 AE events could not be
assigned a severity grade unambiguously from the source text and were resolved
conservatively under the pinned rubric; each carries a recorded rationale and is
listed in `human_review_queue.csv`.

---

## 9. Table 5 (line 236) — the psychedelic benchmark row

**Current row:** `16 | 1,125 | 2.49 (1.57–3.93) | 0.50 (0.25–0.75)`

**Replace with:** `16 | 973 | 2.30 (1.49–3.55) | 0.46 (0.22–0.70)`

Random-effects (DerSimonian–Laird) pooled Hedges' g = 0.460, 95% CI 0.222–0.698,
I² = 67%. The odds-ratio column is the logit back-transform of that g, matching
how the other rows in this table are standardized. Fixed-effect g = 0.408
(0.280–0.537) if you prefer that estimator — say which and I will state it in the
Methods.

**The conclusion at line 240 survives.** A pooled g of 0.46 still sits above the
statin (0.047–0.228), alcohol screening (0.293), and opioid screening (0.262)
benchmarks, and remains comparable to HIV PrEP (0.427). The PrEP-as-benchmark
argument is, if anything, slightly better supported now that the psychedelic
estimate is nearer PrEP's than before.

**Add an I² footnote.** I² = 67% is substantial heterogeneity across 16 trials
spanning three substances, four psychedelics, and six decades. A reviewer will
ask. One sentence acknowledging that the pooled figure is directional rather than
a defensible meta-analytic summary would pre-empt it — consistent with the
"only directional, not definitive" framing already at line 240.

---

## 10. Discussion and Limitations

**Line 254** repeats the demographic figures. Update to match §5: "only **14%**
of clinical trials recruited participants representative of real-world community
or primary care populations, only **19%** included low socioeconomic status
participants, average female participation was **28%**, average BIPOC
participation was 21%, and only 5% of studies had any interaction within primary
care settings." The final sentence — "No studies used cultural framing,
Indigenous frameworks, or reciprocity principles" — must be softened to "No study
referenced Indigenous frameworks or reciprocity principles, and only one employed
an explicit cultural frame."

**Line 246** — "with few participants across the studies reporting serious
adverse events" is now quantifiable. Consider: "with severe adverse events
recorded in 24 of 186 discrete events across the 43 trials, and 78% of recorded
events graded mild."

**Line 260 (Limitations)** — the sentence "the AI-based extraction process may
have led to errors and misinterpretation of codes" is true but now
under-specified, and you have the data to replace hand-waving with a number.
Suggested replacement paragraph:

> A further limitation concerns the extraction process. Coding was performed by
> an isolated language-model subagent per article under a pinned prompt, then
> validated by a deterministic gate and re-adjudicated against source texts
> wherever the automated coding disagreed with a prior independent hand
> extraction. After correction the two methods agree on 89.5% of all comparable
> extracted cells (2,126 of 2,376); across the 281 fields that required
> adjudication, the automated value was upheld in 51% and the hand-extracted
> value in 26%. The most frequent automated
> error modes were the omission of statistics reported only inside tables in
> degraded scans, the selection of a secondary rather than a pre-specified
> primary endpoint, and an over-liberal reading of criterion fields — most
> notably power, where any statement justifying a sample size was initially
> credited as a power calculation. All fields resolved in favour of the hand
> extraction were corrected in the analytic dataset. A residual 29 fields (10%)
> could not be resolved from the source texts because the articles themselves are
> ambiguous — most often where a paper reports several defensible denominators
> for retention or final sample size, or states no baseline severity
> classification. These were left at their extracted values and are reported
> here as an irreducible uncertainty rather than a correctable error.

---

## 11. Two data-integrity items you should know about

Both were found by cross-checking the effect-size configuration against the
adjudicated dataset, and both are already fixed in `scripts/_config_*.py`.

1. **Rothberg 2021 sign error (material).** Its Hedges' g was **−0.59**, plotting
   the study as evidence of harm, when the paper reports ketamine reducing
   at-risk drinking roughly five-fold. Cause: the odds ratio was recomputed from
   Table 2 proportions in the orientation where >1 already favours ketamine,
   while the frozen entry's `direction: −1` — written to pair with an OR
   expressed the other way round — was carried forward unchanged. The two
   negations compounded. Now **+0.59**.
2. **Das 2019 wrong statistic.** The conversion was keyed to ηp² = 0.219, which
   the adjudication identified as belonging to a secondary post-consumption urge
   measure. Re-keyed to the primary drinking outcome, ηp² = 0.14. g: 1.05 → 0.80.

I also found and fixed a false positive in the visual-regression checker: it
compared title/legend pixel bands whenever image height was unchanged, but the
figure height has a floor, so a figure sitting at that floor keeps its canvas
size while losing a row and re-centres its content. The check now also requires
an unchanged plotted-row count.

---

## 12. Open items requiring your decision

| # | Item | Status |
|---|---|---|
| 1 | **Ludwig 1969** — no frozen row exists and the PDF is unusable. It has never contributed to any manuscript number. Add only if you can supply a readable copy. | Blocked on source |
| 2 | **Hollister 1969** stays in Tier 1 per your instruction, on the 2-month F statistic. The adjudication designates the 6-month null as primary. Needs a footnote saying so, or reviewers will find it. | Needs footnote text |
| 3 | **Fixed vs random effects** for the Table 5 pooled estimate. I used random-effects; the Methods do not currently state which. | Needs one sentence in §3.1 |
| 4 | **17 config proposals remain pending** human ratification. All 12 eligible ones already have hand-written frozen entries that were kept, so nothing is unkeyed — but the divergences are unreviewed. | `outputs/config_proposals/` |
| 5 | **`InterventionDescription` is the literal value `1`** in all 44 frozen rows, where the codebook specifies ≤30 words of free text. Table 3 reports it as 100% "described", which is technically true of the new extraction but was never true of the old. | Cosmetic but worth a look |
| 6 | **Observational-study rows in Table 4** were not regenerated — they come from the separate `observational_studies` pipeline and are outside this rebuild. | Unchanged, verify separately |
