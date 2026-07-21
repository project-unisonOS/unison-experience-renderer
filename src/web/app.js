import { createComposer } from "./composer.js";
import { createVisualAdapter } from "./modality/visual.js";
import { createAudioAdapter } from "./modality/audio.js";
import { createHapticAdapter } from "./modality/haptic.js";
import { createEventStream } from "./events.js";
import { fetchPreferences } from "./preferences.js";
import { SceneTypes, createScene, TransitionKinds, createTransition } from "./sceneGraph.js";
import { createSpeechCapture } from "./speechCapture.js";

const field = document.getElementById("field");
const glyph = document.getElementById("glyph");
const logo = document.getElementById("logo");
const question = document.getElementById("question");
const quietLabel = document.getElementById("quietLabel");
const watermark = document.getElementById("watermark");
const actions = document.getElementById("actions");
const actionNote = document.getElementById("actionNote");
const refreshAction = document.getElementById("refreshAction");
const bootstrapDisplayName = document.getElementById("bootstrapDisplayName");
const bootstrapHousehold = document.getElementById("bootstrapHousehold");
const bootstrapUser = document.getElementById("bootstrapUser");
const bootstrapEmail = document.getElementById("bootstrapEmail");
const bootstrapPassword = document.getElementById("bootstrapPassword");
const bootstrapToken = document.getElementById("bootstrapToken");
const bootstrapAction = document.getElementById("bootstrapAction");
const bootstrapConfirmed = document.getElementById("bootstrapConfirmed");
const bootstrapCancel = document.getElementById("bootstrapCancel");
const loginHandle = document.getElementById("loginHandle");
const loginPassword = document.getElementById("loginPassword");
const loginAction = document.getElementById("loginAction");
const logoutAction = document.getElementById("logoutAction");
const lockAction = document.getElementById("lockAction");
const recoveryAction = document.getElementById("recoveryAction");
const recoveryCancel = document.getElementById("recoveryCancel");
const micAction = document.getElementById("micAction");
const speakerAction = document.getElementById("speakerAction");
const modelAction = document.getElementById("modelAction");
const wakewordInput = document.getElementById("wakewordInput");
const wakewordOnAction = document.getElementById("wakewordOnAction");
const wakewordOffAction = document.getElementById("wakewordOffAction");
const finishAction = document.getElementById("finishAction");

const modalities = {
  visual: createVisualAdapter({ field, glyph, logo, question, quietLabel }),
  audio: null,
  haptic: null,
};

modalities.visual.present();

async function boot() {
  await maybeShowWatermark();
  const personId = new URLSearchParams(window.location.search).get("person_id") || null;
  const preferences = await fetchPreferences({ personId });
  const activePersonId = personId;
  modalities.audio = createAudioAdapter(preferences);
  modalities.haptic = createHapticAdapter(preferences);
  const composer = createComposer({ preferences });
  const speechCapture = createSpeechCapture();
  let speechStarted = false;
  let startupPollingActive = false;
  let onboardingState = null;

  const maybeStartSpeech = (eventEnvelope) => {
    try {
      if (!speechStarted && eventEnvelope && eventEnvelope.type === "READY_LISTENING") {
        const payload = eventEnvelope.payload && typeof eventEnvelope.payload === "object" ? eventEnvelope.payload : {};
        if (payload.speech_enabled === true && typeof payload.speech_ws_endpoint === "string") {
          speechStarted = true;
          speechCapture.start({
            wsUrl: payload.speech_ws_endpoint,
            endpointing: payload.endpointing || null,
            asrProfile: payload.asr_profile || null,
          }).catch(() => {
            speechStarted = false;
          });
        }
      }
    } catch (_) {}
  };

  const handleEnvelope = async (eventEnvelope) => {
    maybeStartSpeech(eventEnvelope);
    const plan = composer.compose(eventEnvelope);
    if (!plan) return;
    await modalities.visual.apply(plan.scene, plan.transition);
    modalities.audio.apply(plan.audio);
    modalities.haptic.apply(plan.haptic);
  };

  const refreshOnboarding = async () => {
    const status = await fetchOnboardingStatus(activePersonId);
    if (!status) return null;
    onboardingState = status;
    applyOnboardingControls(status, {
      personId: activePersonId,
      preferences,
      modalities,
      refreshOnboarding,
      handleEnvelope,
      setNote,
    });
    await handleEnvelope(startupEnvelopeFromStatus(status));
    return status;
  };

  await modalities.visual.apply(
    createScene(SceneTypes.PRESENCE, { cue: preferences.presenceCueVisual === true }),
    createTransition(TransitionKinds.FADE, preferences.reduceMotion === true ? 0 : 220),
  );

  if (preferences.presenceCueAudio === true) {
    modalities.audio.presence();
  }

  await refreshOnboarding();
  startupPollingActive = true;
  scheduleStartupRefresh(async () => {
    if (!startupPollingActive) return false;
    const status = await refreshOnboarding();
    if (!status) return true;
    return status.startup && status.startup.onboarding_required === true;
  });

  const stream = createEventStream({
    url: "/events/stream",
    onEvent: handleEnvelope,
  });

  stream.start();
}

