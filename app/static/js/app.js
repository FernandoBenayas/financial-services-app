/* Financial Services AI Workbench — client-side logic */

let isStreaming = false;
let abortController = null;

/* ── Initialization ── */

document.addEventListener("DOMContentLoaded", () => {
    restoreSettings();
});

function restoreSettings() {
    const provider = localStorage.getItem("fs_provider") || "anthropic";
    const providerSel = document.getElementById("provider-select");
    if (providerSel) {
        providerSel.value = provider;
        filterModels(provider);
        const savedModel = localStorage.getItem("fs_model_" + provider);
        if (savedModel) {
            const modelSel = document.getElementById("model-select");
            if (modelSel) modelSel.value = savedModel;
        }
    }
    updateProviderBadge(provider);
}

function onProviderChange() {
    const provider = document.getElementById("provider-select").value;
    filterModels(provider);
    localStorage.setItem("fs_provider", provider);
    updateProviderBadge(provider);
}

function filterModels(provider) {
    const sel = document.getElementById("model-select");
    if (!sel) return;
    let firstVisible = null;
    for (const opt of sel.options) {
        const show = opt.dataset.provider === provider;
        opt.style.display = show ? "" : "none";
        if (show && !firstVisible) firstVisible = opt;
    }
    if (firstVisible) sel.value = firstVisible.value;
}

function updateProviderBadge(provider) {
    const badge = document.getElementById("provider-badge");
    if (!badge) return;
    if (provider === "anthropic") {
        badge.textContent = "Anthropic";
        badge.className = "badge bg-success me-2";
    } else {
        badge.textContent = "Mistral";
        badge.className = "badge bg-warning text-dark me-2";
    }
}

/* ── Ticker Lookup ── */

async function lookupTicker(fieldName) {
    const input = document.getElementById("field-" + fieldName);
    const infoDiv = document.getElementById("ticker-info-" + fieldName);
    if (!input || !infoDiv) return;

    const ticker = input.value.trim().toUpperCase();
    if (!ticker) return;

    infoDiv.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Looking up…';

    try {
        const resp = await fetch("/api/lookup_ticker", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ticker }),
        });
        const data = await resp.json();
        if (data.error) {
            infoDiv.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-circle me-1"></i>' + data.error + '</span>';
        } else {
            const mcap = data.market_cap ? formatNumber(data.market_cap) : "N/A";
            infoDiv.innerHTML =
                '<span class="text-success"><i class="fas fa-check-circle me-1"></i></span>' +
                '<strong>' + data.name + '</strong> | ' +
                data.sector + ' | ' + data.industry +
                ' | Mkt Cap: $' + mcap;

            // Auto-fill company name field if empty
            const nameField = document.getElementById("field-company_name");
            if (nameField && !nameField.value) {
                nameField.value = data.name;
            }
        }
    } catch (e) {
        infoDiv.innerHTML = '<span class="text-danger">Lookup failed</span>';
    }
}

function formatNumber(n) {
    if (n >= 1e12) return (n / 1e12).toFixed(2) + "T";
    if (n >= 1e9) return (n / 1e9).toFixed(2) + "B";
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    return n.toLocaleString();
}

/* ── Skill Execution ── */

async function executeSkill(skillId) {
    if (isStreaming) {
        if (abortController) abortController.abort();
        isStreaming = false;
        updateSubmitButton(false);
        return;
    }

    const provider = document.getElementById("provider-select")?.value || "anthropic";
    const model = document.getElementById("model-select")?.value || "";

    localStorage.setItem("fs_provider", provider);
    localStorage.setItem("fs_model_" + provider, model);

    // Collect form data
    const formData = {};
    const form = document.getElementById("skill-form");
    if (form) {
        for (const el of form.elements) {
            if (el.name && el.name !== "" && el.type !== "file" && el.id !== "provider-select" && el.id !== "model-select") {
                formData[el.name] = el.value;
            }
        }
    }

    // Read file content if present
    let fileContent = "";
    const fileInput = form?.querySelector('input[type="file"]');
    if (fileInput?.files?.length) {
        fileContent = await readFileContent(fileInput.files[0]);
    }

    // Show status
    showStatus("Initializing…");
    isStreaming = true;
    updateSubmitButton(true);

    abortController = new AbortController();

    try {
        const resp = await fetch("/api/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                skill_id: skillId,
                form_data: formData,
                provider,
                model,
                file_content: fileContent,
            }),
            signal: abortController.signal,
        });

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullText = "";
        let analysisStarted = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                try {
                    const payload = JSON.parse(line.slice(6));

                    if (payload.status) {
                        updateStatus(payload.status);
                    }

                    if (payload.chunk) {
                        if (!analysisStarted) {
                            analysisStarted = true;
                            hideStatus();
                            showOutput();
                        }
                        fullText += payload.chunk;
                        renderMarkdown(fullText);
                    }

                    if (payload.done) {
                        hideStatus();
                        if (fullText) renderMarkdown(fullText, false);
                    }

                    if (payload.error) {
                        showError(payload.error);
                    }
                } catch (e) { /* skip malformed lines */ }
            }
        }
    } catch (e) {
        if (e.name !== "AbortError") {
            showError(e.message);
        }
    } finally {
        isStreaming = false;
        updateSubmitButton(false);
    }
}

