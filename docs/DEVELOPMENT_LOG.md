# Development log

Newest first. Records decisions, real errors and their root causes, and lessons learned.

## 2026-10-12 — Fix: pronoun-initial sentences misclassified as UNCLEAR

- **Found during Phase 1 manual testing**: `classify_claim_type`'s `_UNCLEAR` rule matched *any*
  sentence starting with `it`/`this`/`that`/`they`, so concrete facts read from an article ("It was
  completed in 1889...", "This tower is located in Paris.") were labelled `UNCLEAR` and skipped the
  evidence pipeline (returned `NOT_VERIFIABLE`).
- **Fix**: removed the bare pronouns from the vague-subject rule, keeping the genuinely vague
  subjects (`things`, `stuff`, `everyone`, `nobody`, `everything`, `nothing`, `the situation`,
  `the system`, `the government`). Verified live: the Eiffel Tower article's "It is named after the
  engineer Gustave Eiffel..." is now `CHECKABLE_FACT` and analysed instead of `NOT_VERIFIABLE`.
- Regression test `test_pronoun_initial_factual_sentences_are_checkable`. **178 tests pass, ruff
  clean.**

## 2026-10-12 — Honest NOT_VERIFIABLE badge in the UI

- **Found**: the frontend labelled **every** `NOT_VERIFIABLE` claim "Opinion / not directly
  verifiable", which is wrong for predictions, allegations and unclear statements.
- **Fix**: the badge now reflects the actual claim type (Opinion / Prediction / Allegation — not
  verifiable; No checkable claim), falling back to a neutral "Not directly verifiable". The frontend
  test asserts the claim-type labels are present and the misleading string is gone. 177 tests pass,
  ruff clean.

## 2026-10-12 — Control-doc reconciliation

- **Found**: `PLAN.md` M2 still recorded "hybrid retained as default", contradicting the shipped
  implementation (`verity_retrieval_mode="dense"`) and `docs/EVALUATION.md`. `docs/READINESS.md`
  pinned a stale snapshot (`main` = `875f042`) and a stale CI run, and `docs/PROJECT_STATUS.md`
  listed a stale CI run, commit and test count.
- **Fix**: M2 now states that a later harder-corpus run superseded the hybrid default and that the
  runtime default is dense-only; the READINESS snapshot/CI line, the PROJECT_STATUS GitHub/CI/test
  rows are updated to the current verified state (177 tests; CI run #38 on `25f435d`, 2026-10-12).
  No behavioural change; documentation only.

## 2026-10-12 — Explicit NAT64 SSRF blocking + IPv6 transition regression tests

- **Found (while auditing)**: the SSRF validator blocked NAT64 (`64:ff9b::/96`) and IPv4-translated
  (`::ffff:0:0/96`) destinations only *incidentally*, via `ipaddress.is_reserved`; only 6to4 and
  teredo had dedicated handling. `is_reserved` semantics are Python-version-dependent, so the NAT64
  block was fragile.
- **Fix**: added the NAT64 well-known (`64:ff9b::/96`) and local-use (`64:ff9b:1::/48`) prefixes to
  the explicit blocked-network list in `url_extract.py`. 6to4 stays blocked via the `sixtofour`
  property and teredo via `is_private` (2001::/32).
- **Tests**: extended `test_blocked_addresses` from 11 to 25 cases — IPv4 reserved/documentation
  ranges, IPv6 unique-local/link-local, and the IPv4-mapped / IPv4-translated / 6to4 / teredo / NAT64
  transition forms that embed a private destination. **177 tests pass, ruff clean.**
- Lesson: a security control that relies on a stdlib predicate's *incidental* coverage is not a
  control; make the blocked ranges explicit and lock them with tests. No production behaviour changed
  for the previously-blocked cases (the tests still pass).

## 2026-10-12 — Hindi/Hinglish claim-type and negation parity (Phase 3)

- **Gap**: `classify_claim_type` matched only English markers plus `sabse`/`सबसे`, so a
  Hindi/Hinglish **prediction** ("... honge") or **allegation** ("... aarop laga") was classified
  `CHECKABLE_FACT` and forced through the true/false verdict pipeline — the non-verifiable path was
  English-only. `has_negation` likewise only saw English, so the "contains negation" disclosure was
  missing for Hindi claims.
- **Fix**: added deterministic Hindi/Hinglish markers for opinion (`mujhe lagta`, `mere khayal`,
  `मुझे लगता`, `मेरे ख्याल`), prediction (`hoga`/`jayega`/`karega`/`rahega` families and their
  Devanagari forms) and allegation (`aarop`/`ilzaam`/`आरोप`/`इलज़ाम`), plus `nahi`/`nahin`/`नहीं` in
  `has_negation`. Not tuned on any labelled set; the marker lists are deliberately finite and are not
  exhaustive.
- Tests: `test_hindi_and_hinglish_first_person_opinions`, `..._predictions`, `..._allegations`, and
  `test_has_negation_handles_hindi_and_hinglish`. **163 tests pass, ruff clean.**
- **Unverified**: these rules are unit-tested only; classifier accuracy against a human-labelled set
  remains an open Phase 2 gate (no labels), and Hindi/Hinglish quality remains unverified.

## 2026-10-12 — Roman-Hinglish + danda claim extraction (Phase 3)

- **Found**: `looks_like_claim` accepted Devanagari copulas (`है`, `था`, ...) but had no Roman-script
  equivalent, so **every** Hinglish sentence ("Bharat ki rajdhani New Delhi hai.") was rejected and a
  Hinglish article collapsed to one whole-text claim. The single accidental pass relied on an English
  word ("...100 centuries..." matched `[a-z]{3,}s`).
- **Found**: the sentence-boundary regex (`[.!?]`) omitted the Devanagari danda `।`/`॥`, so a
  three-sentence Hindi paragraph was extracted as **one** claim.
- **Fix 1**: added `_VERB_HINT_HINGLISH`, Roman transliterations of the same copulas/auxiliaries
  (`hai, hain, tha, thi, hoga, gaya, kiya, karta, raha, hota, hua, sthit, ...`), wired into
  `looks_like_claim`. `the` is deliberately excluded — it is a high-frequency English article and
  would over-accept English fragments.
- **Fix 2**: added `।`/`॥` to `_BOUNDARY`; danda-terminated text now segments per sentence.
- Tests: Roman-Hinglish acceptance, a negative English-fragment case (the hint must not leak), and
  danda segmentation at both the text and claim-extraction levels. **159 tests pass, ruff clean.**
- Scope unchanged: models remain English-first and Hindi quality is still **unverified** (no labelled
  set). The `<5`-token floor still rejects very short fragments ("Bharat ek desh hai."), consistent
  with English behaviour.

## 2026-10-11 — Classifier diagnostic vs proposed annotations

- Ran the rules classifier over the 100 **machine-proposed** candidate rows as a *diagnostic* (the
  proposed types are **not ground truth**): 94/100 agreed after adding a Hinglish/Hindi superlative
  marker (`sabse` / `सबसे`). The 6 remaining disagreements are genuinely hard — evaluative or unclear
  statements ("Summer is the most pleasant season.", "They should do something about it.") and a
  conviction phrased as fact ("A court found a defendant guilty...").
- Deliberately **not** tuned to match the proposed labels — that would be fitting to unreviewed
  machine labels. Evaluative comparatives ("X is larger than Y" is often factual) were left out.
- Lesson: use proposed labels only to find rule blind spots, never as an accuracy target.

## 2026-10-11 — Phase 1/2/3 increments (evidence, claim handling, scripts)

- **Phase 1**: optional keyless **Wikinews** source (`VERITY_ENABLE_WIKINEWS`, off by default),
  reusing the MediaWiki adapter; provenance/recency disclosure in the report (publication-date
  limitation + per-claim count of undated passages).
- **Phase 2**: deterministic rules-based claim-type classifier; **opinions / predictions / unclear**
  short-circuit to `NOT_VERIFIABLE` (no retrieval, no true/false). **Allegations** run the pipeline
  but are always `NOT_VERIFIABLE`, with alleged-vs-official-finding disclosure. The held-out harness
  now scores claim-type accuracy. Classifier **accuracy is not yet evaluated** (needs labels).
- **Phase 3 (groundwork)**: tokenization is Unicode-aware and claim detection accepts Devanagari
  copulas/verbs, so Hindi statements are extracted rather than rejected. Models remain English-first;
  Hindi quality is **unverified**.
- **Lesson**: keep rule-based behaviour conservative and default-off when its value is unmeasured;
  disclose rather than decide (allegations) and expose what is unknown (recency, language).

## 2026-10-11 — Script-aware tokenization fixes non-Latin source independence

- **Fix**: `app.core.text.tokenize` now uses a Unicode-aware pattern (`[^\W_]+`) instead of
  `[A-Za-z0-9]+`, so Devanagari / non-Latin text produces tokens. ASCII tokenization is unchanged.
- `shingles()` now returns an empty set for token-less text (the old `"<empty>"` fallback made every
  token-less string identical), and `jaccard()` treats an empty shingle set as "no comparable content"
  (0.0) instead of 1.0. Distinct non-Latin / punctuation-only passages are therefore no longer merged
  into one "independent" source, which had overstated corroboration.
- Regression tests added at the text level and at `analysis/independence` (`cluster_passages`).
- Still unsupported (Phase 3): `looks_like_claim`'s verb hint is Latin-only, so pure-Hindi claims are
  not extracted. Documented, not changed here.

## 2026-10-10 — Annotation tooling; Latin-only tokenizer limitation

- Added `experiments/annotation_tools.py` (+ `backend/tests/test_annotation_tools.py`) to validate
  annotation CSVs and detect claim / near-duplicate leakage across the tuning/held-out split before
  any metric is computed. It never fills labels.
- **Found while testing**: `app.core.text.tokenize` uses `[A-Za-z0-9]+` (Latin-only), so non-Latin
  text (e.g. Devanagari) yields **zero** tokens; `shingles()` then falls back to a single `"<empty>"`
  gram, so *every* token-less text has Jaccard 1.0 with every other. This made three distinct Hindi
  claims look identical. Leakage detection now uses script-agnostic character n-grams.
- **Latent risk (not fixed here)**: the same collapse affects `analysis/independence.cluster_passages`
  for short (<5 Latin-token) and non-Latin passages — distinct passages can be merged into one
  "independent" source, which would overstate corroboration. Relevant to Phase 3 (Hindi/Hinglish).
  Recorded in `docs/READINESS.md`; not changed in this cycle to avoid altering clustering behaviour
  without measured justification.

## 2026-10-10 — NLI re-evaluation: base CI recorded, small model blocked

- Re-ran the NLI evaluation on the current code. Base model `DeBERTa-v3-base-mnli-fever-anli`:
  accuracy **0.675** [0.633, 0.716], macro-F1 **0.671** [0.630, 0.712], mean latency
  **159.9 ms/pair** [155.6, 165.1] (2000-resample percentile bootstrap; `eval_nli.json`).
- **Blocker**: `cross-encoder/nli-deberta-v3-small` failed to load — its DeBERTa-v2 tokenizer imports
  `sentencepiece`, and the host's Windows Application Control policy blocks the `sentencepiece` DLL
  (`ImportError: DLL load failed ... blocked by an Application Control policy`). Same policy class
  that forced older sklearn/pandas/pyarrow pins. The small model cannot be evaluated on this host;
  the historical 0.448/0.458 point estimates are not reproducible here and now carry no CI.
- Latency rose vs the earlier 90.5 ms/pair because the host was under CPU contention during the run
  (several stray Python processes); it is contention-dependent, not a model regression.
- **Lesson**: an application-control policy is a real evaluation constraint — a candidate model is
  only usable if its tokenizer/deps are permitted on the target host.

## 2026-10-10 — Single-source aggregation safeguard (false-positive fix)

- **Problem**: `docs/experiments/004-end-to-end.md` recorded the nonsense claim "Zorbax-9 … land on
  the Sun." reported `SUPPORTED` from one passage. The cause is aggregation, not retrieval or NLI:
  a single entailment ≥ `tau` (0.5) carried a verdict with no minimum evidence mass.
- **Fix**: a verdict resting on a **single independent source** must clear a higher bar, `tau_single`
  (`VERITY_TAU_NLI_SINGLE_SOURCE`, default 0.75); below it the status is `INSUFFICIENT_EVIDENCE`.
  Corroborated verdicts keep `tau`. Not tuned on the 8-claim set.
- **Measured re-check (live, one observation)**: the claim now returns `INSUFFICIENT_EVIDENCE`; its
  lone supporting passage (Wikidata "Sun Microsystems: instance of — software company.") scored
  entailment **0.519** — above `tau`, below `tau_single`.
- **Mechanism**: DeBERTa NLI is not a fact-checker; it matched salient tokens ("Sun") to an
  unrelated entity, the classic single-spurious-entailment mode.
- **Trade-off**: a genuine claim supported by only one weak source is now downgraded to
  `INSUFFICIENT_EVIDENCE` (recall↓ / precision↑ for `SUPPORTED`). A confident spurious entailment
  (≥ `tau_single`) from a lone source still passes — documented, not eliminated.
- **Tests**: `test_aggregation_regression.py` reproduces the failure shape; `test_aggregation.py`
  covers weak single-source support/contradiction, a preserved conflict, and a confident
  single-source verdict; `test_analyzer.py` verifies the setting is threaded end-to-end.

## 2026-10-10 — M2/M3 evaluation: real errors and fixes

- **Windows Application Control blocked newest wheels.** `scikit-learn 1.9.1`,
  `pandas 3.0.6` and `pyarrow 26.0.0` failed with *"DLL load failed ... blocked by an
  Application Control policy"*. Because `transformers` imports sklearn when it is installed,
  this also broke `transformers` → `sentence-transformers`. **Root cause**: the policy blocks
  the newly released binaries, not these libraries in general. **Fix**: pin
  `scikit-learn==1.5.2`, `pandas==2.2.3`, `pyarrow==17.0.0` (older, allowed). All imports OK.
- **FEVER dataset schema.** The HF `fever` `v1.0` config has **no `validation` split**; the
  development split is `labelled_dev`, and it requires `trust_remote_code=True`. Its rows are
  **flattened** (one row per evidence annotation, so claim ids repeat) with scalar
  `evidence_wiki_url` / `evidence_sentence_id` columns and `-LRB-`/`-RRB-` encoded titles.
  **Fix**: group rows back into claims and decode titles. Result: 500 claims, 333 with gold
  evidence, 367 gold pages, plus 800 deterministic distractor pages → 1167-page corpus.
- **`py` launcher broken**; **PyPI CDN throttled** (~33 KB/s vs ~245 KB/s on a mirror) — the
  install was switched to a PyPI mirror.
- **Performance bug in `eval_retrieval.py`**: `tfidf.transform(texts)` was recomputed for every
  claim, and `titles.index(...)` (O(n)) was used inside the per-claim loop. **Fix**: build the
  TF-IDF matrix once and use a `title → index` dict.
- **Measured reality**: corpus embedding of ~1161 Wikipedia pages with `bge-small-en-v1.5` on
  this CPU costs several minutes of real compute (~7 cores busy); cross-encoder reranking of
  333 × 20 pairs is the other dominant cost. Numbers, not assumptions, drove the evaluation
  runtime.
- **Lesson**: verify the evaluation dataset schema and the host's application-control policy
  *before* building on them.

## 2026-10-10 — M0: environment audit and control files

- **Environment**: Windows, Python 3.11.7, pip 26.2.1 (in venv), Node v24.15.0, git 2.55.0,
  i7-12650HX (14c/20t), 15.7 GB RAM, RTX 4050 (unused; CPU default), D: has 213 GB free.
- **Findings that changed the plan**:
  - The `py` launcher is broken (points at a missing `C:\Program Files\Python314`) → use the
    `python` executable directly.
  - **`gh` CLI is not installed** and there is no GitHub CLI config → the `gh repo create`
    workflow is blocked until it is installed/authenticated.
  - **No Hugging Face token** is present (`HF_TOKEN` unset, no cached token) → automated Space
    deploy is blocked until the user authenticates.
  - PyPI throughput from this host is slow (~30–80 KB/s for the first wheels), so the initial
    dependency install (dominated by the ~200 MB CPU torch wheel) is slow but not blocked.
- **Decisions**: vanilla no-build frontend; Hugging Face Spaces (Docker) as the deploy target;
  CPU-only torch; deterministic regex sentence segmentation instead of spaCy (smaller install,
  fully deterministic, no model download); a `VERITY_PRELOAD_MODELS` switch so tests never
  download models.
- **Lessons**: verify the toolchain *before* depending on it — `gh` and HF auth assumptions were
  wrong, so those steps are prepared rather than assumed.

## 2026-10-10 — M1: application skeleton and real retrieval

- Built the FastAPI app, the source adapters (Wikipedia/Wikidata/OpenAlex/FactCheck), the
  retrieval/dense/fusion modules, NLI + aggregation, the SSRF-safe fetcher, and the frontend.
- Design choice: each adapter **fails soft** (`status="error"`) so one broken source never fails
  a request; combined with "all sources failed → `UNABLE_TO_ASSESS`" this preserves the
  no-fabrication rule.
- Design choice: NLI label order is read from `config.id2label` and validated; a model that
  cannot be resolved is a hard load error rather than a silent mis-mapping.
- Design choice: aggregation counts **independent source groups** (document key plus
  near-duplicate text merge) so syndicated copies cannot inflate corroboration.
