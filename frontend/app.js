const form = document.querySelector("#shorten-form");
const input = document.querySelector("#long-url");
const submitButton = document.querySelector("#shorten-button");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const shortLink = document.querySelector("#short-link");
const copyButton = document.querySelector("#copy-button");
const historyList = document.querySelector("#history-list");
const historyEmpty = document.querySelector("#history-empty");
const clearHistoryButton = document.querySelector("#clear-history");

const HISTORY_KEY = "url-shortener-history";
const API_BASE = (window.API_BASE_URL || "").replace(/\/+$/, "");
const aliasInput = document.querySelector("#custom-alias");

function readHistory() {
  try {
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function writeHistory(entries) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, 20)));
}

function renderHistory() {
  const entries = readHistory();
  historyList.replaceChildren();
  historyEmpty.hidden = entries.length > 0;
  clearHistoryButton.hidden = entries.length === 0;

  for (const entry of entries) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = entry.short_url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = entry.short_url;
    const original = document.createElement("span");
    original.textContent = entry.long_url;
    item.append(link, original);
    historyList.append(item);
  }
}

function setStatus(message, isError) {
  status.textContent = message;
  status.classList.toggle("error", Boolean(isError));
}

function showResult(shortUrl) {
  shortLink.href = shortUrl;
  shortLink.textContent = shortUrl;
  result.hidden = false;
  copyButton.textContent = "Copy";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const longUrl = input.value.trim();
  if (!longUrl) {
    setStatus("Enter a URL to shorten.", true);
    return;
  }

  submitButton.disabled = true;
  setStatus("Shortening…");

  try {
    const response = await fetch(`${API_BASE}/shorten`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: longUrl, custom_alias: aliasInput.value.trim() }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      setStatus(data.error || "The shortener could not save that URL.", true);
      return;
    }

    showResult(data.short_url);
    aliasInput.value = "";
    setStatus("Short link ready.");
    writeHistory([{ long_url: longUrl, short_url: data.short_url }, ...readHistory()]);
    renderHistory();
  } catch {
    setStatus("Could not reach the shortener API.", true);
  } finally {
    submitButton.disabled = false;
  }
});

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(shortLink.href);
    copyButton.textContent = "Copied";
  } catch {
    setStatus("Copy was blocked by the browser.", true);
  }
});

clearHistoryButton.addEventListener("click", () => {
  localStorage.removeItem(HISTORY_KEY);
  result.hidden = true;
  setStatus("");
  renderHistory();
});

renderHistory();
