// Main JavaScript logic for YTDL WebUI

let currentFormat = "mp3";
let previewDebounceTimer = null;
let currentPreviewUrl = "";

// DOM Elements
const urlInput = document.getElementById("url-input");
const clearUrlBtn = document.getElementById("clear-url-btn");
const pasteBtn = document.getElementById("paste-btn");
const previewThumbnail = document.getElementById("preview-thumbnail");
const previewPlaceholderIcon = document.getElementById("preview-placeholder-icon");
const previewSpinner = document.getElementById("preview-loading-spinner");
const previewTitle = document.getElementById("preview-title");
const previewDetails = document.getElementById("preview-details");
const previewTypeBadge = document.getElementById("preview-type-badge");
const folderInput = document.getElementById("folder-input");
const browseBtn = document.getElementById("browse-btn");
const fmtAudioBtn = document.getElementById("fmt-audio-btn");
const fmtVideoBtn = document.getElementById("fmt-video-btn");
const qualitySelect = document.getElementById("quality-select");
const downloadBtn = document.getElementById("download-btn");
const downloadBtnText = document.getElementById("download-btn-text");
const downloadBtnIcon = document.getElementById("download-btn-icon");
const progressFill = document.getElementById("progress-fill");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const openFolderBtn = document.getElementById("open-folder-btn");
const tabBtnDownloader = document.getElementById("tab-btn-downloader");
const tabBtnHistory = document.getElementById("tab-btn-history");
const viewDownloader = document.getElementById("view-downloader");
const viewHistory = document.getElementById("view-history");
const historyList = document.getElementById("history-list");
const historyBadge = document.getElementById("history-badge");
const clearHistoryBtn = document.getElementById("clear-history-btn");
const ffmpegBanner = document.getElementById("ffmpeg-banner");

// Quality dropdown options
const AUDIO_QUALITIES = [
  "320 kbps (High)",
  "256 kbps",
  "192 kbps (Standard)",
  "128 kbps (Compact)",
];

const VIDEO_QUALITIES = [
  "Best Available",
  "1080p",
  "720p",
  "480p",
  "360p",
];

// Helper: Call Python API with safety check
async function callPy(fnName, ...args) {
  if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[fnName] === "function") {
    return await window.pywebview.api[fnName](...args);
  }
  console.warn(`[YTDL WebUI] pywebview API '${fnName}' not ready.`);
  return null;
}

// 1. Initial State Setup
async function initApp() {
  const state = await callPy("get_initial_state");
  if (state) {
    if (state.default_dir) {
      folderInput.value = state.default_dir;
    }
    if (!state.ffmpeg_installed) {
      ffmpegBanner.classList.remove("hidden");
    }
    renderHistory(state.history || []);
  }
}

window.addEventListener("pywebviewready", initApp);
// Fallback if pywebviewready fired earlier
if (window.pywebview) {
  initApp();
}

// 2. Navigation Tabs
tabBtnDownloader.addEventListener("click", () => {
  tabBtnDownloader.classList.add("active");
  tabBtnHistory.classList.remove("active");
  viewDownloader.classList.remove("hidden");
  viewHistory.classList.add("hidden");
});

tabBtnHistory.addEventListener("click", () => {
  tabBtnHistory.classList.add("active");
  tabBtnDownloader.classList.remove("active");
  viewHistory.classList.remove("hidden");
  viewDownloader.classList.add("hidden");
});

// 3. Format Switching
fmtAudioBtn.addEventListener("click", () => {
  currentFormat = "mp3";
  fmtAudioBtn.className = "fmt-btn flex-1 py-1.5 text-xs font-semibold rounded-lg bg-yt-red text-white shadow transition-all duration-200";
  fmtVideoBtn.className = "fmt-btn flex-1 py-1.5 text-xs font-semibold rounded-lg text-yt-subtext hover:text-white transition-all duration-200";

  qualitySelect.innerHTML = AUDIO_QUALITIES.map(q => `<option value="${q}">${q}</option>`).join("");
});

