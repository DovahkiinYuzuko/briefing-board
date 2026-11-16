/**
 * Briefing Board Application Logic (DADS, TOML I/O, i18n, No-localStorage Persistence)
 */

document.addEventListener("DOMContentLoaded", async () => {
  const data = window.BRIEFING_DATA;
  if (!data) {
    console.error("BRIEFING_DATA is not defined.");
    return;
  }

  const locales = window.BRIEFING_LOCALES || {};
  const initialSettings = window.BRIEFING_INITIAL_SETTINGS || {};
  const isHttpProtocol = window.location.protocol.startsWith("http");

  let currentLang = locales[initialSettings.language] ? initialSettings.language : "en";
  let currentViewMode = initialSettings.view_mode || "auto";
  let lastSavedStatus = "DRAFT";
  let proposedAgendas = [];
  let allCollapsed = false;

  const t = (key, params) => {
    const langDict = locales[currentLang] || {};
    const enDict = locales.en || {};
    let text = langDict[key] !== undefined ? langDict[key] : (enDict[key] !== undefined ? enDict[key] : key);
    if (params && typeof text === "string") {
      Object.keys(params).forEach((k) => {
        text = text.replace(new RegExp(`\\{${k}\\}`, "g"), String(params[k]));
      });
    }
    return text;
  };

  // DOM Elements
  const langSelectEl = document.getElementById("langSelect");
  const agendaListEl = document.getElementById("agendaList");
  const scratchpadNotesEl = document.getElementById("scratchpadNotes");
  const aiNotesCardEl = document.getElementById("aiNotesCard");
  const aiNotesContentEl = document.getElementById("aiNotesContent");
  const proposedAgendasListEl = document.getElementById("proposedAgendasList");
  const proposedCountBadgeEl = document.getElementById("proposedCountBadge");
  const proposedAgendasDisclosureEl = document.getElementById("proposedAgendasDisclosure");
  const newAgendaTitleEl = document.getElementById("newAgendaTitle");
  const newAgendaDetailEl = document.getElementById("newAgendaDetail");
  const addProposedAgendaBtn = document.getElementById("addProposedAgendaBtn");
  const saveDraftBtn = document.getElementById("saveDraftBtn");
  const saveCompleteBtn = document.getElementById("saveCompleteBtn");
  const copyNoticeBtn = document.getElementById("copyNoticeBtn");
  const toggleAllBtn = document.getElementById("toggleAllBtn");
  const hideResolvedSwitch = document.getElementById("hideResolvedSwitch");
  const allResolvedNotice = document.getElementById("allResolvedNotice");
  const toastEl = document.getElementById("toast");
  const headerTitleEl = document.getElementById("headerTitle");
  const headerSubtitleEl = document.getElementById("headerSubtitle");
  const serverStatusDot = document.getElementById("serverStatusDot");
  const serverStatusText = document.getElementById("serverStatusText");
  const overallStatusBadge = document.getElementById("overallStatusBadge");
  const statusBreakdownEl = document.getElementById("statusBreakdown");
  const bulkActionSelect = document.getElementById("bulkActionSelect");
  const applyBulkActionBtn = document.getElementById("applyBulkActionBtn");
  const completeErrorText = document.getElementById("completeErrorText");
  const viewModeBtns = document.querySelectorAll(".view-mode-btn");
  const notesSidebarEl = document.getElementById("notesSidebar");
  const mobileTabBtns = document.querySelectorAll(".dads-tab-btn");

  const persistUserSettings = async (partial) => {
    if (!isHttpProtocol) return;
    try {
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(partial),
      });
    } catch (e) {
      console.warn("Failed to persist user settings:", e);
    }
  };

  const populateLangSelect = () => {
    if (!langSelectEl) return;
    langSelectEl.innerHTML = "";
    const codes = Object.keys(locales);
    if (codes.length === 0) {
      const opt = document.createElement("option");
      opt.value = "en";
      opt.textContent = "English";
      langSelectEl.appendChild(opt);
      return;
    }
    codes.forEach((code) => {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = (locales[code]._meta && locales[code]._meta.label) || code.toUpperCase();
      langSelectEl.appendChild(opt);
    });
    langSelectEl.value = currentLang;
  };

  // Dynamically populate title and subtitle from BRIEFING_DATA
  if (data.title) {
    document.title = `${data.title} - ${t("board_page_title")}`;
    if (headerTitleEl) {
      headerTitleEl.removeAttribute("data-i18n");
      headerTitleEl.textContent = data.title;
    }
  }
  if (headerSubtitleEl) {
    headerSubtitleEl.textContent = data.subtitle || "";
  }

  // AI Notes (Read-Only, strictly separated from user's personal notes)
  const aiNotesText = data.ai_notes || data.briefing_notes || data.initialPersonalNotes || "";
  if (aiNotesText.trim() && aiNotesCardEl && aiNotesContentEl) {
    aiNotesContentEl.textContent = aiNotesText.trim();
    aiNotesCardEl.hidden = false;
  }

  const updateServerStatusIndicator = () => {
    if (isHttpProtocol && serverStatusDot && serverStatusText) {
      serverStatusDot.style.backgroundColor = "#22c55e";
      serverStatusText.textContent = t("server_connected");
    } else if (serverStatusDot && serverStatusText) {
      serverStatusDot.style.backgroundColor = "#f59e0b";
      serverStatusText.textContent = t("server_file_mode");
    }
  };

  // Mobile Tab & View Mode Selector
  let activeTab = "agenda";
  const updateMobileTabDisplay = () => {
    const isMobileMode =
      document.body.classList.contains("view-mobile") ||
      (!document.body.classList.contains("view-desktop") && window.innerWidth < 768);

    if (!isMobileMode) {
      if (agendaListEl) agendaListEl.style.display = "block";
      if (notesSidebarEl) notesSidebarEl.style.display = "block";
      return;
    }

    mobileTabBtns.forEach((btn) => {
      const isSelected = btn.dataset.tab === activeTab;
      btn.classList.toggle("active", isSelected);
      btn.setAttribute("aria-selected", String(isSelected));
    });

    if (activeTab === "agenda") {
      if (agendaListEl) agendaListEl.style.display = "block";
      if (notesSidebarEl) notesSidebarEl.style.display = "none";
    } else {
      if (agendaListEl) agendaListEl.style.display = "none";
      if (notesSidebarEl) notesSidebarEl.style.display = "block";
    }
  };

  const handleResponsiveLayout = () => {
    if (!document.body.classList.contains("view-desktop") && !document.body.classList.contains("view-mobile")) {
      updateMobileTabDisplay();
    }
  };

  const applyViewMode = (mode, shouldPersist) => {
    currentViewMode = mode;
    document.body.classList.remove("view-desktop", "view-mobile");
    viewModeBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.mode === mode);
    });

    if (mode === "desktop") {
      document.body.classList.add("view-desktop");
      if (agendaListEl) agendaListEl.style.display = "block";
      if (notesSidebarEl) notesSidebarEl.style.display = "block";
    } else if (mode === "mobile") {
      document.body.classList.add("view-mobile");
      updateMobileTabDisplay();
    } else {
      handleResponsiveLayout();
    }

    if (shouldPersist) {
      persistUserSettings({ view_mode: mode });
    }
  };

  viewModeBtns.forEach((btn) => {
    btn.addEventListener("click", () => applyViewMode(btn.dataset.mode, true));
  });

  mobileTabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      activeTab = btn.dataset.tab;
      updateMobileTabDisplay();
    });
  });

  window.addEventListener("resize", handleResponsiveLayout);

  // Toast Helper
  let toastTimer = null;
  const showToast = (message) => {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("show");
    }, 4000);
  };

  // Compute Overall Action & Breakdown from individual cards
  const getActionCounts = () => {
    const counts = { pending: 0, approve: 0, revise: 0, investigate: 0, cancel: 0 };
    data.agenda.forEach((item) => {
      const checked = document.querySelector(`input[name="action_${CSS.escape(item.id)}"]:checked`);
      const val = checked ? checked.value : "pending";
      if (Object.prototype.hasOwnProperty.call(counts, val)) {
        counts[val] += 1;
      } else {
        counts.pending += 1;
      }
    });
    return counts;
  };

  const computeOverallAction = () => {
    const total = data.agenda.length;
    const c = getActionCounts();
    if (c.pending > 0) return "pending";
    if (c.revise > 0 || c.investigate > 0) return "revise_needed";
    if (c.approve === total) return "approve";
    if (c.cancel === total) return "cancel";
    return "partial";
  };

  const updateSummaryStatus = () => {
    const c = getActionCounts();
    const overall = computeOverallAction();

    if (statusBreakdownEl) {
      statusBreakdownEl.textContent = t("breakdown_text", c);
    }

    if (overallStatusBadge) {
      overallStatusBadge.className = "domain-tag";
      const badgeConfig = {
        pending: { cls: "status-badge-wip", key: "overall_pending" },
        revise_needed: { cls: "status-badge-revise", key: "overall_revise_needed" },
        approve: { cls: "status-badge-approve", key: "overall_approve" },
        cancel: { cls: "status-badge-cancel", key: "overall_cancel" },
        partial: { cls: "status-badge-partial", key: "overall_partial" },
      };
      const cfg = badgeConfig[overall] || badgeConfig.pending;
      overallStatusBadge.classList.add(cfg.cls);
      overallStatusBadge.textContent = t(cfg.key);
    }

    if (completeErrorText && c.pending === 0) {
      completeErrorText.hidden = true;
      completeErrorText.textContent = "";
    }
  };

  // Resolved Card Helpers (Auto-collapse & Hide Resolved Switch)
  const syncResolvedCardState = (card, action) => {
    if (!card) return;
    const isResolved = action === "approve" || action === "cancel";
    card.classList.toggle("is-resolved", isResolved);
    const chip = card.querySelector(".resolved-status-chip");
    if (!chip) return;
    chip.classList.remove("chip-approve", "chip-cancel");
    if (isResolved) {
      const i18nKey = action === "approve" ? "resolved_badge_approve" : "resolved_badge_cancel";
      chip.classList.add(action === "approve" ? "chip-approve" : "chip-cancel");
      chip.setAttribute("data-i18n", i18nKey);
      chip.textContent = t(i18nKey);
      chip.hidden = false;
    } else {
      chip.removeAttribute("data-i18n");
      chip.textContent = "";
      chip.hidden = true;
    }
  };

  const updateResolvedVisibility = () => {
    const hideResolved = Boolean(hideResolvedSwitch?.checked);
    if (hideResolvedSwitch) {
      hideResolvedSwitch.setAttribute("aria-checked", String(hideResolved));
    }
    agendaListEl.classList.toggle("hide-resolved", hideResolved);
    if (allResolvedNotice) {
      const cards = Array.from(agendaListEl.querySelectorAll(".agenda-card"));
      const visibleCount = hideResolved ? cards.filter((c) => !c.classList.contains("is-resolved")).length : cards.length;
      allResolvedNotice.hidden = !(hideResolved && cards.length > 0 && visibleCount === 0);
    }
  };

  // Render Agenda Cards
  const ACTION_VALUES = ["pending", "approve", "revise", "investigate", "cancel"];

  data.agenda.forEach((item) => {
    const card = document.createElement("div");
    card.className = "agenda-card";
    card.id = `card_${item.id}`;

    const header = document.createElement("button");
    header.type = "button";
    header.className = "card-header";
    header.setAttribute("aria-expanded", "true");
    header.innerHTML = `
      <span class="card-header-title-wrap">
        <span class="domain-tag">${escapeHtml(item.domain)}</span>
        <span class="resolved-status-chip" hidden></span>
        <span class="card-title">${escapeHtml(item.title)}</span>
      </span>
      <span class="toggle-icon" aria-hidden="true">▼</span>
    `;

    header.addEventListener("click", () => {
      card.classList.toggle("collapsed");
      const isExpanded = !card.classList.contains("collapsed");
      header.setAttribute("aria-expanded", String(isExpanded));
    });

    const body = document.createElement("div");
    body.className = "card-body";

    const summaryP = document.createElement("p");
    summaryP.className = "agenda-summary";
    summaryP.textContent = item.summary;
    body.appendChild(summaryP);

    if (Array.isArray(item.history) && item.history.length > 0) {
      const historyDetails = document.createElement("details");
      historyDetails.className = "history-details";
      const historySummary = document.createElement("summary");
      historySummary.className = "history-summary";
      historySummary.setAttribute("data-i18n", "history_summary");
      historySummary.setAttribute("data-i18n-params", JSON.stringify({ count: item.history.length }));
      historySummary.textContent = t("history_summary", { count: item.history.length });
      historyDetails.appendChild(historySummary);

      const historyList = document.createElement("div");
      historyList.className = "history-list";
      item.history.forEach((h, idx) => {
        const entry = document.createElement("div");
        entry.className = "history-entry";

        const headerDiv = document.createElement("div");
        const roundStrong = document.createElement("strong");
        if (h.round) {
          roundStrong.textContent = `Round ${h.round}`;
        } else {
          roundStrong.setAttribute("data-i18n", "history_round_fallback");
          roundStrong.setAttribute("data-i18n-params", JSON.stringify({ index: idx + 1 }));
          roundStrong.textContent = t("history_round_fallback", { index: idx + 1 });
        }
        headerDiv.appendChild(roundStrong);

        if (h.action) {
          const actionSpan = document.createElement("span");
          actionSpan.textContent = " (";
          const actionTextSpan = document.createElement("span");
          actionTextSpan.setAttribute("data-i18n", "history_decision");
          actionTextSpan.setAttribute("data-i18n-params", JSON.stringify({ action: String(h.action).toUpperCase() }));
          actionTextSpan.textContent = t("history_decision", { action: String(h.action).toUpperCase() });
          actionSpan.appendChild(actionTextSpan);
          actionSpan.appendChild(document.createTextNode(")"));
          headerDiv.appendChild(actionSpan);
        }
        entry.appendChild(headerDiv);

        if (h.comment) {
          const commentDiv = document.createElement("div");
          commentDiv.setAttribute("data-i18n", "history_comment");
          commentDiv.setAttribute("data-i18n-params", JSON.stringify({ comment: h.comment }));
          commentDiv.textContent = t("history_comment", { comment: h.comment });
          entry.appendChild(commentDiv);
        }

        historyList.appendChild(entry);
      });
      historyDetails.appendChild(historyList);
      body.appendChild(historyDetails);
    }

    const initialAction = item.defaultAction || "pending";
    const actionGroup = document.createElement("div");
    actionGroup.className = "action-selector-group";

    const pillsHtml = ACTION_VALUES.map((val) => {
      const checkedAttr = initialAction === val ? "checked" : "";
      return `
        <label class="action-pill" data-action="${val}">
          <input type="radio" name="action_${escapeHtml(item.id)}" value="${val}" ${checkedAttr}>
          <span data-i18n="action_${val}">${escapeHtml(t(`action_${val}`))}</span>
        </label>
      `;
    }).join("");

    actionGroup.innerHTML = `
      <span class="action-label" data-i18n="action_selector_label">${escapeHtml(t("action_selector_label"))}</span>
      <div class="pill-container">${pillsHtml}</div>
    `;

    const updateActivePill = () => {
      const checkedInput = actionGroup.querySelector(`input[name="action_${CSS.escape(item.id)}"]:checked`);
      const allPills = actionGroup.querySelectorAll(".action-pill");
      allPills.forEach((p) => p.classList.remove("active"));
      if (checkedInput) {
        checkedInput.closest(".action-pill").classList.add("active");
        if (checkedInput.value !== "pending") {
          card.classList.remove("needs-attention");
        }
        syncResolvedCardState(card, checkedInput.value);
      }
      updateResolvedVisibility();
      updateSummaryStatus();
    };
    actionGroup.addEventListener("change", updateActivePill);
    syncResolvedCardState(card, initialAction);
    if (initialAction === "approve" || initialAction === "cancel") {
      card.classList.add("collapsed");
      header.setAttribute("aria-expanded", "false");
    }
    body.appendChild(actionGroup);

    if (item.formula) {
      const formulaBlock = document.createElement("div");
      formulaBlock.className = "presentation-block";
      formulaBlock.innerHTML = `
        <div class="presentation-title" data-i18n="formula_title">${escapeHtml(t("formula_title"))}</div>
        <div class="math-content">$$${escapeHtml(item.formula)}$$</div>
      `;
      body.appendChild(formulaBlock);
    }

    if (item.code) {
      const codeBlock = document.createElement("div");
      codeBlock.className = "presentation-block";
      codeBlock.innerHTML = `
        <div class="presentation-title" data-i18n="code_title">${escapeHtml(t("code_title"))}</div>
        <div class="code-content">
          <pre><code class="language-${escapeHtml(item.codeLang || "go")}">${escapeHtml(item.code)}</code></pre>
        </div>
      `;
      body.appendChild(codeBlock);
    }

    if (item.options && item.options.length > 0) {
      const optGroup = document.createElement("div");
      optGroup.className = "options-group";
      const isRadio = item.optionsType === "radio";

      item.options.forEach((opt) => {
        const optBox = document.createElement("label");
        optBox.className = "option-box";
        optBox.innerHTML = `
          <input type="${isRadio ? "radio" : "checkbox"}"
                 name="opt_${escapeHtml(item.id)}"
                 value="${escapeHtml(opt.id)}"
                 ${opt.defaultSelected ? "checked" : ""}>
          <div class="option-info">
            <div class="option-title">
              ${escapeHtml(opt.label)}
              ${opt.recommended ? `<span class="option-badge-recommended" data-i18n="recommended_badge">${escapeHtml(t("recommended_badge"))}</span>` : ""}
            </div>
            ${opt.description ? `<div class="option-desc">${escapeHtml(opt.description)}</div>` : ""}
          </div>
        `;
        optGroup.appendChild(optBox);
      });
      body.appendChild(optGroup);
    }

    const noteGroup = document.createElement("div");
    noteGroup.className = "dads-form-field item-note-group";
    noteGroup.innerHTML = `
      <label for="note_${escapeHtml(item.id)}" class="dads-field-label">
        <span data-i18n="item_note_label">${escapeHtml(t("item_note_label"))}</span>
        <span class="dads-requirement-label" data-i18n="optional_mark">${escapeHtml(t("optional_mark"))}</span>
      </label>
      <p id="note_hint_${escapeHtml(item.id)}" class="dads-support-text" data-i18n="item_note_hint">${escapeHtml(t("item_note_hint"))}</p>
      <input type="text" class="item-note-input" id="note_${escapeHtml(item.id)}" aria-describedby="note_hint_${escapeHtml(item.id)}" />
    `;
    body.appendChild(noteGroup);

    card.appendChild(header);
    card.appendChild(body);
    agendaListEl.appendChild(card);

    updateActivePill();
  });

  if (window.renderMathInElement) {
    window.renderMathInElement(document.body, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  }

  if (window.Prism) {
    window.Prism.highlightAll();
  }

  // Proposed Agendas Management
  const renderProposedAgendas = () => {
    if (proposedCountBadgeEl) {
      proposedCountBadgeEl.textContent = String(proposedAgendas.length);
    }
    if (proposedAgendasDisclosureEl && proposedAgendas.length > 0) {
      proposedAgendasDisclosureEl.open = true;
    }
    if (!proposedAgendasListEl) return;
    proposedAgendasListEl.innerHTML = "";
    proposedAgendas.forEach((pItem, idx) => {
      const row = document.createElement("div");
      row.className = "proposed-agenda-item";

      const textWrap = document.createElement("div");
      textWrap.className = "proposed-agenda-text";
      const titleDiv = document.createElement("div");
      titleDiv.className = "proposed-agenda-title";
      titleDiv.textContent = pItem.title;
      textWrap.appendChild(titleDiv);

      if (pItem.detail) {
        const detailDiv = document.createElement("div");
        detailDiv.className = "proposed-agenda-detail";
        detailDiv.textContent = pItem.detail;
        textWrap.appendChild(detailDiv);
      }

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "proposed-remove-btn";
      removeBtn.setAttribute("data-i18n", "remove_btn");
      removeBtn.textContent = t("remove_btn");
      removeBtn.addEventListener("click", () => {
        proposedAgendas.splice(idx, 1);
        renderProposedAgendas();
      });

      row.appendChild(textWrap);
      row.appendChild(removeBtn);
      proposedAgendasListEl.appendChild(row);
    });
  };

  if (addProposedAgendaBtn) {
    addProposedAgendaBtn.addEventListener("click", () => {
      const title = (newAgendaTitleEl?.value || "").trim();
      const detail = (newAgendaDetailEl?.value || "").trim();
      if (!title) {
        showToast(t("toast_proposed_title_required"));
        newAgendaTitleEl?.focus();
        return;
      }
      proposedAgendas.push({ title, detail });
      if (newAgendaTitleEl) newAgendaTitleEl.value = "";
      if (newAgendaDetailEl) newAgendaDetailEl.value = "";
      renderProposedAgendas();
      showToast(t("toast_proposed_added"));
    });
  }

  // Apply i18n across static and dynamic elements without losing user inputs
  const applyI18n = () => {
    document.documentElement.lang = currentLang;
    document.title = data.title
      ? `${data.title} - ${t("board_page_title")}`
      : t("board_page_title");

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (!key) return;
      const rawParams = el.getAttribute("data-i18n-params");
      let params = null;
      if (rawParams) {
        try {
          params = JSON.parse(rawParams);
        } catch (_) {}
      }
      el.textContent = t(key, params);
    });

    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      const key = el.getAttribute("data-i18n-aria");
      if (key) el.setAttribute("aria-label", t(key));
    });

    if (toggleAllBtn) {
      toggleAllBtn.textContent = allCollapsed ? t("expand_all_btn") : t("collapse_all_btn");
    }
    if (langSelectEl) {
      langSelectEl.value = currentLang;
    }

    updateServerStatusIndicator();
    updateResolvedVisibility();
    updateSummaryStatus();
  };

  // Load user settings from server (/api/settings) or fallback bundle
  const loadSettingsFromServer = async () => {
    populateLangSelect();
    if (isHttpProtocol) {
      try {
        const resp = await fetch("/api/settings");
        if (resp.ok) {
          const payload = await resp.json();
          const loaded = payload.settings || {};
          if (loaded.language && locales[loaded.language]) {
            currentLang = loaded.language;
          }
          if (loaded.view_mode) {
            currentViewMode = loaded.view_mode;
          }
        }
      } catch (e) {
        console.warn("Could not fetch user settings from server:", e);
      }
    }
    applyViewMode(currentViewMode, false);
    applyI18n();
  };

  if (langSelectEl) {
    langSelectEl.addEventListener("change", (e) => {
      currentLang = e.target.value;
      applyI18n();
      persistUserSettings({ language: currentLang });
    });
  }

  // Restore Previous Decision State (Server API -> Embedded Fallback)
  const applyDecisionState = (dec) => {
    if (!dec || typeof dec !== "object") return;
    if (dec.decision_status) {
      lastSavedStatus = String(dec.decision_status).toUpperCase();
    }
    const notesVal = dec.global_notes ?? dec.user_notes ?? "";
    if (scratchpadNotesEl && typeof notesVal === "string") {
      scratchpadNotesEl.value = notesVal;
    }
    if (Array.isArray(dec.proposed_agendas)) {
      proposedAgendas = dec.proposed_agendas
        .filter((p) => p && (typeof p === "string" || p.title))
        .map((p) =>
          typeof p === "string"
            ? { title: p, detail: "" }
            : { title: String(p.title), detail: String(p.detail || "") }
        );
      renderProposedAgendas();
    }
    if (Array.isArray(dec.decisions)) {
      dec.decisions.forEach((d) => {
        if (!d || !d.id) return;
        const card = document.getElementById(`card_${d.id}`);
        if (!card) return;

        if (d.action) {
          const radio = card.querySelector(`input[name="action_${CSS.escape(d.id)}"][value="${CSS.escape(d.action)}"]`);
          if (radio) {
            radio.checked = true;
            const group = radio.closest(".action-selector-group");
            if (group) {
              group.querySelectorAll(".action-pill").forEach((p) => p.classList.remove("active"));
              radio.closest(".action-pill").classList.add("active");
            }
          }
          syncResolvedCardState(card, d.action);
          const isResolved = d.action === "approve" || d.action === "cancel";
          card.classList.toggle("collapsed", isResolved);
          card.querySelector(".card-header")?.setAttribute("aria-expanded", String(!isResolved));
        }

        if (Array.isArray(d.selected_options)) {
          const optInputs = card.querySelectorAll(`input[name="opt_${CSS.escape(d.id)}"]`);
          optInputs.forEach((inp) => {
            inp.checked = d.selected_options.includes(inp.value);
          });
        }

        const noteInput = document.getElementById(`note_${d.id}`);
        if (noteInput && typeof d.comment === "string") {
          noteInput.value = d.comment;
        }
      });
    }
    updateResolvedVisibility();
    updateSummaryStatus();
  };

  const restorePreviousDecision = async () => {
    let restored = null;
    if (isHttpProtocol) {
      try {
        const targetPath = data.saveNoticeFilePath || "decision.toml";
        const resp = await fetch(`/api/decision?target_path=${encodeURIComponent(targetPath)}`);
        if (resp.ok) {
          const payload = await resp.json();
          if (payload.exists && payload.data) {
            restored = payload.data;
          }
        }
      } catch (e) {
        console.warn("Could not fetch existing decision from server:", e);
      }
    }
    if (!restored && data.previousDecision) {
      restored = data.previousDecision;
    }
    if (restored) {
      applyDecisionState(restored);
    } else {
      updateSummaryStatus();
    }
  };

  await loadSettingsFromServer();
  await restorePreviousDecision();

  // Hide Resolved Switch
  if (hideResolvedSwitch) {
    hideResolvedSwitch.addEventListener("change", () => {
      updateResolvedVisibility();
    });
  }

  // Toggle All Cards Button
  if (toggleAllBtn) {
    toggleAllBtn.addEventListener("click", () => {
      allCollapsed = !allCollapsed;
      const cards = document.querySelectorAll(".agenda-card");
      cards.forEach((c) => {
        c.classList.toggle("collapsed", allCollapsed);
        c.querySelector(".card-header")?.setAttribute("aria-expanded", String(!allCollapsed));
      });
      toggleAllBtn.textContent = allCollapsed ? t("expand_all_btn") : t("collapse_all_btn");
    });
  }

  // Bulk Action Shortcut (Select + Apply Button)
  if (applyBulkActionBtn && bulkActionSelect) {
    applyBulkActionBtn.addEventListener("click", () => {
      const targetAction = bulkActionSelect.value;
      data.agenda.forEach((item) => {
        const card = document.getElementById(`card_${item.id}`);
        const itemRadio = document.querySelector(
          `input[name="action_${CSS.escape(item.id)}"][value="${CSS.escape(targetAction)}"]`
        );
        if (itemRadio) {
          itemRadio.checked = true;
          const parentGroup = itemRadio.closest(".action-selector-group");
          if (parentGroup) {
            parentGroup.querySelectorAll(".action-pill").forEach((p) => p.classList.remove("active"));
            itemRadio.closest(".action-pill").classList.add("active");
          }
          if (card && targetAction !== "pending") {
            card.classList.remove("needs-attention");
          }
          syncResolvedCardState(card, targetAction);
        }
      });
      updateResolvedVisibility();
      updateSummaryStatus();
      showToast(t("toast_bulk_applied", { action: t(`bulk_${targetAction}`) }));
    });
  }

  // Safe TOML String Serializers (100% compatible with Python tomllib)
  const tomlBasicString = (str) => JSON.stringify(String(str));

  const tomlMultilineString = (str) => {
    const normalized = String(str).replace(/\r\n/g, "\n");
    if (!normalized.includes("\n")) {
      return tomlBasicString(normalized);
    }
    const escaped = normalized
      .replace(/\\/g, "\\\\")
      .replace(/"""/g, '\\"\\"\\"')
      .replace(/"$/g, '\\"');
    return `"""\n${escaped}"""`;
  };

  // Build TOML String (Top-level keys first, then [[array_of_tables]] per TOML spec)
  const generateDecisionToml = (decisionStatus) => {
    const timestamp = new Date().toISOString();
    const overallAction = computeOverallAction();
    const rawNotes = (scratchpadNotesEl?.value || "").replace(/\r\n/g, "\n").trim();

    let toml = `# Decision Record\n`;
    toml += `updated_at = ${tomlBasicString(timestamp)}\n`;
    toml += `project = ${tomlBasicString(data.project || "default-project")}\n`;
    toml += `decision_status = ${tomlBasicString(decisionStatus)}\n`;
    toml += `overall_action = ${tomlBasicString(overallAction)}\n`;
    toml += `global_notes = ${rawNotes ? tomlMultilineString(rawNotes) : '""'}\n`;

    if (proposedAgendas.length === 0) {
      toml += `proposed_agendas = []\n`;
    }
    toml += `\n`;

    if (proposedAgendas.length > 0) {
      proposedAgendas.forEach((p) => {
        toml += `[[proposed_agendas]]\n`;
        toml += `title = ${tomlBasicString(p.title)}\n`;
        if (p.detail) {
          toml += `detail = ${tomlMultilineString(p.detail)}\n`;
        }
        toml += `\n`;
      });
    }

    data.agenda.forEach((item) => {
      const selectedAction =
        document.querySelector(`input[name="action_${CSS.escape(item.id)}"]:checked`)?.value || "pending";
      const itemNote = (document.getElementById(`note_${item.id}`)?.value || "").trim();
      const selectedOpts = Array.from(
        document.querySelectorAll(`input[name="opt_${CSS.escape(item.id)}"]:checked`)
      ).map((el) => el.value);

      toml += `[[decisions]]\n`;
      toml += `id = ${tomlBasicString(item.id)}\n`;
      toml += `action = ${tomlBasicString(selectedAction)}\n`;
      toml += `selected_options = [${selectedOpts.map(tomlBasicString).join(", ")}]\n`;
      if (itemNote) {
        toml += `comment = ${tomlMultilineString(itemNote)}\n`;
      }
      toml += `\n`;
    });

    return toml;
  };

  // Save Decision Helper
  const executeSave = async (decisionStatus) => {
    const tomlContent = generateDecisionToml(decisionStatus);
    lastSavedStatus = decisionStatus;

    try {
      const targetPath = data.saveNoticeFilePath || "decision.toml";
      const response = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_path: targetPath,
          filename: "decision.toml",
          toml: tomlContent,
        }),
      });

      if (response.ok) {
        showToast(decisionStatus === "DRAFT" ? t("toast_draft_saved") : t("toast_complete_saved"));
        return;
      }
    } catch (e) {
      console.warn("Local server auto-save endpoint unavailable, falling back to download:", e);
    }

    const blob = new Blob([tomlContent], { type: "application/toml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "decision.toml";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(t("toast_downloaded", { filename: "decision.toml" }));
  };

  if (saveDraftBtn) {
    saveDraftBtn.addEventListener("click", () => executeSave("DRAFT"));
  }

  if (saveCompleteBtn) {
    saveCompleteBtn.addEventListener("click", () => {
      const counts = getActionCounts();
      if (counts.pending > 0) {
        let firstPendingCard = null;
        data.agenda.forEach((item) => {
          const val = document.querySelector(`input[name="action_${CSS.escape(item.id)}"]:checked`)?.value || "pending";
          const card = document.getElementById(`card_${item.id}`);
          if (val === "pending" && card) {
            card.classList.add("needs-attention");
            if (!firstPendingCard) firstPendingCard = card;
          }
        });
        if (completeErrorText) {
          completeErrorText.textContent = t("complete_pending_error", { count: counts.pending });
          completeErrorText.hidden = false;
        }
        if (firstPendingCard) {
          firstPendingCard.classList.remove("collapsed");
          firstPendingCard.querySelector(".card-header")?.setAttribute("aria-expanded", "true");
          firstPendingCard.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        showToast(t("toast_pending_error", { count: counts.pending }));
        return;
      }
      if (completeErrorText) {
        completeErrorText.hidden = true;
        completeErrorText.textContent = "";
      }
      executeSave("COMPLETED");
    });
  }

  // Copy Notice Text Handler (Context-aware, always English prompt for AI agent)
  if (copyNoticeBtn) {
    copyNoticeBtn.addEventListener("click", () => {
      const filePath = data.saveNoticeFilePath || "briefing-board/decision.toml";
      const overall = computeOverallAction();
      let noticeText = "";

      if (lastSavedStatus === "DRAFT" || overall === "pending") {
        noticeText = `I saved a DRAFT of the briefing to ${filePath}. The discussion is still in progress — DO NOT start implementation or create issues yet. Please review my notes and questions.`;
      } else if (overall === "revise_needed") {
        noticeText = `I completed this round of the briefing at ${filePath} (overall_action: revise_needed). Some items need revision or investigation — DO NOT start implementation yet. Please update the briefing agenda based on my feedback.`;
      } else {
        noticeText = `I have completed the briefing decisions and saved them to ${filePath} (overall_action: ${overall}). Please summarize the decisions and ask for my explicit confirmation before archiving to done/, creating tasks, or starting implementation. Do NOT run archive or implementation commands in this turn.`;
      }

      navigator.clipboard.writeText(noticeText).then(() => {
        showToast(t("toast_notice_copied"));
      });
    });
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