boot();

async function maybeShowWatermark() {
  if (!watermark) return;
  try {
    const resp = await fetch("/meta", { headers: { Accept: "application/json" } });
    if (!resp.ok) return;
    const meta = await resp.json();
    if (!meta?.dev?.watermark) return;

    const shaFull = typeof meta?.build?.sha === "string" ? meta.build.sha : "unknown";
    const sha = shaFull.length > 12 ? shaFull.slice(0, 12) : shaFull;
    const host = typeof meta?.runtime?.hostname === "string" ? meta.runtime.hostname : "";
    const suffix = host ? ` · ${host}` : "";
    watermark.textContent = `unison-experience-renderer@${sha}${suffix}`;
    watermark.style.opacity = "1";
  } catch (_) {}
}

async function fetchOnboardingStatus(personId) {
  try {
    const params = personId ? `?person_id=${encodeURIComponent(personId)}` : "";
    const resp = await fetch(`/onboarding-status${params}`, { headers: sessionHeaders() });
    if (resp.status === 401) {
      const firstRun = await fetch("/first-run/status", { headers: { Accept: "application/json" } });
      if (!firstRun.ok) return null;
      return await firstRun.json();
    }
    if (!resp.ok) return null;
    const body = await resp.json();
    return body && typeof body === "object" ? body : null;
  } catch (_) {
    return null;
  }
}

function startupEnvelopeFromStatus(status) {
  const startup = status && typeof status.startup === "object" ? status.startup : {};
  const checks = startup && typeof startup.checks === "object" ? startup.checks : {};
  const steps = Array.isArray(status?.steps) ? status.steps : [];
  const remediation = Array.isArray(status?.remediation) ? status.remediation : [];
  const state = typeof startup.state === "string" ? startup.state : "starting";
  if (state === "AUTH_BOOTSTRAP_REQUIRED") {
    return {
      type: "AUTH_BOOTSTRAP_REQUIRED",
      payload: { checks, steps, remediation, bootstrap_required: true },
    };
  }
  if (state === "CORE_SERVICES_DEGRADED") {
    return {
      type: "CORE_SERVICES_DEGRADED",
      payload: { checks, steps, remediation },
    };
  }
  if (state === "SPEECH_UNAVAILABLE") {
    return {
      type: "SPEECH_UNAVAILABLE",
      payload: { checks, steps, remediation, reason: startup.speech_reason || null },
    };
  }
  if (state === "READY_LISTENING" && startup.ok === true) {
    return {
      type: "READY_LISTENING",
      payload: {
        checks,
        speech_enabled: startup.speech_ready === true,
        speech_ws_endpoint: typeof startup.speech_ws_endpoint === "string" ? startup.speech_ws_endpoint : null,
        endpointing: startup.speech_endpointing || null,
        asr_profile: startup.speech_asr_profile || null,
      },
    };
  }
  return {
    type: "BOOT_START",
    payload: { stage: "Preparing first-run experience" },
  };
}

function scheduleStartupRefresh(checkFn) {
  const tick = async () => {
    let shouldContinue = false;
    try {
      shouldContinue = (await checkFn()) === true;
    } catch (_) {
      shouldContinue = true;
    }
    if (shouldContinue) {
      window.setTimeout(tick, 3000);
    }
  };
  window.setTimeout(tick, 3000);
}