fmtVideoBtn.addEventListener("click", () => {
  currentFormat = "mp4";
  fmtVideoBtn.className = "fmt-btn flex-1 py-1.5 text-xs font-semibold rounded-lg bg-yt-red text-white shadow transition-all duration-200";
  fmtAudioBtn.className = "fmt-btn flex-1 py-1.5 text-xs font-semibold rounded-lg text-yt-subtext hover:text-white transition-all duration-200";

  qualitySelect.innerHTML = VIDEO_QUALITIES.map(q => `<option value="${q}">${q}</option>`).join("");
});

// 4. URL Input & Debounced Preview
urlInput.addEventListener("input", () => {
  const url = urlInput.value.trim();
  clearUrlBtn.classList.toggle("hidden", !url);

  if (!url) {
    resetPreview();
    return;
  }

  if (previewDebounceTimer) {
    clearTimeout(previewDebounceTimer);
  }
  previewDebounceTimer = setTimeout(() => {
    fetchPreview(url);
  }, 450);
});

clearUrlBtn.addEventListener("click", () => {
  urlInput.value = "";
  clearUrlBtn.classList.add("hidden");
  resetPreview();
});

// Paste Button
pasteBtn.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text && text.trim()) {
      urlInput.value = text.trim();
      clearUrlBtn.classList.remove("hidden");
      fetchPreview(text.trim());
    }
  } catch (err) {
    console.error("Clipboard paste error:", err);
  }
});

async function fetchPreview(url) {
  if (url === currentPreviewUrl) return;
  currentPreviewUrl = url;

  previewSpinner.classList.remove("hidden");
  updateStatus("Loading preview...", "#facc15");

  const preview = await callPy("get_preview", url);
  previewSpinner.classList.add("hidden");

  if (preview && preview.success) {
    previewTitle.innerText = preview.title;
    previewDetails.innerText = preview.details;

    if (preview.thumbnail) {
      previewThumbnail.src = preview.thumbnail;
      previewThumbnail.classList.remove("hidden");
      previewPlaceholderIcon.classList.add("hidden");
    } else {
      previewThumbnail.classList.add("hidden");
      previewPlaceholderIcon.classList.remove("hidden");
    }

    if (preview.is_playlist) {
      previewTypeBadge.innerText = "Playlist";
      previewTypeBadge.className = "text-[10px] bg-red-950/70 text-red-300 border border-red-800/60 px-2 py-0.5 rounded-md font-bold";
      previewTypeBadge.classList.remove("hidden");
    } else {
      previewTypeBadge.innerText = "Video";
      previewTypeBadge.className = "text-[10px] bg-neutral-800 text-yt-subtext border border-neutral-700 px-2 py-0.5 rounded-md font-medium";
      previewTypeBadge.classList.remove("hidden");
    }

    updateStatus("Ready to download", "#4ade80");
  } else {
    resetPreview("Could not load preview", "Please check the URL");
    updateStatus("Ready", "#aaaaaa");
  }
}

function resetPreview(title = "No video loaded", details = "Paste a YouTube link above to preview") {
  currentPreviewUrl = "";
  previewTitle.innerText = title;
  previewDetails.innerText = details;
  previewThumbnail.classList.add("hidden");
  previewThumbnail.src = "";
  previewPlaceholderIcon.classList.remove("hidden");
  previewTypeBadge.classList.add("hidden");
}

// 5. Save Destination Browse
browseBtn.addEventListener("click", async () => {
  const selected = await callPy("select_folder");
  if (selected) {
    folderInput.value = selected;
  }
});

// 6. Download Trigger
downloadBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  const folder = folderInput.value.trim();
  const quality = qualitySelect.value;

  if (!url) {
    updateStatus("Please enter a valid URL.", "#f87171");
    return;
  }
  if (!folder) {
    updateStatus("Please choose a destination folder.", "#f87171");
    return;
  }

  // Set downloading UI state
  setInputsEnabled(false);
  progressFill.style.width = "0%";
  openFolderBtn.classList.add("hidden");
  downloadBtn.classList.add("downloading-pulse");
  downloadBtnIcon.innerText = "⏳";
  downloadBtnText.innerText = "Downloading...";
  updateStatus("Starting download...", "#facc15");

  const res = await callPy("start_download", url, currentFormat, quality, folder);
  if (res && !res.success) {
    updateStatus(res.error || "Download failed to start.", "#f87171");
    setInputsEnabled(true);
    resetDownloadBtn();
  }
});

