# Manual smoke-test checklist

Purpose: verify a locally running VerityAI end to end. An **HTTP 200 only means the request
succeeded** — it does *not* mean the verdict is correct. Always read the cited evidence and judge
the result yourself. Never assume an expected verdict.

## Prerequisites

Models are cached (see `.env.example`, `HF_HOME`). Start the server in one terminal:

```powershell
cd "D:\project ideas\VerityAI"
$env:HF_HOME = "D:\hf-cache"                 # point at the existing model cache
.\.venv\Scripts\python.exe scripts\run_dev.py
```

Wait for `GET /health` to report both models loaded, then run the cases below from the same machine.

## Helper

```powershell
function Check($payload) {
  $b = $payload | ConvertTo-Json -Compress
  $r = Invoke-WebRequest http://127.0.0.1:8000/api/analyze -Method Post `
        -ContentType "application/json" -Body $b -UseBasicParsing
  $j = $r.Content | ConvertFrom-Json
  foreach ($c in $j.claims) {
    "HTTP $($r.StatusCode) | status=$($c.status) type=$($c.claim_type) | $($c.text)"
    ($c.supporting + $c.contradicting) | Select-Object -First 2 |
      ForEach-Object { "    [$($_.source)] nli=$([math]::Round($_.nli_score,3)) $($_.url)" }
  }
}
```

## Cases

Record the **observed** status and the top cited URL for each; decide correctness from the evidence.

| # | Case | Command | Observed status / cited URL |
|---|---|---|---|
| 1 | Factual, known true | `Check @{claim="World War II ended in 1945."}` | |
| 2 | Factual, false | `Check @{claim="The Great Wall of China is located in Japan."}` | |
| 3 | Opinion — expect `NOT_VERIFIABLE`, no retrieval | `Check @{claim="Chocolate is the best ice cream flavor."}` | |
| 4 | Prediction — expect `NOT_VERIFIABLE` | `Check @{claim="Bitcoin will reach one million dollars by 2030."}` | |
| 5 | Insufficient evidence (niche/nonsense) | `Check @{claim="The Zorbax-9 spacecraft landed on the Sun in 2019."}` | |
| 6 | URL input | `Check @{url="https://en.wikipedia.org/wiki/Eiffel_Tower"}` | |
| 7 | Hindi (accepted; quality unverified) | `Check @{claim="भारत की राजधानी नई दिल्ली है।"}` | |
| 8 | Hinglish (accepted; quality unverified) | `Check @{claim="Bharat ki rajdhani New Delhi hai."}` | |

## How to read a result

- The **HTTP status** is transport; the **verdict, explanation and evidence** are the substance.
- Open the cited URL and confirm the passage really says what the item claims.
- `INSUFFICIENT_EVIDENCE` and `CONFLICTING_EVIDENCE` are honest non-commitments, not failures.
- `NOT_VERIFIABLE` for an opinion/prediction/allegation/unclear statement is correct behaviour.
- The analysis endpoints are rate-limited to **10 requests / 60 seconds per client** (HTTP 429).

## Known limitations to expect (see `README.md` and `docs/EVALUATION.md`)

- Retrieval can pull a **different entity with a similar name** (e.g. Eiffel Tower vs Eiffel Tower
  (Paris, Texas)), which can surface as `CONFLICTING_EVIDENCE` for a simple claim.
- A **confident single-source error** is possible: the single-source safeguard only downgrades below
  `tau_single` (default 0.75).
- **Hindi/Hinglish** input is accepted but the models are English-first; verdict quality is
  **unverified** and the NLI model can return wrong verdicts on non-English text.
- A source may fail transiently (`status="error"` in `sources_queried`), e.g. upstream throttling.
