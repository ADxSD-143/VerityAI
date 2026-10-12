/* VerityAI frontend — vanilla JS, no build step.
   All externally-sourced text is inserted via textContent, never innerHTML. */
(function () {
  "use strict";

  const MODES = {
    claim: {
      label: "Claim",
      hint: "Submit one clear statement. Names, dates and numbers are kept as written.",
      placeholder: "e.g. The Eiffel Tower is located in Paris.",
      useUrl: false,
    },
    text: {
      label: "Article or paragraph text",
      hint: "Long text is split into sentences; likely factual claims are analysed individually.",
      placeholder: "Paste a paragraph or article text...",
      useUrl: false,
    },
    url: {
      label: "Article URL",
      hint: "Only public http/https pages are fetched. Private, local and cloud-metadata addresses are blocked.",
      placeholder: "",
      useUrl: true,
    },
  };

  const STATUS_LABELS = {
    SUPPORTED: "Supported",
    REFUTED: "Refuted",
    CONFLICTING_EVIDENCE: "Conflicting evidence",
    INSUFFICIENT_EVIDENCE: "Insufficient evidence",
    UNABLE_TO_ASSESS: "Unable to assess",
    NOT_VERIFIABLE: "Not directly verifiable",
  };

  // NOT_VERIFIABLE covers several claim types; label the badge with the actual reason rather
  // than implying every non-verifiable statement is an opinion.
  const CLAIM_TYPE_LABELS = {
    OPINION_SUBJECTIVE: "Opinion — not verifiable",
    PREDICTION: "Prediction — not verifiable",
    ALLEGATION: "Allegation — not verifiable",
    UNCLEAR: "No checkable claim",
  };

  function badgeLabel(claim) {
    if (claim.status === "NOT_VERIFIABLE") {
      return CLAIM_TYPE_LABELS[claim.claim_type] || STATUS_LABELS.NOT_VERIFIABLE;
    }
    return STATUS_LABELS[claim.status] || claim.status;
  }

  const $ = (id) => document.getElementById(id);
  const form = $("analyze-form");
  const textInput = $("text-input");
  const urlInput = $("url-input");
  const textLabel = $("text-label");
  const urlLabel = $("url-label");
  const hint = $("input-hint");
  const analyzeBtn = $("analyze-btn");
  const statusRegion = $("status-region");
  const results = $("results");

  let mode = "claim";
  let lastPayload = null;

  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const key of Object.keys(attrs)) {
        const value = attrs[key];
        if (value === null || value === undefined || value === false) continue;
        if (key === "class") node.className = value;
        else if (key === "text") node.textContent = value;
        else if (key.startsWith("on") && typeof value === "function")
          node.addEventListener(key.slice(2), value);
        else node.setAttribute(key, value === true ? "" : String(value));
      }
    }
    append(node, children);
    return node;
  }

  function append(node, children) {
    for (const child of children) {
      if (child === null || child === undefined || child === false) continue;
      if (Array.isArray(child)) append(node, child);
      else node.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
    }
  }

  function fmt(value) {
    if (value === null || value === undefined) return "—";
    const num = Number(value);
    return Number.isFinite(num) ? num.toFixed(2) : String(value);
  }

  function setMode(next) {
    mode = next;
    document.querySelectorAll(".tab").forEach((tab) => {
      const active = tab.dataset.mode === next;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    const config = MODES[next];
    textLabel.textContent = config.label;
    hint.textContent = config.hint;
    hint.classList.remove("error");
    textInput.placeholder = config.placeholder;
    textInput.hidden = config.useUrl;
    textLabel.hidden = config.useUrl;
    urlInput.hidden = !config.useUrl;
    urlLabel.hidden = !config.useUrl;
    (config.useUrl ? urlInput : textInput).focus();
  }

  function buildPayload() {
    if (mode === "url") {
      const url = urlInput.value.trim();
      if (!/^https?:\/\/\S+$/i.test(url)) {
        setHintError("Enter a full http:// or https:// URL.");
        return null;
      }
      return { url };
    }
    const text = textInput.value.trim();
    if (text.length < 5) {
      setHintError("Enter at least a few words.");
      return null;
    }
    return mode === "claim" ? { claim: text } : { text };
  }

  function setHintError(message) {
    hint.textContent = message;
    hint.classList.add("error");
  }

  function makeBanner(kind, message, options) {
    const opts = options || {};
    const children = [];
    if (opts.spinner) children.push(h("span", { class: "spinner", "aria-hidden": "true" }));
    children.push(h("span", { text: message }));
    if (opts.retry) children.push(h("button", { class: "ghost retry", type: "button", text: "Retry", onClick: opts.retry }));
    return h("div", { class: "banner " + kind }, ...children);
  }

  function setStatus(node) {
    statusRegion.replaceChildren(node || document.createTextNode(""));
  }

  function setLoading(loading) {
    analyzeBtn.disabled = loading;
    analyzeBtn.textContent = loading ? "Analyzing…" : "Analyze";
  }

  async function onSubmit(event) {
    event.preventDefault();
    const payload = buildPayload();
    if (!payload) return;
    lastPayload = payload;
    setLoading(true);
    results.replaceChildren();
    setStatus(makeBanner("info",
      "Retrieving evidence and running the NLI model. The first request can take longer while models load.",
      { spinner: true }));

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(friendlyError(response.status, body));
      }
      const report = await response.json();
      setStatus(null);
      renderReport(report);
    } catch (error) {
      setStatus(makeBanner("error", error.message || "Unexpected error.", {
        retry: () => onSubmit({ preventDefault() {} }),
      }));
    } finally {
      setLoading(false);
    }
  }

  function friendlyError(status, body) {
    if (status === 422) {
      const first = body && body.details && body.details.errors && body.details.errors[0];
      return (first && (first.msg || first.message)) || (body && body.error) || "Invalid input.";
    }
    if (status === 503) return (body && body.error) || "A required model is unavailable.";
    return (body && body.error) || ("Request failed with status " + status + ".");
  }

  function metaBlock(report) {
    const grid = h("dl", { class: "meta-grid" });
    const item = (label, value) =>
      h("div", { class: "meta-item" }, h("dt", { text: label }), h("dd", { text: value }));
    grid.appendChild(item("Input", report.input.kind + (report.input.title ? " — " + report.input.title : "")));
    if (report.input.url) grid.appendChild(item("URL", report.input.url));
    grid.appendChild(item("Claims analysed", String(report.claims.length)));
    grid.appendChild(item("Processing time", report.meta.processing_ms + " ms"));
    grid.appendChild(item("Created (UTC)", report.meta.created_at));
    grid.appendChild(item("Device", (report.meta.models[0] || {}).device || "cpu"));

    const models = h("p", { class: "evidence-meta" });
    (report.meta.models || []).forEach((model) => {
      models.appendChild(h("span", {
        class: "pill",
        text: model.name + ": " + model.model_id + (model.loaded ? "" : " (not loaded)"),
      }));
    });

    return h("div", { class: "result-block" },
      h("h3", { class: "block-title", text: "Analysis " + report.meta.analysis_id }),
      grid,
      report.input.value_preview ? h("p", { class: "claim-sub mono", text: report.input.value_preview }) : null,
      models);
  }

  function statRow(stats) {
    const stat = (label, value) =>
      h("div", { class: "stat" }, h("strong", { text: String(value) }), label);
    return h("div", { class: "stat-row" },
      stat("passages considered", stats.passages_considered),
      stat("supporting passages", stats.support_passages),
      stat("contradicting passages", stats.contradict_passages),
      stat("independent sources (support)", stats.support_sources),
      stat("independent sources (contradict)", stats.contradict_sources),
      stat("independent groups", stats.independent_groups));
  }

  function evidenceItem(item, kind) {
    const title = item.url
      ? h("a", { class: "evidence-title", href: item.url, target: "_blank", rel: "noopener noreferrer", text: item.title || item.url })
      : h("span", { class: "evidence-title", text: item.title || "Untitled source" });

    const meta = h("div", { class: "evidence-meta" },
      h("span", { text: item.publisher || item.source }),
      item.published_at ? h("span", { text: "published " + item.published_at }) : null,
      h("span", { text: "retrieved " + (item.retrieved_at || "") }),
      item.nli_label ? h("span", { class: "pill " + item.nli_label, text: item.nli_label + " " + fmt(item.nli_score) }) : null,
      item.rank ? h("span", { class: "pill", text: "rank #" + item.rank }) : null,
      item.retrieval_score !== null && item.retrieval_score !== undefined
        ? h("span", { class: "pill", text: "relevance " + fmt(item.retrieval_score) }) : null,
      item.independent_group !== null && item.independent_group !== undefined
        ? h("span", { class: "pill", text: "source group " + item.independent_group }) : null);

    return h("div", { class: "evidence-card " + kind },
      title,
      meta,
      h("blockquote", { text: item.passage }),
      item.note ? h("div", { class: "evidence-meta", text: item.note }) : null);
  }

  function evidenceSection(kind, title, items) {
    return h("div", { class: "evidence-section " + kind },
      h("h4", { text: title + " (" + items.length + ")" }),
      items.map((item) => evidenceItem(item, kind)));
  }

  function factCheckBlock(items) {
    const box = h("div", { class: "factcheck" }, h("h4", { text: "Publisher fact-checks (shown separately, not treated as ground truth)" }));
    items.forEach((fc) => {
      box.appendChild(h("p", null,
        h("span", { class: "verdict", text: fc.publisher_verdict }),
        " — ",
        fc.url ? h("a", { href: fc.url, target: "_blank", rel: "noopener noreferrer", text: fc.publisher }) : h("span", { text: fc.publisher }),
        fc.reviewed_at ? h("span", { class: "muted", text: " (" + fc.reviewed_at + ")" }) : null));
    });
    return box;
  }

  function claimCard(claim) {
    const head = h("div", { class: "claim-head" },
      h("p", { class: "claim-text", text: claim.text }),
      h("span", { class: "badge " + claim.status, text: badgeLabel(claim) }),
      h("p", { class: "explanation", text: claim.explanation }),
      claim.limited_corroboration
        ? h("p", { class: "limited-note", text: "Corroboration is limited: the decisive evidence comes from a single independent source." }) : null,
      claim.claim_notes && claim.claim_notes.length
        ? h("ul", { class: "claim-notes" }, claim.claim_notes.map((note) => h("li", { text: note }))) : null);

    const body = h("div", { class: "claim-body" }, statRow(claim.stats));
    if (claim.supporting.length) body.appendChild(evidenceSection("support", "Supporting evidence", claim.supporting));
    if (claim.contradicting.length) body.appendChild(evidenceSection("contradict", "Contradicting evidence", claim.contradicting));
    if (claim.neutral.length) body.appendChild(evidenceSection("neutral", "Neutral / insufficient evidence", claim.neutral));
    if (claim.fact_checks && claim.fact_checks.length) body.appendChild(factCheckBlock(claim.fact_checks));
    if (!claim.supporting.length && !claim.contradicting.length && !claim.neutral.length) {
      body.appendChild(h("p", { class: "empty-state", text: "No evidence passages were retrieved for this claim from the permitted sources." }));
    }

    return h("article", { class: "claim-card" }, head, body);
  }

  function sourcesBlock(records) {
    const table = h("table", { class: "sources" },
      h("thead", null, h("tr", null,
        h("th", { text: "Source" }),
        h("th", { text: "Status" }),
        h("th", { text: "Results" }),
        h("th", { text: "Queries / error" }))));
    const tbody = h("tbody");
    records.forEach((record) => {
      tbody.appendChild(h("tr", null,
        h("td", { text: record.source }),
        h("td", null, h("span", { class: "status-" + record.status, text: record.status })),
        h("td", { text: String(record.n_results) }),
        h("td", { class: "mono", text: record.error || (record.queries || []).join(" | ") })));
    });
    table.appendChild(tbody);
    return h("div", { class: "result-block" },
      h("h3", { class: "block-title", text: "Sources queried" }),
      records.length ? table : h("p", { class: "empty-state", text: "No sources were queried." }));
  }

  function renderReport(report) {
    const frag = document.createDocumentFragment();
    if (report.meta.degraded_mode) {
      frag.appendChild(h("div", { class: "result-block" },
        h("div", { class: "banner warn" },
          h("span", { text: "Degraded mode — " + report.meta.degraded_reasons.join("; ") }))));
    }
    frag.appendChild(metaBlock(report));
    report.claims.forEach((claim) => frag.appendChild(claimCard(claim)));
    frag.appendChild(sourcesBlock(report.sources_queried || []));
    frag.appendChild(h("div", { class: "result-block" },
      h("h3", { class: "block-title", text: "Limitations and uncertainty" }),
      h("ul", { class: "limitations" }, (report.meta.limitations || []).map((text) => h("li", { text })))));
    results.replaceChildren(frag);
    if (report.claims.length) results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  document.querySelectorAll(".tab").forEach((tab) =>
    tab.addEventListener("click", () => setMode(tab.dataset.mode)));

  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      setMode("claim");
      textInput.value = chip.dataset.example;
      hint.classList.remove("error");
      textInput.focus();
    }));

  $("clear-btn").addEventListener("click", () => {
    textInput.value = "";
    urlInput.value = "";
    hint.classList.remove("error");
    results.replaceChildren();
    setStatus(null);
    setHintForMode();
  });

  function setHintForMode() {
    hint.textContent = MODES[mode].hint;
    hint.classList.remove("error");
  }

  form.addEventListener("submit", onSubmit);
  setMode("claim");
})();