// 7. Event Handler for Python Push Events
window.onAppEvent = function(eventType, payload) {
  if (eventType === "progress") {
    const percent = payload.percent || 0;
    progressFill.style.width = `${percent}%`;

    const parts = [];
    if (payload.item_index && payload.item_total) {
      parts.push(`Item ${payload.item_index}/${payload.item_total} (${percent}%)`);
    } else {
      parts.push(`Downloading: ${percent}%`);
    }

    if (payload.speed) parts.push(payload.speed);
    if (payload.eta) parts.push(`ETA ${payload.eta}`);

    updateStatus(parts.join(" • "), "#facc15");
  } else if (eventType === "processing") {
    progressFill.style.width = "100%";
    updateStatus(payload.message || "Processing...", "#facc15");
  } else if (eventType === "success") {
    progressFill.style.width = "100%";
    updateStatus(`✔ Done! Saved to ${payload.dir}`, "#4ade80");
    openFolderBtn.classList.remove("hidden");
    resetDownloadBtn();
    setInputsEnabled(true);
    urlInput.value = "";
    clearUrlBtn.classList.add("hidden");
    resetPreview();
    if (payload.history) {
      renderHistory(payload.history);
    }
  } else if (eventType === "error") {
    updateStatus(`✖ Error: ${payload.error}`, "#f87171");
    resetDownloadBtn();
    setInputsEnabled(true);
  }
};

function resetDownloadBtn() {
  downloadBtn.classList.remove("downloading-pulse");
  downloadBtnIcon.innerText = "⚡";
  downloadBtnText.innerText = "Download Now";
}

function setInputsEnabled(enabled) {
  downloadBtn.disabled = !enabled;
  urlInput.disabled = !enabled;
  pasteBtn.disabled = !enabled;
  browseBtn.disabled = !enabled;
  fmtAudioBtn.disabled = !enabled;
  fmtVideoBtn.disabled = !enabled;
  qualitySelect.disabled = !enabled;
}

function updateStatus(text, color = "#aaaaaa") {
  statusText.innerText = text;
  statusDot.style.backgroundColor = color;
}

// 8. Open Folder Actions
openFolderBtn.addEventListener("click", () => {
  callPy("open_last_download");
});

// 9. History Rendering
function renderHistory(items) {
  if (items && items.length > 0) {
    historyBadge.innerText = items.length;
    historyBadge.classList.remove("hidden");

    historyList.innerHTML = items.map((item, idx) => `
      <div class="bg-yt-input border border-yt-cardBorder rounded-xl p-3 flex items-center justify-between gap-3 hover:border-neutral-700 transition-all duration-200">
        <div class="min-w-0 flex-1">
          <p class="text-xs font-bold text-white truncate">${escapeHtml(item.title || "Unknown File")}</p>
          <p class="text-[11px] text-yt-muted mt-0.5 truncate">${escapeHtml(item.format || "")} • ${item.timestamp || ""}</p>
        </div>
        <button onclick="openHistoryFile(${idx})" class="bg-yt-secondary hover:bg-yt-secondaryHover active:scale-95 text-white border border-yt-cardBorder px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 flex-shrink-0">
          <span>📂</span> Open
        </button>
      </div>
    `).join("");

    // Cache current history items globally for the click handler
    window.__currentHistoryItems = items;
  } else {
    historyBadge.classList.add("hidden");
    historyList.innerHTML = `
      <div class="text-center py-12 text-yt-muted text-xs">
        No downloads recorded yet.
      </div>
    `;
    window.__currentHistoryItems = [];
  }
}

window.openHistoryFile = function(idx) {
  const item = (window.__currentHistoryItems || [])[idx];
  if (item && item.path) {
    callPy("open_path", item.path);
  }
};

clearHistoryBtn.addEventListener("click", async () => {
  await callPy("clear_history");
  renderHistory([]);
});

function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