function applyOnboardingControls(status, ctx) {
  const startup = status && typeof status.startup === "object" ? status.startup : {};
  const visible = startup.onboarding_required === true;
  if (actions) {
    actions.dataset.visible = "true";
  }

  const remediation = Array.isArray(status.remediation) ? status.remediation : [];
  setNote(remediation[0] || "");

  const wakeword = status.wakeword && typeof status.wakeword === "object" ? status.wakeword : {};
  if (wakewordInput) {
    wakewordInput.value = typeof wakeword.value === "string" && wakeword.value ? wakeword.value : "unison";
  }

  if (refreshAction) {
    refreshAction.onclick = async () => {
      setNote("Rechecking readiness…");
      await ctx.refreshOnboarding();
    };
  }

  const bootstrapStep = Array.isArray(status.steps) ? status.steps.find((step) => step && step.id === "admin-bootstrap") : null;
  const bootstrapVisible = bootstrapStep && bootstrapStep.ready !== true;
  for (const element of [bootstrapDisplayName, bootstrapHousehold, bootstrapUser, bootstrapEmail, bootstrapPassword, bootstrapToken, bootstrapConfirmed, bootstrapAction, bootstrapCancel]) {
    if (element) {
      element.disabled = !bootstrapVisible;
      element.style.display = bootstrapVisible ? "" : "none";
    }
  }

  if (bootstrapAction) {
    bootstrapAction.onclick = async () => {
      const username = bootstrapUser && typeof bootstrapUser.value === "string" ? bootstrapUser.value.trim() : "";
      const displayName = bootstrapDisplayName && typeof bootstrapDisplayName.value === "string" ? bootstrapDisplayName.value.trim() : "";
      const householdName = bootstrapHousehold && typeof bootstrapHousehold.value === "string" ? bootstrapHousehold.value.trim() : "";
      const email = bootstrapEmail && typeof bootstrapEmail.value === "string" ? bootstrapEmail.value.trim() : "";
      const password = bootstrapPassword && typeof bootstrapPassword.value === "string" ? bootstrapPassword.value : "";
      const token = bootstrapToken && typeof bootstrapToken.value === "string" ? bootstrapToken.value.trim() : "";
      const confirmed = bootstrapConfirmed?.checked === true;
      if (!displayName || !householdName || !username || !password || !token || !confirmed) {
        setNote("Display name, household, login, password, local token, and explicit confirmation are required.");
        return;
      }
      setNote("Creating your independent person and assistant identities…");
      const result = await bootstrapAdmin({ displayName, householdName, username, email, password, bootstrapToken: token, confirmed });
      if (!result.ok) {
        setNote(result.detail || "Admin bootstrap failed.");
        return;
      }
      if (bootstrapPassword) bootstrapPassword.value = "";
      if (bootstrapToken) bootstrapToken.value = "";
      if (bootstrapConfirmed) bootstrapConfirmed.checked = false;
      setNote("Your person and assistant identities were created. Sign in to continue setup.");
      await ctx.refreshOnboarding();
    };
  }
  if (bootstrapCancel) {
    bootstrapCancel.onclick = () => {
      for (const element of [bootstrapDisplayName, bootstrapUser, bootstrapEmail, bootstrapPassword, bootstrapToken]) {
        if (element) element.value = "";
      }
      if (bootstrapConfirmed) bootstrapConfirmed.checked = false;
      setNote("Enrollment cancelled. No identity was created.");
    };
  }

  if (loginAction) {
    loginAction.onclick = async () => {
      const username = loginHandle?.value?.trim() || "";
      const password = loginPassword?.value || "";
      if (!username || !password) {
        setNote("Login handle and password are required.");
        return;
      }
      setNote("Signing in…");
      try {
        const response = await fetch("/session/login", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ username, password }),
        });
        const data = await response.json();
        if (!response.ok || !data.access_token) throw new Error();
        sessionStorage.setItem("unisonAccessToken", data.access_token);
        if (data.refresh_token) sessionStorage.setItem("unisonRefreshToken", data.refresh_token);
        loginPassword.value = "";
        setNote("Signed in. Your private assistant controls are available.");
        await ctx.refreshOnboarding();
      } catch (_) {
        setNote("Sign-in failed. Check the login handle and password, or try again when authentication is available.");
      }
    };
  }
  if (logoutAction) {
    logoutAction.onclick = async () => {
      const ok = await postSessionAction("/session/logout");
      sessionStorage.removeItem("unisonAccessToken");
      sessionStorage.removeItem("unisonRefreshToken");
      setNote(ok ? "This session was revoked." : "Session revocation could not be confirmed.");
    };
  }
  if (lockAction) {
    lockAction.onclick = async () => {
      const ok = await postSessionAction("/session/lock");
      sessionStorage.removeItem("unisonAccessToken");
      sessionStorage.removeItem("unisonRefreshToken");
      setNote(ok ? "Your assistant is locked and its sessions are revoked." : "Assistant lock could not be confirmed.");
    };
  }
  if (recoveryAction) {
    recoveryAction.onclick = async () => {
      try {
        const response = await fetch("/session/recovery/status", { headers: { Accept: "application/json" } });
        const data = await response.json();
        setNote(data.detail || "Recovery status is unavailable.");
      } catch (_) {
        setNote("Recovery status is temporarily unavailable. No account change was made.");
      }
    };
  }
  if (recoveryCancel) {
    recoveryCancel.onclick = () => setNote("Recovery cancelled. No account change was made.");
  }

  if (micAction) {
    micAction.onclick = async () => {
      setNote("Checking microphone access…");
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        try {
          for (const track of stream.getTracks()) track.stop();
        } catch (_) {}
        await saveOnboardingProfile(ctx.personId, { microphone_checked: true });
        setNote("Microphone access confirmed.");
        await ctx.refreshOnboarding();
      } catch (_) {
        setNote("Microphone access was not granted.");
      }
    };
  }

  if (speakerAction) {
    speakerAction.onclick = async () => {
      setNote("Playing speaker check…");
      const ok = await playSpeakerCheck(ctx.modalities.audio, ctx.personId);
      if (ok) {
        await saveOnboardingProfile(ctx.personId, { speaker_checked: true });
        setNote("Speaker check played.");
        await ctx.refreshOnboarding();
      } else {
        setNote("Speaker check could not play.");
      }
    };
  }

  if (modelAction) {
    modelAction.onclick = async () => {
      const modelStep = Array.isArray(status.steps) ? status.steps.find((step) => step && step.id === "local-model") : null;
      if (!modelStep || modelStep.available !== true) {
        setNote("Model readiness is still blocked. Recheck before confirming.");
        return;
      }
      await saveOnboardingProfile(ctx.personId, { model_checked: true });
      setNote("Model readiness confirmed.");
      await ctx.refreshOnboarding();
    };
  }

  if (wakewordOnAction) {
    wakewordOnAction.onclick = async () => {
      const wakewordValue = wakewordInput && typeof wakewordInput.value === "string" ? wakewordInput.value.trim() : "";
      await saveOnboardingProfile(ctx.personId, {
        wakeword_opt_in: true,
        wakeword: wakewordValue || "unison",
        wakeword_configured: true,
      });
      setNote("Wakeword choice saved.");
      await ctx.refreshOnboarding();
    };
  }

  if (wakewordOffAction) {
    wakewordOffAction.onclick = async () => {
      await saveOnboardingProfile(ctx.personId, {
        wakeword_opt_in: false,
        wakeword_configured: true,
      });
      setNote("Wakeword will remain off by default.");
      await ctx.refreshOnboarding();
    };
  }

  if (finishAction) {
    finishAction.onclick = async () => {
      const canFinish = status.ready_to_finish === true;
      if (!canFinish) {
        const remediation = Array.isArray(status.remediation) ? status.remediation[0] : null;
        setNote(remediation || "A few checks still need attention before setup can finish.");
        return;
      }
      await saveOnboardingProfile(ctx.personId, {
        model_checked: true,
        completed: true,
      });
      setNote("Setup recorded. Returning to presence…");
      await ctx.refreshOnboarding();
    };
  }
}

