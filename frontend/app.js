(() => {
  const state = {
    activeTab: "dashboard",
    autoRefreshLogs: true,
    logLevel: "",
    clientLogs: [],
    logTimer: null,
  };

  const dom = {
    statusEl: document.getElementById("status-text"),
    statusTimeEl: document.getElementById("status-time"),
    schedulerChip: document.getElementById("scheduler-chip"),
    profileForm: document.getElementById("profile-form"),
    cvFile: document.getElementById("cv-file"),
    cvStatus: document.getElementById("cv-status"),
    profileSummary: document.getElementById("profile-summary"),
    companiesList: document.getElementById("companies-list"),
    jobsRows: document.getElementById("jobs-rows"),
    jobsCountChip: document.getElementById("jobs-count-chip"),
    filteredJobsRows: document.getElementById("filtered-jobs-rows"),
    filteredJobsCountChip: document.getElementById("filtered-jobs-count-chip"),
    filteredJobsNote: document.getElementById("filtered-jobs-note"),
    matchesList: document.getElementById("matches-list"),
    dbSummary: document.getElementById("db-summary"),
    dbView: document.getElementById("db-view"),
    bulkCompanies: document.getElementById("bulk-companies"),
    logsList: document.getElementById("logs-list"),
    logsCountChip: document.getElementById("logs-count-chip"),
    logsPath: document.getElementById("logs-path"),
    logsLevel: document.getElementById("logs-level"),
    btnToggleLogPoll: document.getElementById("btn-toggle-log-poll"),
    tabButtons: document.querySelectorAll(".tab-btn"),
    panels: document.querySelectorAll(".tab-panel"),
    btnSaveProfile: document.getElementById("btn-save-profile"),
    btnUploadCv: document.getElementById("btn-upload-cv"),
    btnRunSearch: document.getElementById("btn-run-search"),
    btnSendReport: document.getElementById("btn-send-report"),
    btnDiscoverSites: document.getElementById("btn-discover-sites"),
    btnRefreshCompanies: document.getElementById("btn-refresh-companies"),
    btnRefreshJobs: document.getElementById("btn-refresh-jobs"),
    btnRefreshMatches: document.getElementById("btn-refresh-matches"),
    btnBulkAdd: document.getElementById("btn-bulk-add"),
    btnRefreshDb: document.getElementById("btn-refresh-db"),
    btnRefreshLogs: document.getElementById("btn-refresh-logs"),
  };

  const toList = (value) =>
    value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  const timestampNow = () => new Date().toISOString().slice(0, 19).replace("T", " ");

  const formatList = (items) => (items && items.length ? items.map(escapeHtml).join(", ") : "None");

  const formatDate = (value) => {
    if (!value) return "Not set";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  };

  const pushClientLog = (level, logger, message) => {
    state.clientLogs.push({
      timestamp: timestampNow(),
      level: level.toUpperCase(),
      logger,
      message,
      source: "ui",
    });
    state.clientLogs = state.clientLogs.slice(-200);
    if (state.activeTab === "logs") {
      renderLogs();
    }
  };

  const setStatus = (message, tone = "info") => {
    dom.statusEl.textContent = message;
    dom.statusEl.dataset.tone = tone;
    dom.statusTimeEl.textContent = new Date().toLocaleTimeString();
  };

  const setButtonBusy = (button, busy, labelWhenBusy) => {
    if (!button) return;
    if (!button.dataset.defaultLabel) {
      button.dataset.defaultLabel = button.textContent;
    }
    button.disabled = busy;
    button.textContent = busy ? labelWhenBusy : button.dataset.defaultLabel;
  };

  const ensureFilteredJobsPanel = () => {
    if (dom.filteredJobsRows && dom.filteredJobsCountChip && dom.filteredJobsNote) {
      return true;
    }

    const dashboard = document.querySelector('[data-panel="dashboard"]');
    const matchesPanel = dom.matchesList ? dom.matchesList.closest(".card") : null;
    if (!dashboard) {
      return false;
    }

    const panel = document.createElement("section");
    panel.className = "card span-2";
    panel.innerHTML = `
      <div class="card-head">
        <h2>Filtered Out Jobs</h2>
        <span class="chip" id="filtered-jobs-count-chip">0 filtered</span>
      </div>
      <p class="muted filter-note" id="filtered-jobs-note">Filtered after discovery by seniority keywords and clear experience requirements.</p>
      <div class="table">
        <div class="table-head filtered-table-head">
          <span>Title</span>
          <span>Company</span>
          <span>Reason</span>
          <span>Apply</span>
        </div>
        <div id="filtered-jobs-rows"></div>
      </div>
    `;
    dashboard.insertBefore(panel, matchesPanel || null);
    dom.filteredJobsRows = document.getElementById("filtered-jobs-rows");
    dom.filteredJobsCountChip = document.getElementById("filtered-jobs-count-chip");
    dom.filteredJobsNote = document.getElementById("filtered-jobs-note");
    return Boolean(dom.filteredJobsRows && dom.filteredJobsCountChip && dom.filteredJobsNote);
  };

  const api = async (path, { method = "GET", body, headers = {}, isForm = false } = {}) => {
    const options = { method, headers: { ...headers } };
    if (body) {
      if (isForm) {
        options.body = body;
      } else {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
      }
    }

    try {
      const response = await fetch(path, options);
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json") ? await response.json() : await response.text();

      if (!response.ok) {
        const detail = typeof payload === "string" ? payload : JSON.stringify(payload);
        throw new Error(`${response.status} ${response.statusText}: ${detail}`);
      }

      pushClientLog("INFO", "ui.api", `${method} ${path} -> ${response.status}`);
      return payload;
    } catch (error) {
      pushClientLog("ERROR", "ui.api", `${method} ${path} failed: ${error.message}`);
      throw error;
    }
  };

  const switchTab = (tab) => {
    state.activeTab = tab;
    dom.tabButtons.forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
    dom.panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === tab));
    if (tab === "admin") {
      loadDbOverview(true).catch((error) => setStatus(error.message, "warn"));
    }
    if (tab === "logs") {
      loadLogs().catch((error) => setStatus(error.message, "warn"));
    }
    updateLogPolling();
  };

  const updateLogPolling = () => {
    if (state.logTimer) {
      clearInterval(state.logTimer);
      state.logTimer = null;
    }
    dom.btnToggleLogPoll.textContent = `Auto Refresh: ${state.autoRefreshLogs ? "On" : "Off"}`;
    if (!state.autoRefreshLogs) {
      return;
    }
    state.logTimer = window.setInterval(() => {
      if (state.activeTab === "logs") {
        loadLogs(true).catch(() => {});
      }
    }, 4000);
  };

  const loadHealth = async () => {
    const data = await api("/health");
    dom.schedulerChip.textContent = `Scheduler: ${data.scheduler_enabled ? "ON" : "OFF"}`;
  };

  const hydrateProfileForm = (profile) => {
    if (!profile) return;

    const setValue = (name, value) => {
      const field = dom.profileForm.elements[name];
      if (field) {
        field.value = value ?? "";
      }
    };

    setValue("target_roles", (profile.target_roles || []).join(", "));
    setValue("skills", (profile.skills || []).join(", "));
    setValue("preferred_locations", (profile.preferred_locations || []).join(", "));
    setValue("remote_preference", profile.remote_preference || "hybrid");
    setValue("salary_min", profile.salary_min ?? "");
    setValue("salary_max", profile.salary_max ?? "");
    setValue("experience_years", profile.experience_years ?? "");
    setValue("notice_period_days", profile.notice_period_days ?? "");
    setValue("job_level", profile.job_level ?? "");

    dom.profileSummary.textContent = profile.profile_summary || "Parsed CV summary will appear here.";
    dom.cvStatus.textContent = profile.cv_path ? `Stored: ${profile.cv_path}` : "No upload yet.";
  };

  const loadProfile = async (silent = false) => {
    const profile = await api("/profile");
    if (profile) {
      hydrateProfileForm(profile);
    }
    if (!silent) {
      setStatus(profile ? "Profile loaded" : "No profile found yet");
    }
  };

  const saveProfile = async () => {
    const payload = {
      target_roles: toList(dom.profileForm.elements["target_roles"].value),
      skills: toList(dom.profileForm.elements["skills"].value),
      preferred_locations: toList(dom.profileForm.elements["preferred_locations"].value),
      remote_preference: dom.profileForm.elements["remote_preference"].value || "hybrid",
      salary_min: dom.profileForm.elements["salary_min"].value ? Number(dom.profileForm.elements["salary_min"].value) : null,
      salary_max: dom.profileForm.elements["salary_max"].value ? Number(dom.profileForm.elements["salary_max"].value) : null,
      experience_years: dom.profileForm.elements["experience_years"].value
        ? Number(dom.profileForm.elements["experience_years"].value)
        : null,
      notice_period_days: dom.profileForm.elements["notice_period_days"].value
        ? Number(dom.profileForm.elements["notice_period_days"].value)
        : null,
      job_level: dom.profileForm.elements["job_level"].value || null,
    };

    setButtonBusy(dom.btnSaveProfile, true, "Saving...");
    pushClientLog("INFO", "ui.profile", "Saving profile");
    try {
      const profile = await api("/profile", { method: "POST", body: payload });
      hydrateProfileForm(profile);
      await loadDbOverview(true);
      setStatus("Profile saved");
    } finally {
      setButtonBusy(dom.btnSaveProfile, false, "Saving...");
    }
  };

  const uploadCv = async () => {
    if (!dom.cvFile.files.length) {
      setStatus("Pick a file first", "warn");
      pushClientLog("WARNING", "ui.upload", "Upload blocked: no file selected");
      return;
    }

    const file = dom.cvFile.files[0];
    const formData = new FormData();
    formData.append("file", file);

    setButtonBusy(dom.btnUploadCv, true, "Uploading...");
    dom.cvStatus.textContent = `Uploading ${file.name}...`;
    pushClientLog("INFO", "ui.upload", `Uploading CV ${file.name} (${file.size} bytes)`);

    try {
      const updated = await api("/profile/upload-cv", { method: "POST", body: formData, isForm: true });
      hydrateProfileForm(updated);
      await loadProfile(true);
      await loadDbOverview(true);
      setStatus("CV uploaded and parsed");
      pushClientLog("INFO", "ui.upload", `Upload complete for ${file.name}`);
    } finally {
      setButtonBusy(dom.btnUploadCv, false, "Uploading...");
    }
  };

  const parseCompanyLines = (text) =>
    text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split("|").map((part) => part.trim()).filter(Boolean);
        if (parts.length === 1) {
          return {
            name: parts[0],
            priority: 9,
            career_url: null,
            enabled: true,
          };
        }
        return {
          name: parts[0],
          priority: parts[1] ? Number(parts[1]) || 5 : 5,
          career_url: parts[2] || null,
          enabled: true,
        };
      })
      .filter((company) => company.name);

  const loadCompanies = async (silent = true) => {
    const companies = await api("/companies");
    dom.companiesList.innerHTML = "";

    if (!companies.length) {
      dom.companiesList.innerHTML = `<li class="muted">No companies loaded yet.</li>`;
      return;
    }

    companies.forEach((company) => {
      const item = document.createElement("li");
      item.innerHTML = `
        <div>
          <strong>${escapeHtml(company.name)}</strong>
          <div class="muted">Priority ${escapeHtml(company.priority)}${company.career_url ? ` - ${escapeHtml(company.career_url)}` : ""}</div>
        </div>
        <span class="badge ${company.enabled ? "green" : "red"}">${company.enabled ? "Enabled" : "Disabled"}</span>
      `;
      dom.companiesList.appendChild(item);
    });

    if (!silent) {
      setStatus(`Loaded ${companies.length} companies`);
    }
  };

  const bulkAddCompanies = async () => {
    const companies = parseCompanyLines(dom.bulkCompanies.value);
    if (!companies.length) {
      setStatus("No companies to add", "warn");
      return;
    }

    setButtonBusy(dom.btnBulkAdd, true, "Adding...");
    pushClientLog("INFO", "ui.company", `Bulk adding ${companies.length} companies`);

    try {
      for (const company of companies) {
        await api("/companies", { method: "POST", body: company });
      }
      dom.bulkCompanies.value = "";
      await loadCompanies(false);
      await loadDbOverview(true);
      setStatus(`Added or updated ${companies.length} companies`);
    } finally {
      setButtonBusy(dom.btnBulkAdd, false, "Adding...");
    }
  };

  const discoverSites = async () => {
    pushClientLog("INFO", "ui.company", "Discovering missing career URLs");
    const result = await api("/companies/discover-career-sites", { method: "POST" });
    setStatus(`Missing career URLs: ${result.missing_career_urls}`);
    await loadCompanies(true);
    await loadDbOverview(true);
  };

  const runSearch = async () => {
    setButtonBusy(dom.btnRunSearch, true, "Running...");
    pushClientLog("INFO", "ui.search", "Running search cycle");
    try {
      const result = await api("/search/run", { method: "POST" });
      const emailText = result.email_report?.sent ? " Email sent." : "";
      setStatus(
        `Search complete: ${result.jobs_inserted} jobs inserted from ${result.companies_processed} companies.${emailText}`
      );
      await loadJobs();
      await loadFilteredJobs();
      await loadMatches();
      await loadDbOverview(true);
    } finally {
      setButtonBusy(dom.btnRunSearch, false, "Running...");
    }
  };

  const sendReport = async () => {
    setButtonBusy(dom.btnSendReport, true, "Sending...");
    pushClientLog("INFO", "ui.email", "Sending top jobs email report");
    try {
      const result = await api("/jobs/report/email", { method: "POST" });
      setStatus(result.sent ? `Email sent to ${result.to}` : `Email skipped: ${result.reason}`, result.sent ? "info" : "warn");
    } finally {
      setButtonBusy(dom.btnSendReport, false, "Sending...");
    }
  };

  const loadJobs = async () => {
    const jobs = await api("/jobs");
    dom.jobsRows.innerHTML = "";
    dom.jobsCountChip.textContent = `${jobs.length} visible`;

    if (!jobs.length) {
      dom.jobsRows.innerHTML = `<div class="table-row"><span class="muted">No jobs yet</span><span></span><span></span></div>`;
      return;
    }

    jobs.forEach((job) => {
      const row = document.createElement("div");
      row.className = "table-row";
      row.innerHTML = `
        <span>${escapeHtml(job.title)}</span>
        <span>${escapeHtml(job.company || "Unknown")}</span>
        <span><a href="${escapeHtml(job.apply_url)}" target="_blank" rel="noreferrer">Open</a></span>
      `;
      dom.jobsRows.appendChild(row);
    });
  };

  const loadFilteredJobs = async () => {
    if (!ensureFilteredJobsPanel()) {
      pushClientLog("WARNING", "ui.jobs", "Filtered jobs panel is not available in the current page");
      return;
    }

    const result = await api("/jobs/filtered-out");
    const jobs = result.jobs || [];
    const keywords = result.keywords || [];
    const profileExperience = result.profile_experience_years;
    dom.filteredJobsRows.innerHTML = "";
    dom.filteredJobsCountChip.textContent = `${jobs.length} filtered`;
    dom.filteredJobsNote.textContent = `Filtered after discovery when the title contains ${keywords.join(", ") || "none"} or when a clear minimum experience requirement is above profile experience${profileExperience == null ? "" : ` (${profileExperience} years)`}.`;

    if (!jobs.length) {
      dom.filteredJobsRows.innerHTML = `
        <div class="table-row filtered-table-row">
          <span class="muted">No filtered jobs</span><span></span><span></span><span></span>
        </div>
      `;
      return;
    }

    jobs.forEach((job) => {
      const row = document.createElement("div");
      row.className = "table-row filtered-table-row";
      row.innerHTML = `
        <span>${escapeHtml(job.title)}</span>
        <span>${escapeHtml(job.company || "Unknown")}</span>
        <span><span class="badge orange">${escapeHtml(job.filtered_reason || "Filtered")}</span></span>
        <span><a href="${escapeHtml(job.apply_url)}" target="_blank" rel="noreferrer">Open</a></span>
      `;
      dom.filteredJobsRows.appendChild(row);
    });
  };

  const loadMatches = async () => {
    const matches = await api("/jobs/matches");
    dom.matchesList.innerHTML = "";

    if (!matches.length) {
      dom.matchesList.innerHTML = `<div class="muted">Run a search and build a profile before ranking matches.</div>`;
      return;
    }

    matches.forEach((match) => {
      const card = document.createElement("div");
      card.className = "match-card";
      card.innerHTML = `
        <div class="fit">${escapeHtml(match.company)}</div>
        <div class="score">${Number(match.score).toFixed(1)}</div>
        <div class="badge ${match.fit_level === "high" ? "green" : match.fit_level === "low" ? "red" : ""}">${escapeHtml(match.fit_level)}</div>
        <p class="muted">${escapeHtml(match.reason || "")}</p>
      `;
      dom.matchesList.appendChild(card);
    });
  };

  const sectionHtml = (title, content) => `
    <section class="db-section">
      <h3>${escapeHtml(title)}</h3>
      ${content}
    </section>
  `;

  const renderDbOverview = (data) => {
    const counts = data.counts || {};
    const stats = [
      ["Profiles", counts.profiles || 0],
      ["Companies", counts.companies || 0],
      ["Enabled", counts.enabled_companies || 0],
      ["Jobs", counts.jobs || 0],
      ["Visible Jobs", counts.visible_jobs || 0],
      ["Filtered Jobs", counts.filtered_jobs || 0],
      ["Matches", counts.matches || 0],
    ];

    dom.dbSummary.innerHTML = stats
      .map(([label, value]) => `<div class="stat"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
      .join("");

    const profile = data.profile
      ? `
        <div class="details-grid">
          <div><span>Target roles</span><strong>${formatList(data.profile.target_roles)}</strong></div>
          <div><span>Skills</span><strong>${formatList(data.profile.skills)}</strong></div>
          <div><span>Locations</span><strong>${formatList(data.profile.preferred_locations)}</strong></div>
          <div><span>Remote</span><strong>${escapeHtml(data.profile.remote_preference || "Not set")}</strong></div>
          <div><span>Experience</span><strong>${escapeHtml(data.profile.experience_years ?? "Not set")}</strong></div>
          <div><span>Notice</span><strong>${escapeHtml(data.profile.notice_period_days ?? "Not set")}</strong></div>
          <div><span>Level</span><strong>${escapeHtml(data.profile.job_level || "Not set")}</strong></div>
          <div><span>CV</span><strong>${escapeHtml(data.profile.cv_path || "Not uploaded")}</strong></div>
          <div class="wide"><span>Updated</span><strong>${escapeHtml(formatDate(data.profile.updated_at))}</strong></div>
          <div class="wide"><span>Summary</span><p class="muted">${escapeHtml(data.profile.profile_summary || "No parsed summary yet.")}</p></div>
        </div>
      `
      : `<p class="muted">No profile stored yet.</p>`;

    const companies = (data.companies || [])
      .slice(0, 25)
      .map(
        (company) => `
          <div class="mini-row">
            <div>
              <strong>${escapeHtml(company.name)}</strong>
              <p class="muted">${escapeHtml(company.career_url || "No career URL")}</p>
            </div>
            <span class="badge ${company.enabled ? "green" : "red"}">P${escapeHtml(company.priority)}</span>
          </div>
        `
      )
      .join("");

    const jobs = (data.jobs || [])
      .slice(0, 20)
      .map(
        (job) => `
          <div class="mini-row">
            <div>
              <strong>${escapeHtml(job.title)}</strong>
              <p class="muted">${escapeHtml(job.company)}${job.location ? ` - ${escapeHtml(job.location)}` : ""}</p>
            </div>
            <a href="${escapeHtml(job.apply_url)}" target="_blank" rel="noreferrer">Open</a>
          </div>
        `
      )
      .join("");

    const filteredJobs = (data.filtered_jobs || [])
      .slice(0, 20)
      .map(
        (job) => `
          <div class="mini-row">
            <div>
              <strong>${escapeHtml(job.title)}</strong>
              <p class="muted">${escapeHtml(job.company)} - ${escapeHtml(job.filtered_reason || "Filtered")}</p>
            </div>
            <a href="${escapeHtml(job.apply_url)}" target="_blank" rel="noreferrer">Open</a>
          </div>
        `
      )
      .join("");

    const matches = (data.matches || [])
      .slice(0, 20)
      .map(
        (match) => `
          <div class="mini-row">
            <div>
              <strong>${escapeHtml(match.title)}</strong>
              <p class="muted">${escapeHtml(match.company)} - ${escapeHtml(match.reason || "No reason")}</p>
            </div>
            <span class="score-pill">${Number(match.score || 0).toFixed(1)} ${escapeHtml(match.fit_level || "")}</span>
          </div>
        `
      )
      .join("");

    dom.dbView.innerHTML =
      sectionHtml("Profile", profile) +
      sectionHtml("Companies", companies || `<p class="muted">No companies stored.</p>`) +
      sectionHtml("Visible Jobs", jobs || `<p class="muted">No visible jobs stored.</p>`) +
      sectionHtml("Filtered Jobs", filteredJobs || `<p class="muted">No filtered jobs.</p>`) +
      sectionHtml("Recent Matches", matches || `<p class="muted">No matches generated.</p>`);
  };

  const loadDbOverview = async (silent = false) => {
    const data = await api("/admin/db");
    renderDbOverview(data);
    if (!silent) {
      setStatus("Database view refreshed");
    }
  };

  const getFilteredClientLogs = () => {
    if (!state.logLevel) {
      return state.clientLogs;
    }
    return state.clientLogs.filter((entry) => entry.level === state.logLevel);
  };

  const renderLogs = (serverEntries = null, logFile = null) => {
    if (logFile) {
      dom.logsPath.textContent = logFile;
    }

    const mergedEntries = [...(serverEntries || []), ...getFilteredClientLogs()]
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .slice(-200);

    dom.logsCountChip.textContent = `${mergedEntries.length} entries`;
    dom.logsList.innerHTML = "";

    if (!mergedEntries.length) {
      dom.logsList.innerHTML = `<div class="log-empty">No logs for the current filter.</div>`;
      return;
    }

    mergedEntries.forEach((entry) => {
      const levelClass =
        entry.level === "ERROR" ? "red" : entry.level === "WARNING" ? "orange" : entry.level === "INFO" ? "blue" : "";
      const item = document.createElement("article");
      item.className = "log-entry";
      item.innerHTML = `
        <div class="log-top">
          <span class="badge ${levelClass}">${escapeHtml(entry.level)}</span>
          <span class="log-meta">${escapeHtml(entry.timestamp)} - ${escapeHtml(entry.logger)}</span>
        </div>
        <div class="log-message">${escapeHtml(entry.message)}</div>
      `;
      dom.logsList.appendChild(item);
    });
  };

  const loadLogs = async (silent = false) => {
    const params = new URLSearchParams({ limit: "150" });
    if (state.logLevel) {
      params.set("level", state.logLevel);
    }

    const result = await api(`/admin/logs?${params.toString()}`);
    const serverEntries = (result.entries || []).map((entry) => ({ ...entry, source: "server" }));
    renderLogs(serverEntries, result.log_file);

    if (!silent) {
      setStatus("Logs refreshed");
    }
  };

  const wire = () => {
    dom.tabButtons.forEach((button) => {
      button.addEventListener("click", () => switchTab(button.dataset.tab));
    });

    dom.btnSaveProfile.addEventListener("click", () => {
      saveProfile().catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnUploadCv.addEventListener("click", () => {
      uploadCv().catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnRunSearch.addEventListener("click", () => {
      runSearch().catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnSendReport.addEventListener("click", () => {
      sendReport().catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnDiscoverSites.addEventListener("click", () => {
      discoverSites().catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnRefreshCompanies.addEventListener("click", () => {
      loadCompanies(false).catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnRefreshJobs.addEventListener("click", () => {
      Promise.all([loadJobs(), loadFilteredJobs(), loadDbOverview(true)]).catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnRefreshMatches.addEventListener("click", () => {
      loadMatches().catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnBulkAdd.addEventListener("click", () => {
      bulkAddCompanies().catch((error) => setStatus(error.message, "warn"));
    });

    if (dom.btnRefreshDb) {
      dom.btnRefreshDb.addEventListener("click", () => {
        loadDbOverview().catch((error) => setStatus(error.message, "warn"));
      });
    }

    dom.btnRefreshLogs.addEventListener("click", () => {
      loadLogs().catch((error) => setStatus(error.message, "warn"));
    });

    dom.btnToggleLogPoll.addEventListener("click", () => {
      state.autoRefreshLogs = !state.autoRefreshLogs;
      pushClientLog("INFO", "ui.logs", `Auto refresh ${state.autoRefreshLogs ? "enabled" : "disabled"}`);
      updateLogPolling();
    });

    dom.logsLevel.addEventListener("change", () => {
      state.logLevel = dom.logsLevel.value;
      loadLogs().catch((error) => setStatus(error.message, "warn"));
    });

    window.addEventListener("error", (event) => {
      pushClientLog("ERROR", "ui.window", event.message || "Unhandled window error");
    });

    window.addEventListener("unhandledrejection", (event) => {
      const reason = event.reason && event.reason.message ? event.reason.message : String(event.reason);
      pushClientLog("ERROR", "ui.promise", reason);
    });
  };

  const init = async () => {
    wire();
    pushClientLog("INFO", "ui.boot", "UI initialized");

    try {
      await loadHealth();
      await loadProfile(true);
      await loadCompanies(true);
      await loadJobs();
      await loadFilteredJobs();
      await loadMatches();
      await loadDbOverview(true);
      setStatus("Ready");
      updateLogPolling();
    } catch (error) {
      setStatus(error.message, "warn");
    }
  };

  init();
})();
