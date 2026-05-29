/* Financial Services AI Workbench — Client JS */

// ── State ──
let currentProvider = localStorage.getItem("fs-provider") || "anthropic";
let currentModel = localStorage.getItem("fs-model") || "";
let isStreaming = false;
let abortController = null;

// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
    restoreSettings();
    setupProviderToggle();
});

function restoreSettings() {
    const providerSel = document.getElementById("global-provider");
    const chatProvider = document.getElementById("chat-provider");
    if (providerSel) providerSel.value = currentProvider;
    if (chatProvider) {
        chatProvider.value = currentProvider;
        filterModels(currentProvider);
    }
    updateProviderBadge();
}

function setupProviderToggle() {
    const chatProvider = document.getElementById("chat-provider");
    if (!chatProvider) return;
    chatProvider.addEventListener("change", (e) => {
        currentProvider = e.target.value;
        filterModels(currentProvider);
        updateProviderBadge();
    });
}

function filterModels(provider) {
    const modelSel = document.getElementById("chat-model");
    if (!modelSel) return;
    Array.from(modelSel.options).forEach((opt) => {
        const optProvider = opt.dataset.provider;
        if (optProvider === provider) {
            opt.classList.remove("d-none");
            opt.disabled = false;
        } else {
            opt.classList.add("d-none");
            opt.disabled = true;
        }
    });
    // Select first visible option
    const first = modelSel.querySelector(`option[data-provider="${provider}"]`);
    if (first) modelSel.value = first.value;
}

function updateProviderBadge() {
    const badge = document.getElementById("active-provider");
    if (badge) {
        badge.textContent = currentProvider === "anthropic" ? "Anthropic" : "Mistral";
    }
}

function saveSettings() {
    const providerSel = document.getElementById("global-provider");
    if (providerSel) {
        currentProvider = providerSel.value;
        localStorage.setItem("fs-provider", currentProvider);
    }
    // Toggle model groups in modal
    const aGroup = document.getElementById("anthropic-models-group");
    const mGroup = document.getElementById("mistral-models-group");
    if (aGroup && mGroup) {
        aGroup.classList.toggle("d-none", currentProvider !== "anthropic");
        mGroup.classList.toggle("d-none", currentProvider !== "mistral");
    }
    updateProviderBadge();
    // Also update skill page provider if present
    const chatProvider = document.getElementById("chat-provider");
    if (chatProvider) {
        chatProvider.value = currentProvider;
        filterModels(currentProvider);
    }
}

// ── Skill Submission ──

async function submitSkill(skillId) {
    const msgEl = document.getElementById("user-message");
    const message = msgEl ? msgEl.value.trim() : "";
    const fileInput = document.getElementById("file-upload");
    const provider = document.getElementById("chat-provider")?.value || currentProvider;
    const model = document.getElementById("chat-model")?.value || "";

    let fileContent = "";
    if (fileInput && fileInput.files.length > 0) {
        fileContent = await readFileContent(fileInput.files[0]);
    }

    if (!message && !fileContent) {
        alert("Please enter a message or attach a file.");
        return;
    }

    showLoading();

    abortController = new AbortController();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                skill_id: skillId,
                message: message,
                provider: provider,
                model: model || null,
                file_content: fileContent,
            }),
            signal: abortController.signal,
        });

        if (!response.ok) {
            const err = await response.json();
            showError(err.error || "Request failed");
            return;
        }

        showOutput();
        isStreaming = true;
        updateSubmitButton(true);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                    const data = JSON.parse(jsonStr);
                    if (data.error) {
                        showError(data.error);
                        isStreaming = false;
                        updateSubmitButton(false);
                        return;
                    }
                    if (data.done) {
                        isStreaming = false;
                        updateSubmitButton(false);
                        renderMarkdown(fullText);
                        showMeta(provider, model || "(default)");
                        return;
                    }
                    if (data.chunk) {
                        fullText += data.chunk;
                        renderMarkdown(fullText, true);
                    }
                } catch (e) {
                    // skip malformed chunks
                }
            }
        }

        // Stream ended without explicit done
        isStreaming = false;
        updateSubmitButton(false);
        if (fullText) {
            renderMarkdown(fullText);
            showMeta(provider, model || "(default)");
        }
    } catch (err) {
        if (err.name === "AbortError") {
            showMeta(provider, "Cancelled");
        } else {
            showError(err.message);
        }
        isStreaming = false;
        updateSubmitButton(false);
    }
}

// ── File Reading ──

function readFileContent(file) {
    return new Promise((resolve) => {
        if (
            file.type.startsWith("text/") ||
            file.name.endsWith(".csv") ||
            file.name.endsWith(".json") ||
            file.name.endsWith(".md") ||
            file.name.endsWith(".txt")
        ) {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.readAsText(file);
        } else {
            resolve(`[Binary file attached: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]`);
        }
    });
}

// ── UI Helpers ──

function showLoading() {
    hide("output-placeholder");
    hide("output-content");
    hide("output-error");
    hide("output-meta");
    show("output-loading");
}

function showOutput() {
    hide("output-placeholder");
    hide("output-loading");
    hide("output-error");
    show("output-content");
}

function showError(msg) {
    hide("output-placeholder");
    hide("output-loading");
    hide("output-content");
    const el = document.getElementById("output-error");
    if (el) {
        el.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${escapeHtml(msg)}`;
        el.classList.remove("d-none");
    }
}

function showMeta(provider, model) {
    const metaEl = document.getElementById("output-meta");
    const textEl = document.getElementById("output-meta-text");
    if (metaEl && textEl) {
        textEl.textContent = `Provider: ${provider} | Model: ${model}`;
        metaEl.classList.remove("d-none");
    }
}

function renderMarkdown(text, streaming = false) {
    const el = document.getElementById("output-content");
    if (!el) return;
    el.innerHTML = marked.parse(text);
    if (streaming) {
        el.classList.add("streaming-cursor");
    } else {
        el.classList.remove("streaming-cursor");
    }
    // Auto-scroll
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
        btn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Generate';
        btn.onclick = () => submitSkill(skillId);
    }
}

function copyOutput() {
    const el = document.getElementById("output-content");
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        // Brief visual feedback
        const btn = el.closest(".card").querySelector('[onclick="copyOutput()"]');
        if (btn) {
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => (btn.innerHTML = orig), 1500);
        }
    });
}

function clearOutput() {
    hide("output-content");
    hide("output-error");
    hide("output-meta");
    show("output-placeholder");
    const el = document.getElementById("output-content");
    if (el) el.innerHTML = "";
}

function show(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("d-none");
}

function hide(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add("d-none");
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