function sessionHeaders() {
  const headers = { Accept: "application/json" };
  const token = sessionStorage.getItem("unisonAccessToken");
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function postSessionAction(path) {
  const token = sessionStorage.getItem("unisonAccessToken");
  if (!token) return false;
  try {
    const response = await fetch(path, { method: "POST", headers: sessionHeaders() });
    return response.ok;
  } catch (_) {
    return false;
  }
}

async function saveOnboardingProfile(personId, payload) {
  const body = { person_id: personId, ...payload };
  const resp = await fetch("/onboarding/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error("onboarding save failed");
  }
  return await resp.json();
}

async function bootstrapAdmin({ displayName, householdName, username, email, password, bootstrapToken, confirmed }) {
  try {
    const resp = await fetch("/onboarding/bootstrap-admin", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        username,
        display_name: displayName,
        household_name: householdName,
        email,
        password,
        bootstrap_token: bootstrapToken,
        confirmed,
      }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      const detail = typeof body?.detail === "string"
        ? body.detail
        : typeof body?.detail?.detail === "string"
          ? body.detail.detail
          : "Admin bootstrap failed.";
      return { ok: false, detail };
    }
    return { ok: true, body: await resp.json() };
  } catch (_) {
    return { ok: false, detail: "Auth bootstrap is unavailable." };
  }
}

async function playSpeakerCheck(audioAdapter, personId) {
  try {
    const resp = await fetch("/speech/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        text: "UnisonOS speaker check.",
        person_id: personId,
        session_id: "onboarding-speaker-check",
      }),
    });
    if (!resp.ok) return false;
    const body = await resp.json();
    if (!body || body.ok !== true || typeof body.audio_url !== "string") return false;
    audioAdapter.apply({ kind: "tts_play", url: body.audio_url });
    return true;
  } catch (_) {
    return false;
  }
}

function setNote(message) {
  if (!actionNote) return;
  actionNote.textContent = typeof message === "string" ? message : "";
  actionNote.dataset.visible = message ? "true" : "false";
}