/* ── File Reading ── */

async function readFileContent(file) {
    return new Promise((resolve) => {
        if (file.type.includes("text") || file.name.endsWith(".csv") ||
            file.name.endsWith(".json") || file.name.endsWith(".md")) {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.readAsText(file);
        } else {
            resolve(`[Binary file: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]`);
        }
    });
}

/* ── UI Helpers ── */

function showStatus(text) {
    const placeholder = document.getElementById("output-placeholder");
    const status = document.getElementById("output-status");
    const content = document.getElementById("output-content");
    const error = document.getElementById("output-error");

    if (placeholder) placeholder.style.display = "none";
    if (content) content.style.display = "none";
    if (error) error.style.display = "none";
    if (status) {
        status.style.display = "block";
        document.getElementById("status-text").textContent = text;
    }
}

function updateStatus(text) {
    const statusText = document.getElementById("status-text");
    const steps = document.getElementById("data-steps");
    if (statusText) statusText.textContent = text;

    if (steps && text !== "Generating analysis…") {
        const step = document.createElement("div");
        step.className = "data-step done";
        step.innerHTML = '<span class="step-icon"><i class="fas fa-check-circle"></i></span>' + escapeHtml(text);
        steps.appendChild(step);
    }
}

function hideStatus() {
    const status = document.getElementById("output-status");
    if (status) status.style.display = "none";
}

function showOutput() {
    const content = document.getElementById("output-content");
    const copyBtn = document.getElementById("copy-btn");
    const clearBtn = document.getElementById("clear-btn");
    if (content) content.style.display = "block";
    if (copyBtn) copyBtn.style.display = "inline-block";
    if (clearBtn) clearBtn.style.display = "inline-block";
}

function showError(msg) {
    const error = document.getElementById("output-error");
    if (error) {
        error.style.display = "block";
        error.textContent = msg;
    }
    hideStatus();
}

function renderMarkdown(text, streaming = true) {
    const el = document.getElementById("output-content");
    if (!el) return;
    el.innerHTML = marked.parse(text);
    if (streaming) el.classList.add("streaming-cursor");
    else el.classList.remove("streaming-cursor");

    const panel = document.getElementById("output-panel");
    if (panel) panel.scrollTop = panel.scrollHeight;
}

function updateSubmitButton(streaming) {
    const btn = document.getElementById("submit-btn");
    if (!btn) return;
    const skillId = btn.dataset.skillId || "";
    if (streaming) {
        btn.innerHTML = '<i class="fas fa-stop me-2"></i>Stop';
        btn.onclick = () => {
            if (abortController) abortController.abort();
            isStreaming = false;
            updateSubmitButton(false);
        };
    } else {
        btn.innerHTML = '<i class="fas fa-play me-2"></i>Run Analysis';
        btn.onclick = () => executeSkill(skillId);
    }
}

function copyOutput() {
    const el = document.getElementById("output-content");
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        const btn = document.getElementById("copy-btn");
        if (btn) {
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copied';
            setTimeout(() => { btn.innerHTML = orig; }, 1500);
        }
    });
}

function clearOutput() {
    const content = document.getElementById("output-content");
    const placeholder = document.getElementById("output-placeholder");
    const error = document.getElementById("output-error");
    const status = document.getElementById("output-status");
    const steps = document.getElementById("data-steps");
    const copyBtn = document.getElementById("copy-btn");
    const clearBtn = document.getElementById("clear-btn");

    if (content) { content.style.display = "none"; content.innerHTML = ""; }
    if (placeholder) placeholder.style.display = "block";
    if (error) error.style.display = "none";
    if (status) status.style.display = "none";
    if (steps) steps.innerHTML = "";
    if (copyBtn) copyBtn.style.display = "none";
    if (clearBtn) clearBtn.style.display = "none";
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
