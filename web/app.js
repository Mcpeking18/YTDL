// Interactive Frontend Logic for YTDL Live Server

let currentFormat = "mp3";
let previewDebounceTimer = null;
let currentPreviewUrl = "";
let progressPollInterval = null;

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
const folderPresetsContainer = document.getElementById("folder-presets-container");
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
const updateYtdlpBtn = document.getElementById("update-ytdlp-btn");
const ytdlpVersionLabel = document.getElementById("ytdlp-version-label");
const updateSpinIcon = document.getElementById("update-spin-icon");

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

// 1. Initial State Setup
async function initApp() {
  try {
    const res = await fetch("/api/state");
    if (!res.ok) return;
    const state = await res.json();

    if (state.default_dir) {
      folderInput.value = state.default_dir;
    }
    if (state.ytdlp_version && ytdlpVersionLabel) {
      ytdlpVersionLabel.innerText = `yt-dlp v${state.ytdlp_version}`;
    }
    if (!state.ffmpeg_installed) {
      ffmpegBanner.classList.remove("hidden");
    }

    // Render presets chips
    if (state.presets && state.presets.length > 0) {
      folderPresetsContainer.innerHTML = state.presets.map(p => `
        <button type="button" class="preset-chip bg-yt-secondary hover:bg-yt-secondaryHover active:scale-95 text-yt-subtext hover:text-white border border-yt-cardBorder text-[10px] px-2 py-1 rounded-md transition-all duration-200" data-path="${escapeHtml(p.path)}">
          ${escapeHtml(p.label)}
        </button>
      `).join("");

      document.querySelectorAll(".preset-chip").forEach(chip => {
        chip.addEventListener("click", () => {
          folderInput.value = chip.getAttribute("data-path");
        });
      });
    }

    renderHistory(state.history || []);
  } catch (err) {
    console.error("Failed to connect to backend server:", err);
    updateStatus("Connecting to local server...", "#facc15");
  }
}

document.addEventListener("DOMContentLoaded", initApp);

// 1.1 One-Click uv Update yt-dlp
if (updateYtdlpBtn) {
  updateYtdlpBtn.addEventListener("click", async () => {
    updateYtdlpBtn.disabled = true;
    updateSpinIcon.classList.add("animate-spin");
    ytdlpVersionLabel.innerText = "Checking via uv...";

    try {
      const res = await fetch("/api/update-ytdlp", { method: "POST" });
      const data = await res.json();
      updateSpinIcon.classList.remove("animate-spin");

      if (data.success) {
        ytdlpVersionLabel.innerText = data.updated ? `v${data.version} (Updated!)` : `v${data.version} (Latest)`;
        setTimeout(() => {
          ytdlpVersionLabel.innerText = `yt-dlp v${data.version}`;
          updateYtdlpBtn.disabled = false;
        }, 3000);
      } else {
        ytdlpVersionLabel.innerText = "Update error";
        console.error(data.error);
        setTimeout(() => {
          ytdlpVersionLabel.innerText = "yt-dlp";
          updateYtdlpBtn.disabled = false;
        }, 3000);
      }
    } catch (err) {
      updateSpinIcon.classList.remove("animate-spin");
      ytdlpVersionLabel.innerText = "Network error";
      console.error(err);
      setTimeout(() => {
        ytdlpVersionLabel.innerText = "yt-dlp";
        updateYtdlpBtn.disabled = false;
      }, 3000);
    }
  });
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
  refreshHistory();
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

// Helper: Extract YouTube 11-char ID instantly in JS
function extractYoutubeId(url) {
  const match = url.match(/(?:v=|\/vi\/|youtu\.be\/|\/shorts\/|embed\/)([0-9A-Za-z_-]{11})/);
  return match ? match[1] : null;
}

// 4. URL Input & Preview
urlInput.addEventListener("input", () => {
  const url = urlInput.value.trim();
  clearUrlBtn.classList.toggle("hidden", !url);

  if (!url) {
    resetPreview();
    return;
  }

  // Instant thumbnail preview from video ID (0ms latency!)
  const videoId = extractYoutubeId(url);
  if (videoId) {
    previewThumbnail.src = `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
    previewThumbnail.classList.remove("hidden");
    previewPlaceholderIcon.classList.add("hidden");
  }

  if (previewDebounceTimer) {
    clearTimeout(previewDebounceTimer);
  }
  previewDebounceTimer = setTimeout(() => {
    fetchPreview(url);
  }, 400);
});

clearUrlBtn.addEventListener("click", () => {
  urlInput.value = "";
  clearUrlBtn.classList.add("hidden");
  resetPreview();
});

pasteBtn.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text && text.trim()) {
      urlInput.value = text.trim();
      clearUrlBtn.classList.remove("hidden");
      
      const videoId = extractYoutubeId(text.trim());
      if (videoId) {
        previewThumbnail.src = `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
        previewThumbnail.classList.remove("hidden");
        previewPlaceholderIcon.classList.add("hidden");
      }
      
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

  try {
    const res = await fetch(`/api/preview?url=${encodeURIComponent(url)}`);
    const preview = await res.json();
    previewSpinner.classList.add("hidden");

    if (preview && preview.success) {
      previewTitle.innerText = preview.title;
      previewDetails.innerText = preview.details;

      if (preview.thumbnail) {
        previewThumbnail.src = preview.thumbnail;
        previewThumbnail.classList.remove("hidden");
        previewPlaceholderIcon.classList.add("hidden");
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
      updateStatus("Ready", "#aaaaaa");
    }
  } catch (err) {
    previewSpinner.classList.add("hidden");
    console.error("Preview error:", err);
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

// 5. Native Browse Button
browseBtn.addEventListener("click", async () => {
  browseBtn.innerText = "Opening...";
  browseBtn.disabled = true;
  try {
    const res = await fetch(`/api/browse?initial_dir=${encodeURIComponent(folderInput.value)}`, {
      method: "POST"
    });
    const data = await res.json();
    if (data.selected) {
      folderInput.value = data.selected;
    }
  } catch (err) {
    console.error("Browse folder error:", err);
  } finally {
    browseBtn.innerHTML = `<span>📁</span> Browse`;
    browseBtn.disabled = false;
  }
});

// 6. Download Trigger & Progress Poller
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

  setInputsEnabled(false);
  progressFill.style.width = "0%";
  openFolderBtn.classList.add("hidden");
  downloadBtn.classList.add("downloading-pulse");
  downloadBtnIcon.innerText = "⏳";
  downloadBtnText.innerText = "Downloading...";
  updateStatus("Starting download...", "#facc15");

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: url,
        format: currentFormat,
        quality: quality,
        destination: folder,
      }),
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      updateStatus(data.error || "Download failed to start.", "#f87171");
      setInputsEnabled(true);
      resetDownloadBtn();
      return;
    }

    startProgressPolling();
  } catch (err) {
    updateStatus("Network error starting download.", "#f87171");
    setInputsEnabled(true);
    resetDownloadBtn();
  }
});

