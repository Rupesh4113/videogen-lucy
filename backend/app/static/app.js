/**
 * Videogen-Lucy Web Application Logic + Dual-Mode Authentication
 * Features:
 * - Robust Safe JSON Response Parser (Guarantees no "Unexpected token 'I'" syntax errors)
 * - Dual-Mode Authentication (Email/Password & Mobile/OTP)
 * - Real-Time Subtitle Synchronization during video playback
 * - Storyboard preview, Full Video Pipeline, Scene Regeneration
 */
document.addEventListener("DOMContentLoaded", () => {
  // Initialize Lucide Icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // State
  let currentProjectId = null;
  let pollInterval = null;
  let activeTab = "create";
  let loadedSubtitles = [];
  let authToken = localStorage.getItem("videogen_token") || null;
  let currentUser = JSON.parse(localStorage.getItem("videogen_user") || "null");
  let isRegisterMode = false;
  let activeOtpTarget = null;

  // DOM Elements - Navigation & Forms
  const navButtons = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const promptInput = document.getElementById("promptInput");
  const languageSelect = document.getElementById("languageSelect");
  const durationSelect = document.getElementById("durationSelect");
  const videoStyleSelect = document.getElementById("videoStyleSelect");
  const charStyleSelect = document.getElementById("charStyleSelect");
  const voiceSelect = document.getElementById("voiceSelect");
  const resolutionSelect = document.getElementById("resolutionSelect");
  const aspectRatioSelect = document.getElementById("aspectRatioSelect");
  const musicMoodSelect = document.getElementById("musicMoodSelect");

  const btnExamplePrompt = document.getElementById("btnExamplePrompt");
  const btnCheckSafety = document.getElementById("btnCheckSafety");
  const safetyAlertBox = document.getElementById("safetyAlertBox");
  const btnGenerateStoryboard = document.getElementById("btnGenerateStoryboard");
  const btnDirectGenerate = document.getElementById("btnDirectGenerate");
  const btnApproveStoryboard = document.getElementById("btnApproveStoryboard");

  // Estimation Fields
  const estScenes = document.getElementById("estScenes");
  const estShots = document.getElementById("estShots");
  const estGpuTime = document.getElementById("estGpuTime");
  const estCost = document.getElementById("estCost");
  const estStorage = document.getElementById("estStorage");
  const estVram = document.getElementById("estVram");

  // Status & Progress Fields
  const currentStageBadge = document.getElementById("currentStageBadge");
  const progressBar = document.getElementById("progressBar");
  const progressStatusMessage = document.getElementById("progressStatusMessage");
  const progressPercentText = document.getElementById("progressPercentText");
  const activeProjectPill = document.getElementById("activeProjectPill");
  const activeProjectTitle = document.getElementById("activeProjectTitle");

  // Auth DOM Elements
  const authModal = document.getElementById("authModal");
  const btnLoginModal = document.getElementById("btnLoginModal");
  const btnCloseAuthModal = document.getElementById("btnCloseAuthModal");
  const userAuthPill = document.getElementById("userAuthPill");
  const userNameDisplay = document.getElementById("userNameDisplay");
  const btnLogoutBtn = document.getElementById("btnLogoutBtn");

  const tabBtnEmail = document.getElementById("tabBtnEmail");
  const tabBtnMobile = document.getElementById("tabBtnMobile");
  const paneEmail = document.getElementById("paneEmail");
  const paneMobile = document.getElementById("paneMobile");

  const formEmailAuth = document.getElementById("formEmailAuth");
  const authNameInput = document.getElementById("authNameInput");
  const authEmailInput = document.getElementById("authEmailInput");
  const authPasswordInput = document.getElementById("authPasswordInput");
  const registerNameGroup = document.getElementById("registerNameGroup");
  const btnSubmitEmailAuth = document.getElementById("btnSubmitEmailAuth");
  const btnToggleRegisterMode = document.getElementById("btnToggleRegisterMode");
  const authTogglePrompt = document.getElementById("authTogglePrompt");
  const emailAuthError = document.getElementById("emailAuthError");

  const formMobileAuth = document.getElementById("formMobileAuth");
  const authPhoneInput = document.getElementById("authPhoneInput");
  const btnSendOtp = document.getElementById("btnSendOtp");
  const otpStepPhone = document.getElementById("otpStepPhone");
  const otpStepVerify = document.getElementById("otpStepVerify");
  const authOtpInput = document.getElementById("authOtpInput");
  const authPhoneNameInput = document.getElementById("authPhoneNameInput");
  const btnBackToPhone = document.getElementById("btnBackToPhone");
  const otpDeliveryNotice = document.getElementById("otpDeliveryNotice");
  const mobileAuthError = document.getElementById("mobileAuthError");

  /**
   * Safe JSON Parser Helper
   * Safely parses JSON or extracts plain-text error messages from failed responses
   * without ever throwing "Unexpected token 'I', Internal Server Error..."
   */
  async function safeJson(res) {
    const contentType = res.headers.get("content-type") || "";
    let data;

    if (contentType.includes("application/json")) {
      try {
        data = await res.json();
      } catch (err) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `Server Error (${res.status})`);
      }
    } else {
      const text = await res.text().catch(() => "");
      try {
        data = JSON.parse(text);
      } catch {
        if (!res.ok) {
          throw new Error(text || `Server Error (${res.status}: ${res.statusText})`);
        }
        data = { message: text };
      }
    }

    if (!res.ok) {
      let errMsg = "An error occurred";
      if (typeof data?.detail === "string") {
        errMsg = data.detail;
      } else if (Array.isArray(data?.detail)) {
        errMsg = data.detail.map(d => (d.msg ? `${d.loc?.join(".") || ""}: ${d.msg}` : JSON.stringify(d))).join(", ");
      } else if (data?.message) {
        errMsg = data.message;
      } else {
        errMsg = `Server error (${res.status}): ${res.statusText}`;
      }
      throw new Error(errMsg);
    }
    return data;
  }

  // Auth Helper: Authenticated Fetch
  async function authFetch(url, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }
    return fetch(url, { ...options, headers });
  }

  // Update UI Auth State
  function renderAuthState() {
    if (currentUser && authToken) {
      btnLoginModal.classList.add("hidden");
      userAuthPill.classList.remove("hidden");
      userNameDisplay.textContent = currentUser.name || currentUser.email || currentUser.phone_number || "User";
    } else {
      btnLoginModal.classList.remove("hidden");
      userAuthPill.classList.add("hidden");
    }
    if (window.lucide) window.lucide.createIcons();
  }

  // Check initial Auth Token validity
  async function checkCurrentUser() {
    if (!authToken) {
      renderAuthState();
      return;
    }
    try {
      const res = await authFetch("/api/v1/auth/me");
      if (res.ok) {
        currentUser = await safeJson(res);
        localStorage.setItem("videogen_user", JSON.stringify(currentUser));
      } else {
        authToken = null;
        currentUser = null;
        localStorage.removeItem("videogen_token");
        localStorage.removeItem("videogen_user");
      }
    } catch (e) {
      console.warn("Auth check error", e);
    }
    renderAuthState();
  }
  checkCurrentUser();

  // Auth Modal Handlers
  btnLoginModal.addEventListener("click", () => {
    authModal.classList.remove("hidden");
    resetAuthModal();
  });

  btnCloseAuthModal.addEventListener("click", () => {
    authModal.classList.add("hidden");
  });

  btnLogoutBtn.addEventListener("click", () => {
    authToken = null;
    currentUser = null;
    localStorage.removeItem("videogen_token");
    localStorage.removeItem("videogen_user");
    renderAuthState();
    if (activeTab === "projects") {
      loadProjectsHistory();
    }
  });

  // Switch Auth Tabs (Email vs Mobile)
  tabBtnEmail.addEventListener("click", () => {
    tabBtnEmail.classList.add("active");
    tabBtnMobile.classList.remove("active");
    paneEmail.classList.add("active");
    paneMobile.classList.remove("active");
    emailAuthError.classList.add("hidden");
  });

  tabBtnMobile.addEventListener("click", () => {
    tabBtnMobile.classList.add("active");
    tabBtnEmail.classList.remove("active");
    paneMobile.classList.add("active");
    paneEmail.classList.remove("active");
    mobileAuthError.classList.add("hidden");
  });

  function resetAuthModal() {
    isRegisterMode = false;
    registerNameGroup.classList.add("hidden");
    btnSubmitEmailAuth.textContent = "Sign In";
    authTogglePrompt.textContent = "Don't have an account?";
    btnToggleRegisterMode.textContent = "Create Account";
    emailAuthError.classList.add("hidden");
    mobileAuthError.classList.add("hidden");
    otpStepPhone.classList.remove("hidden");
    otpStepVerify.classList.add("hidden");
  }

  // Toggle Email Register vs Login
  btnToggleRegisterMode.addEventListener("click", () => {
    isRegisterMode = !isRegisterMode;
    emailAuthError.classList.add("hidden");
    if (isRegisterMode) {
      registerNameGroup.classList.remove("hidden");
      btnSubmitEmailAuth.textContent = "Create Account";
      authTogglePrompt.textContent = "Already have an account?";
      btnToggleRegisterMode.textContent = "Sign In";
    } else {
      registerNameGroup.classList.add("hidden");
      btnSubmitEmailAuth.textContent = "Sign In";
      authTogglePrompt.textContent = "Don't have an account?";
      btnToggleRegisterMode.textContent = "Create Account";
    }
  });

  // Handle Email & Password Submit
  formEmailAuth.addEventListener("submit", async (e) => {
    e.preventDefault();
    emailAuthError.classList.add("hidden");
    btnSubmitEmailAuth.disabled = true;

    const email = authEmailInput.value.trim();
    const password = authPasswordInput.value;
    const name = authNameInput.value.trim();

    try {
      const endpoint = isRegisterMode ? "/api/v1/auth/register" : "/api/v1/auth/login";
      const payload = isRegisterMode ? { email, password, name } : { email, password };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await safeJson(res);

      // Save token & user
      authToken = data.access_token;
      currentUser = data.user;
      localStorage.setItem("videogen_token", authToken);
      localStorage.setItem("videogen_user", JSON.stringify(currentUser));

      authModal.classList.add("hidden");
      renderAuthState();
      if (activeTab === "projects") loadProjectsHistory();

    } catch (err) {
      emailAuthError.textContent = err.message;
      emailAuthError.classList.remove("hidden");
    } finally {
      btnSubmitEmailAuth.disabled = false;
    }
  });

  // Handle Send OTP (Mobile Phone)
  btnSendOtp.addEventListener("click", async () => {
    const phone = authPhoneInput.value.trim();
    if (!phone) {
      alert("Please enter a mobile phone number.");
      return;
    }

    btnSendOtp.disabled = true;
    btnSendOtp.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Sending OTP...`;
    mobileAuthError.classList.add("hidden");

    try {
      const res = await fetch("/api/v1/auth/otp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_or_email: phone })
      });
      const data = await safeJson(res);

      activeOtpTarget = phone;
      otpStepPhone.classList.add("hidden");
      otpStepVerify.classList.remove("hidden");
      
      let notice = `OTP code sent to ${phone}. Valid for 10 minutes.`;
      if (data.dev_otp_code) {
        notice += ` (Demo OTP Code: ${data.dev_otp_code})`;
        authOtpInput.value = data.dev_otp_code;
      }
      if (data.mobile_url) {
        otpDeliveryNotice.innerHTML = `${notice} <br><a href="${data.mobile_url}" target="_blank" class="link-btn text-xs mt-1 block">📲 Open Live Mobile Notification Channel (${data.provider})</a>`;
      } else {
        otpDeliveryNotice.textContent = notice;
      }

    } catch (err) {
      mobileAuthError.textContent = err.message;
      mobileAuthError.classList.remove("hidden");
    } finally {
      btnSendOtp.disabled = false;
      btnSendOtp.innerHTML = `<i data-lucide="send"></i> Send 6-Digit OTP Code`;
      if (window.lucide) window.lucide.createIcons();
    }
  });

  btnBackToPhone.addEventListener("click", () => {
    otpStepVerify.classList.add("hidden");
    otpStepPhone.classList.remove("hidden");
  });

  // Handle Verify OTP Submit
  formMobileAuth.addEventListener("submit", async (e) => {
    e.preventDefault();
    const otpCode = authOtpInput.value.trim();
    const name = authPhoneNameInput.value.trim();

    if (!activeOtpTarget || !otpCode) return;

    mobileAuthError.classList.add("hidden");
    try {
      const res = await fetch("/api/v1/auth/otp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_or_email: activeOtpTarget,
          otp_code: otpCode,
          name: name || undefined
        })
      });
      const data = await safeJson(res);

      authToken = data.access_token;
      currentUser = data.user;
      localStorage.setItem("videogen_token", authToken);
      localStorage.setItem("videogen_user", JSON.stringify(currentUser));

      authModal.classList.add("hidden");
      renderAuthState();
      if (activeTab === "projects") loadProjectsHistory();

    } catch (err) {
      mobileAuthError.textContent = err.message;
      mobileAuthError.classList.remove("hidden");
    }
  });

  // 1. Tab Navigation
  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });

  function switchTab(tabId) {
    activeTab = tabId;
    navButtons.forEach(b => {
      if (b.getAttribute("data-tab") === tabId) {
        b.classList.add("active");
      } else {
        b.classList.remove("active");
      }
    });

    tabPanes.forEach(p => {
      if (p.id === `tab-${tabId}`) {
        p.classList.add("active");
      } else {
        p.classList.remove("active");
      }
    });

    if (tabId === "scenes" && currentProjectId) {
      loadSceneStudio(currentProjectId);
    } else if (tabId === "compliance") {
      loadComplianceReport();
    } else if (tabId === "projects") {
      loadProjectsHistory();
    }

    if (window.lucide) window.lucide.createIcons();
  }

  // 2. Load Example Prompt
  btnExamplePrompt.addEventListener("click", () => {
    promptInput.value = "Create a heartwarming 10-minute story about a mother living in an Indian village during the monsoon. Her baby becomes sick and she takes care of the baby throughout the night.";
    durationSelect.value = "600";
    videoStyleSelect.value = "Cinematic animation";
    charStyleSelect.value = "Semi-realistic";
    musicMoodSelect.value = "Indian";
    updateEstimates();
  });

  // 3. Update Resource Estimates on change
  [durationSelect, resolutionSelect].forEach(el => {
    el.addEventListener("change", updateEstimates);
  });

  async function updateEstimates() {
    const duration = parseInt(durationSelect.value, 10);
    const resolution = resolutionSelect.value;
    try {
      const res = await fetch("/api/v1/estimates/cost", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_duration: duration, resolution: resolution })
      });
      if (res.ok) {
        const data = await safeJson(res);
        estScenes.textContent = data.total_scenes_estimated;
        estShots.textContent = data.total_shots_estimated;
        estGpuTime.textContent = `${data.estimated_generation_time_minutes} min`;
        estCost.textContent = `$${data.estimated_gpu_cost_usd.toFixed(2)}`;
        estStorage.textContent = `${data.estimated_storage_gb.toFixed(1)} GB`;
        estVram.textContent = `${data.estimated_vram_requirement_gb} GB`;
      }
    } catch (e) {
      console.warn("Error updating estimates", e);
    }
  }
  updateEstimates();

  // 4. Pre-Flight Safety & Copyright Guard
  btnCheckSafety.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    try {
      const res = await fetch("/api/v1/safety/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt })
      });
      const data = await safeJson(res);

      safetyAlertBox.classList.remove("hidden", "warn", "safe");
      if (!data.is_safe) {
        safetyAlertBox.classList.add("warn");
        let html = `<strong>⚠️ Protected Content Detected (${data.risk_level} Risk):</strong><br>`;
        html += data.detected_violations.join(", ") + "<br>";
        if (data.suggested_rewrite) {
          html += `<div class="mt-2"><strong>Suggested Safe Rewrite:</strong> "${data.suggested_rewrite}"</div>`;
        }
        safetyAlertBox.innerHTML = html;
      } else {
        safetyAlertBox.classList.add("safe");
        safetyAlertBox.innerHTML = `<strong>✓ Content & Legal Guard Passed:</strong> No protected superhero, celebrity likeness, or trademarked IP detected. Safe for YouTube publishing.`;
      }
    } catch (e) {
      console.error(e);
    }
  });

  // 5. Create Project & Generate Storyboard Preview
  btnGenerateStoryboard.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      alert("Please enter a video prompt.");
      return;
    }

    btnGenerateStoryboard.disabled = true;
    btnGenerateStoryboard.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Generating Storyboard...`;

    try {
      const projectPayload = {
        prompt: prompt,
        language: languageSelect.value,
        target_duration: parseInt(durationSelect.value, 10),
        video_style: videoStyleSelect.value,
        character_style: charStyleSelect.value,
        voice_type: voiceSelect.value,
        resolution: resolutionSelect.value,
        aspect_ratio: aspectRatioSelect.value,
        music_mood: musicMoodSelect.value
      };

      const projRes = await authFetch("/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectPayload)
      });
      const proj = await safeJson(projRes);
      currentProjectId = proj.id;

      setActiveProjectUI(proj.title || "New Project", "PLANNING", 10);

      const sbRes = await authFetch(`/api/v1/projects/${currentProjectId}/storyboard`, {
        method: "POST"
      });
      const storyboard = await safeJson(sbRes);

      renderStoryboard(storyboard);
      switchTab("storyboard");
      startPollingStatus(currentProjectId);

    } catch (e) {
      alert("Error generating storyboard: " + e.message);
    } finally {
      btnGenerateStoryboard.disabled = false;
      btnGenerateStoryboard.innerHTML = `<i data-lucide="sparkles"></i> 1. Generate Storyboard Preview`;
      if (window.lucide) window.lucide.createIcons();
    }
  });

  // 6. Direct Full Video Generation
  btnDirectGenerate.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      alert("Please enter a video prompt.");
      return;
    }

    btnDirectGenerate.disabled = true;
    try {
      const projectPayload = {
        prompt: prompt,
        language: languageSelect.value,
        target_duration: parseInt(durationSelect.value, 10),
        video_style: videoStyleSelect.value,
        character_style: charStyleSelect.value,
        voice_type: voiceSelect.value,
        resolution: resolutionSelect.value,
        aspect_ratio: aspectRatioSelect.value,
        music_mood: musicMoodSelect.value
      };

      const projRes = await authFetch("/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectPayload)
      });
      const proj = await safeJson(projRes);
      currentProjectId = proj.id;

      const genRes = await authFetch(`/api/v1/projects/${currentProjectId}/generate`, { method: "POST" });
      await safeJson(genRes);

      setActiveProjectUI(proj.title || "Full Generation", "QUEUED", 5);
      startPollingStatus(currentProjectId);
    } catch (e) {
      alert("Error starting generation: " + e.message);
    } finally {
      btnDirectGenerate.disabled = false;
    }
  });

  // 7. Approve Storyboard Button
  btnApproveStoryboard.addEventListener("click", async () => {
    if (!currentProjectId) return;
    btnApproveStoryboard.disabled = true;
    try {
      const res = await authFetch(`/api/v1/projects/${currentProjectId}/generate`, { method: "POST" });
      await safeJson(res);
      startPollingStatus(currentProjectId);
      switchTab("create");
    } catch (e) {
      alert("Failed to start generation: " + e.message);
    } finally {
      btnApproveStoryboard.disabled = false;
    }
  });

  // Render Storyboard to UI
  function renderStoryboard(sb) {
    document.getElementById("sbStoryTitle").textContent = sb.story.title;
    document.getElementById("sbStoryLogline").textContent = sb.story.logline || sb.story.summary;
    document.getElementById("sbBeginning").textContent = sb.story.beginning || "-";
    document.getElementById("sbConflict").textContent = `${sb.story.conflict || ""} ${sb.story.rising_action || ""}`;
    document.getElementById("sbClimax").textContent = sb.story.climax || "-";
    document.getElementById("sbEnding").textContent = `${sb.story.resolution || ""} ${sb.story.ending || ""}`;

    // Characters
    const charContainer = document.getElementById("characterCardsContainer");
    charContainer.innerHTML = "";
    (sb.characters || []).forEach(c => {
      const card = document.createElement("div");
      card.className = "bible-card";
      card.innerHTML = `
        <div class="bible-card-header">
          <div class="bible-name">${c.name} (${c.gender || 'Unknown'}, ${c.age || 'Adult'})</div>
          <span class="badge">${c.personality ? c.personality.split(',')[0] : 'Character'}</span>
        </div>
        <div class="text-xs text-muted mb-2"><strong>Face & Appearance:</strong> ${c.face_description || '-'}</div>
        <div class="text-xs text-muted mb-2"><strong>Clothing:</strong> ${c.clothing || '-'}</div>
        <div class="text-xs text-muted"><strong>Voice Preset:</strong> ${c.voice_preset || 'Default Neural'}</div>
      `;
      charContainer.appendChild(card);
    });

    // Locations
    const locContainer = document.getElementById("locationCardsContainer");
    locContainer.innerHTML = "";
    (sb.locations || []).forEach(loc => {
      const card = document.createElement("div");
      card.className = "bible-card";
      card.innerHTML = `
        <div class="bible-card-header">
          <div class="bible-name">${loc.name}</div>
          <span class="badge">${loc.time_of_day || 'Day'}</span>
        </div>
        <div class="text-xs text-muted mb-2">${loc.description || '-'}</div>
        <div class="text-xs text-muted"><strong>Weather / Lighting:</strong> ${loc.weather || 'Clear'} • ${loc.lighting || 'Daylight'}</div>
      `;
      locContainer.appendChild(card);
    });

    // Planned Scenes
    const sceneContainer = document.getElementById("plannedScenesContainer");
    sceneContainer.innerHTML = "";
    (sb.scenes || []).forEach(sc => {
      const card = document.createElement("div");
      card.className = "scene-item-card";
      
      let dialogueHtml = "";
      if (sc.dialogue && sc.dialogue.length > 0) {
        dialogueHtml = sc.dialogue.map(d => `<div class="text-xs text-accent mt-1"><strong>${d.character}:</strong> "${d.line}"</div>`).join("");
      }

      card.innerHTML = `
        <div class="flex-between mb-2">
          <h4 class="font-bold text-sm">Scene ${sc.scene_number}: ${sc.title || ''} (${sc.duration_seconds}s)</h4>
          <span class="badge">${sc.shots ? sc.shots.length : 5} Shots</span>
        </div>
        <div class="text-xs text-muted mb-1"><strong>Location:</strong> ${sc.location_name} • <strong>Lighting:</strong> ${sc.lighting}</div>
        <div class="text-xs text-muted mb-2"><strong>Action:</strong> ${sc.action || ''}</div>
        ${sc.narration ? `<div class="text-xs text-muted mb-1"><strong>Narration:</strong> <em>"${sc.narration}"</em></div>` : ''}
        ${dialogueHtml}
      `;
      sceneContainer.appendChild(card);
    });
  }

  // Active Project Indicator
  function setActiveProjectUI(title, stage, percent) {
    activeProjectPill.classList.remove("hidden");
    activeProjectTitle.textContent = title;
    currentStageBadge.textContent = stage;
    progressBar.style.width = `${percent}%`;
    progressPercentText.textContent = `${percent}%`;
  }

  // Status Polling Loop
  function startPollingStatus(projectId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
      try {
        const res = await authFetch(`/api/v1/projects/${projectId}/status`);
        if (!res.ok) return;
        const data = await safeJson(res);

        currentStageBadge.textContent = data.current_stage;
        progressBar.style.width = `${data.progress_percentage}%`;
        progressPercentText.textContent = `${data.progress_percentage}%`;

        document.querySelectorAll(".step-item").forEach(el => el.classList.remove("active", "completed"));
        const activeStep = document.getElementById(`step-${data.current_stage}`);
        if (activeStep) activeStep.classList.add("active");

        if (data.status === "COMPLETED") {
          clearInterval(pollInterval);
          progressStatusMessage.textContent = "✓ Video generation completed successfully!";
          setupVideoPlayer(data);
          loadSceneStudio(projectId);
        } else if (data.status === "FAILED") {
          clearInterval(pollInterval);
          progressStatusMessage.textContent = `❌ Error: ${data.error_message || 'Pipeline failed'}`;
        } else {
          progressStatusMessage.textContent = `Stage: ${data.current_stage} (${data.progress_percentage}%)`;
        }
      } catch (e) {
        console.warn("Poll error", e);
      }
    }, 2000);
  }

  // Video Theater Setup
  function setupVideoPlayer(data) {
    const player = document.getElementById("mainVideoPlayer");
    const source = document.getElementById("mainVideoSource");

    if (data.final_video_url) {
      source.src = data.final_video_url;
      player.load();
    }

    // Download Links
    document.getElementById("linkDownloadMp4").href = data.final_video_url || "#";
    document.getElementById("linkDownloadSubEn").href = data.subtitle_en_url || "#";
    document.getElementById("linkDownloadSubHi").href = data.subtitle_hi_url || "#";
    document.getElementById("linkDownloadManifest").href = data.manifest_url || "#";
    document.getElementById("linkDownloadZip").href = `/api/v1/projects/${data.project_id}/download`;

    // Load subtitles for banner display
    if (data.subtitle_en_url) {
      fetch(data.subtitle_en_url)
        .then(r => r.text())
        .then(txt => parseSRT(txt))
        .catch(() => {});
    }

    // Play Button trigger
    const btnPlay = document.getElementById("btnPlayMasterVideo");
    if (btnPlay) {
      btnPlay.onclick = () => {
        player.play().catch(e => console.log("Autoplay prevented:", e));
      };
    }

    // Time update for subtitle banner
    player.ontimeupdate = () => {
      const cur = player.currentTime;
      const match = loadedSubtitles.find(s => cur >= s.start && cur <= s.end);
      const subBanner = document.getElementById("activeSubtitleText");
      if (match && subBanner) {
        subBanner.textContent = match.text;
      } else if (subBanner && cur === 0) {
        subBanner.textContent = "Ready for playback...";
      }
    };
  }

  function parseSRT(srtText) {
    loadedSubtitles = [];
    const blocks = srtText.trim().split(/\n\s*\n/);
    blocks.forEach(block => {
      const lines = block.trim().split("\n");
      if (lines.length >= 3) {
        const timeMatch = lines[1].match(/(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})/);
        if (timeMatch) {
          const start = parseInt(timeMatch[1]) * 3600 + parseInt(timeMatch[2]) * 60 + parseInt(timeMatch[3]) + parseInt(timeMatch[4]) / 1000;
          const end = parseInt(timeMatch[5]) * 3600 + parseInt(timeMatch[6]) * 60 + parseInt(timeMatch[7]) + parseInt(timeMatch[8]) / 1000;
          const text = lines.slice(2).join(" ");
          loadedSubtitles.push({ start, end, text });
        }
      }
    });
  }

  // Load Scene Studio
  async function loadSceneStudio(projectId) {
    const container = document.getElementById("sceneStudioList");
    try {
      const res = await authFetch(`/api/v1/projects/${projectId}/scenes`);
      const scenes = await safeJson(res);
      container.innerHTML = "";

      scenes.forEach(sc => {
        const card = document.createElement("div");
        card.className = "scene-studio-card";
        
        const videoSrc = sc.video_url || "";
        card.innerHTML = `
          <div class="scene-preview-box">
            ${videoSrc ? `<video src="${videoSrc}" controls preload="metadata"></video>` : `<div class="p-6 text-center text-xs text-muted">Preview Rendering...</div>`}
          </div>
          <div class="scene-studio-body">
            <div>
              <div class="flex-between mb-1">
                <h4 class="font-bold text-sm">Scene ${sc.scene_number}: ${sc.title || ''}</h4>
                <span class="badge">${sc.duration_seconds}s</span>
              </div>
              <p class="text-xs text-muted mb-2">${sc.action || ''}</p>
            </div>
            <button class="btn btn-secondary btn-sm mt-3 btn-regen-scene" data-scene-id="${sc.id}">
              <i data-lucide="refresh-cw"></i> Regenerate Scene ${sc.scene_number}
            </button>
          </div>
        `;
        container.appendChild(card);
      });

      document.querySelectorAll(".btn-regen-scene").forEach(b => {
        b.addEventListener("click", async () => {
          const scId = b.getAttribute("data-scene-id");
          b.disabled = true;
          b.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Regenerating...`;
          try {
            const res = await authFetch(`/api/v1/projects/${projectId}/scenes/${scId}/regenerate`, { method: "POST" });
            await safeJson(res);
            await loadSceneStudio(projectId);
          } catch (err) {
            alert("Regeneration failed: " + err.message);
          }
        });
      });

      if (window.lucide) window.lucide.createIcons();
    } catch (e) {
      console.warn("Error loading scenes", e);
    }
  }

  // Load Compliance Report
  function loadComplianceReport() {
    const container = document.getElementById("complianceChecklistContainer");
    const items = [
      { title: "Original Screenplay", desc: "Crafted algorithmically from original story prompts without copyright infringement." },
      { title: "Original Character Bibles", desc: "No protected superheroes, Disney characters, or trademarked fictional entities." },
      { title: "Royalty-Free Soundtrack Ledger", desc: "Music tracks backed by CC0 / CC-BY commercial licensing records." },
      { title: "No Celebrity Likeness", desc: "All facial profiles generated synthetically with personality right compliance." },
      { title: "Standard Neural Voices", desc: "Licensed neural TTS models without unauthorized voice clones." },
      { title: "Synchronized Subtitles", desc: "English & Hindi SRT/VTT files generated and bundled in export package." },
      { title: "Asset Manifest Record", desc: "Full asset_manifest.json containing all model hashes and prompts." },
      { title: "YouTube AI Disclosure Badge", desc: "Recommended: Check 'Altered or synthetic content' disclosure on upload." }
    ];

    container.innerHTML = "";
    items.forEach(item => {
      const box = document.createElement("div");
      box.className = "checklist-item";
      box.innerHTML = `
        <i data-lucide="check-circle-2" class="checklist-icon"></i>
        <div>
          <div class="font-semibold text-sm">${item.title}</div>
          <div class="text-xs text-muted mt-1">${item.desc}</div>
        </div>
      `;
      container.appendChild(box);
    });
    if (window.lucide) window.lucide.createIcons();
  }

  // Load Projects History
  async function loadProjectsHistory() {
    const container = document.getElementById("projectsListContainer");
    try {
      const res = await authFetch("/api/v1/projects");
      const list = await safeJson(res);
      if (!list || list.length === 0) {
        container.innerHTML = "<p class='text-muted'>No past generations found.</p>";
        return;
      }
      let html = `<div class="flex-col gap-2">`;
      list.forEach(p => {
        html += `
          <div class="card p-4 flex-between">
            <div>
              <div class="font-bold text-sm">${p.title}</div>
              <div class="text-xs text-muted">${p.target_duration}s • ${p.video_style} • ${p.language.toUpperCase()} • Status: ${p.status}</div>
            </div>
            <button class="btn btn-secondary btn-sm btn-load-proj" data-id="${p.id}">
              <i data-lucide="arrow-right"></i> Open
            </button>
          </div>
        `;
      });
      html += `</div>`;
      container.innerHTML = html;

      document.querySelectorAll(".btn-load-proj").forEach(b => {
        b.addEventListener("click", () => {
          currentProjectId = b.getAttribute("data-id");
          startPollingStatus(currentProjectId);
          switchTab("theater");
        });
      });
      if (window.lucide) window.lucide.createIcons();
    } catch (e) {
      console.warn("Error fetching projects", e);
    }
  }
});
