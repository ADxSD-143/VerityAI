# data/

Local, **gitignored** caches used by the evaluation scripts. Nothing in here is
committed, and nothing here is required to run the application.

- `fever_corpus/` — Wikipedia page extracts fetched on demand by
  `experiments/_common.py::fetch_wikipedia_page` and cached as one JSON file per page.
  Reconstructed from live Wikipedia so we avoid downloading the multi-GB FEVER dump.

Model weights are not stored here; they live in the Hugging Face cache (`HF_HOME`).