function startProgressPolling() {
  if (progressPollInterval) clearInterval(progressPollInterval);

  progressPollInterval = setInterval(async () => {
    try {
      const res = await fetch("/api/progress");
      if (!res.ok) return;
      const data = await res.json();

      if (data.state === "downloading") {
        const percent = data.percent || 0;
        progressFill.style.width = `${percent}%`;

        const parts = [];
        if (data.item_index && data.item_total) {
          parts.push(`Item ${data.item_index}/${data.item_total} (${percent}%)`);
        } else {
          parts.push(`Downloading: ${percent}%`);
        }

        if (data.speed) parts.push(data.speed);
        if (data.eta) parts.push(`ETA ${data.eta}`);

        updateStatus(parts.join(" • "), "#facc15");
      } else if (data.state === "processing") {
        progressFill.style.width = "100%";
        updateStatus(data.message || "Processing media & cover art...", "#facc15");
      } else if (data.state === "success") {
        clearInterval(progressPollInterval);
        progressFill.style.width = "100%";
        updateStatus(`✔ Done! Saved to ${data.last_dir || "folder"}`, "#4ade80");
        openFolderBtn.classList.remove("hidden");
        resetDownloadBtn();
        setInputsEnabled(true);
        urlInput.value = "";
        clearUrlBtn.classList.add("hidden");
        resetPreview();
        refreshHistory();
      } else if (data.state === "error") {
        clearInterval(progressPollInterval);
        updateStatus(`✖ Error: ${data.error || data.message}`, "#f87171");
        resetDownloadBtn();
        setInputsEnabled(true);
      }
    } catch (err) {
      console.error("Progress polling error:", err);
    }
  }, 350);
}

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
  folderInput.disabled = !enabled;
  fmtAudioBtn.disabled = !enabled;
  fmtVideoBtn.disabled = !enabled;
  qualitySelect.disabled = !enabled;
}

function updateStatus(text, color = "#aaaaaa") {
  statusText.innerText = text;
  statusDot.style.backgroundColor = color;
}

// 7. Open Folder Action
openFolderBtn.addEventListener("click", async () => {
  try {
    await fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch (err) {
    console.error("Failed to open folder:", err);
  }
});

// 8. History Handling
async function refreshHistory() {
  try {
    const res = await fetch("/api/history");
    if (!res.ok) return;
    const history = await res.json();
    renderHistory(history);
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

function renderHistory(items) {
  if (items && items.length > 0) {
    historyBadge.innerText = items.length;
    historyBadge.classList.remove("hidden");

    historyList.innerHTML = items.map(item => `
      <div class="bg-yt-input border border-yt-cardBorder rounded-xl p-3 flex items-center justify-between gap-3 hover:border-neutral-700 transition-all duration-200">
        <div class="min-w-0 flex-1">
          <p class="text-xs font-bold text-white truncate">${escapeHtml(item.title || "Unknown File")}</p>
          <p class="text-[11px] text-yt-muted mt-0.5 truncate">${escapeHtml(item.format || "")} • ${item.timestamp || ""}</p>
        </div>
        <button onclick="openHistoryFile('${escapeAttr(item.path || '')}')" class="bg-yt-secondary hover:bg-yt-secondaryHover active:scale-95 text-white border border-yt-cardBorder px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 flex-shrink-0">
          <span>📂</span> Open
        </button>
      </div>
    `).join("");
  } else {
    historyBadge.classList.add("hidden");
    historyList.innerHTML = `
      <div class="text-center py-12 text-yt-muted text-xs">
        No downloads recorded yet.
      </div>
    `;
  }
}

window.openHistoryFile = async function(pathStr) {
  if (!pathStr) return;
  try {
    await fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pathStr }),
    });
  } catch (err) {
    console.error("Failed to open file:", err);
  }
};

clearHistoryBtn.addEventListener("click", async () => {
  try {
    await fetch("/api/history", { method: "DELETE" });
    renderHistory([]);
  } catch (err) {
    console.error("Failed to clear history:", err);
  }
});

function escapeHtml(str) {
  return String(str).replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

function escapeAttr(str) {
  return String(str).replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
