(() => {
  const config = window.V4L2CtrlsConfig || {};
  const {
    buildCameraUrl,
    fetchControls,
    fetchInfo,
    renderControls,
    applyControlChanges,
    controlMap,
  } = window.V4L2Ctrls;

  const cameraUrlInput = document.getElementById('camera-url');
  const cameraSelect = document.getElementById('camera-select');
  const previewMode = document.getElementById('preview-mode');
  const preview = document.getElementById('preview');
  const controlsContainer = document.getElementById('controls');
  const applyButton = document.getElementById('apply');
  const resetButton = document.getElementById('reset');
  const statusBox = document.getElementById('status');
  const themeSelect = document.getElementById('theme-select');
  const autoApplyCheckbox = document.getElementById('auto-apply');

  let cams = [];
  let currentControls = [];
  let lastControls = [];
  let autoApplyTimeout = null;

  const storageKey = (key) => `v4l2ctrls-${config.storagePrefix}-${key}`;

  function logStatus(message) {
    statusBox.textContent = message;
  }

  function applyTheme(theme) {
    if (theme === 'system') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    localStorage.setItem(storageKey('theme'), theme);
  }

  function getCameraUrl() {
    return cameraUrlInput.value.trim();
  }

  function updatePreview() {
    const cam = cameraSelect.value;
    const mode = previewMode.value;
    const camInfo = cams.find((c) => c.cam === cam);
    if (!camInfo) {
      preview.innerHTML = '<div>No camera selected.</div>';
      return;
    }
    const previewUrl = buildCameraUrl(camInfo, mode, getCameraUrl());
    if (mode === 'webrtc') {
      preview.innerHTML = `<iframe src="${previewUrl}"></iframe>`;
    } else if (mode === 'mjpg') {
      preview.innerHTML = `<img src="${previewUrl}" alt="MJPG stream" />`;
    } else {
      preview.innerHTML = `<img src="${previewUrl}" alt="Snapshot" />`;
    }
    localStorage.setItem(storageKey('base-url'), cameraUrlInput.value);
    localStorage.setItem(storageKey('preview-mode'), mode);
    localStorage.setItem(storageKey('cam'), cam);
  }

  function updateControlValues(values) {
    const byName = controlMap(currentControls);
    Object.entries(values).forEach(([name, value]) => {
      if (byName[name]) {
        byName[name].value = value;
      }
    });
    lastControls = JSON.parse(JSON.stringify(currentControls));
  }

  function scheduleAutoApply() {
    if (!autoApplyCheckbox.checked) {
      return;
    }
    if (autoApplyTimeout) {
      clearTimeout(autoApplyTimeout);
    }
    autoApplyTimeout = setTimeout(() => {
      applyChanges();
    }, 500);
  }

  function resetControlToDefault(controlName) {
    const ctrl = currentControls.find((control) => control.name === controlName);
    if (!ctrl || ctrl.default === null || ctrl.default === undefined) {
      return;
    }
    const elements = controlsContainer.querySelectorAll(
      `[data-control="${controlName}"][data-role="value"]`,
    );
    elements.forEach((el) => {
      el.value = String(ctrl.default);
      if (el.type === 'range') {
        const wrapper = el.closest('.control');
        const pill = wrapper.querySelector('.value-pill');
        if (pill) {
          pill.textContent = String(ctrl.default);
        }
        const number = wrapper.querySelector('input[type="number"]');
        if (number) {
          number.value = String(ctrl.default);
        }
      }
      const wrapper = el.closest('.control');
      if (wrapper) {
        const defaultValue = ctrl.default;
        const currentValue = ctrl.default;
        if (defaultValue !== null && defaultValue !== undefined && currentValue !== defaultValue) {
          wrapper.classList.add('modified');
        } else {
          wrapper.classList.remove('modified');
        }
      }
    });
  }

  async function applyChanges() {
    const cam = cameraSelect.value;
    applyButton.disabled = true;
    try {
      const result = await applyControlChanges(cam, controlsContainer, lastControls);
      if (!result.applied) {
        logStatus(result.message);
        return;
      }
      logStatus(
        `Applied: ${JSON.stringify(result.data.applied, null, 2)}\n${result.data.stdout || ''}`.trim(),
      );
      if (autoApplyCheckbox.checked) {
        updateControlValues(result.payload);
      } else {
        currentControls = await fetchControls(cam, { silent: true });
        lastControls = JSON.parse(JSON.stringify(currentControls));
        renderControls(controlsContainer, currentControls, scheduleAutoApply);
      }
      if (previewMode.value === 'snapshot') {
        updatePreview();
      } else {
        const camInfo = cams.find((c) => c.cam === cam);
        if (camInfo) {
          const snap = buildCameraUrl(camInfo, 'snapshot', getCameraUrl());
          const img = new Image();
          img.src = snap;
        }
      }
    } catch (err) {
      logStatus(`Error: ${err.message}`);
      const payload = err.payload || {};
      Object.keys(payload).forEach((name) => resetControlToDefault(name));
      await loadControls(cam, true);
    } finally {
      applyButton.disabled = false;
    }
  }

  async function loadControls(cam, silent = false) {
    try {
      currentControls = await fetchControls(cam, { silent, statusBox });
      lastControls = JSON.parse(JSON.stringify(currentControls));
      renderControls(controlsContainer, currentControls, scheduleAutoApply);
    } catch (err) {
      renderControls(controlsContainer, [], scheduleAutoApply);
      logStatus(`Error: ${err.message}`);
    }
  }

  async function loadInfo(cam) {
    try {
      await fetchInfo(cam, statusBox);
    } catch (err) {
      logStatus(`Error: ${err.message}`);
    }
  }

  async function init() {
    const storedTheme = localStorage.getItem(storageKey('theme')) || 'system';
    themeSelect.value = storedTheme;
    applyTheme(storedTheme);
    const storedBase = localStorage.getItem(storageKey('base-url'));
    cameraUrlInput.value = storedBase || config.cameraUrl || '';
    const camsResp = await fetch(window.V4L2Ctrls.apiUrl('api/cams'));
    cams = await camsResp.json();
    cameraSelect.innerHTML = '';
    cams.forEach((cam) => {
      cameraSelect.add(new Option(cam.cam, cam.cam));
    });
    const storedCam = localStorage.getItem(storageKey('cam'));
    if (storedCam && cams.find((c) => c.cam === storedCam)) {
      cameraSelect.value = storedCam;
    }
    const storedMode = localStorage.getItem(storageKey('preview-mode'));
    if (storedMode) {
      previewMode.value = storedMode;
    }
    const storedAutoApply = localStorage.getItem(storageKey('auto-apply'));
    if (storedAutoApply === 'true') {
      autoApplyCheckbox.checked = true;
    }
    updatePreview();
    await loadControls(cameraSelect.value);
    await loadInfo(cameraSelect.value);
  }

  cameraUrlInput.addEventListener('change', updatePreview);
  previewMode.addEventListener('change', updatePreview);
  themeSelect.addEventListener('change', () => {
    applyTheme(themeSelect.value);
  });
  autoApplyCheckbox.addEventListener('change', () => {
    localStorage.setItem(storageKey('auto-apply'), autoApplyCheckbox.checked);
  });
  cameraSelect.addEventListener('change', async () => {
    updatePreview();
    await loadControls(cameraSelect.value);
    await loadInfo(cameraSelect.value);
  });
  applyButton.addEventListener('click', applyChanges);
  resetButton.addEventListener('click', async () => {
    resetButton.disabled = true;
    try {
      logStatus('Resetting controls to defaults...');
      const cam = cameraSelect.value;
      const response = await fetch(
        window.V4L2Ctrls.apiUrl(`api/v4l2/reset?cam=${encodeURIComponent(cam)}`),
        {
          method: 'POST',
        },
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to reset controls');
      }
      const succeeded = data.succeeded || [];
      const failed = data.failed || [];
      let message = `Reset: ${succeeded.length} succeeded, ${failed.length} failed. State: ${
        data.state_removed ? 'removed' : 'not found'
      }.`;
      if (failed.length > 0) {
        message += '\n\nFailed:';
        failed.forEach((entry) => {
          const err = entry.error.replace(/^.*:\s*/, '').replace(/\s+/g, ' ').trim();
          message += `\n  ${entry.name}: ${err}`;
        });
      }
      logStatus(message);
      await loadControls(cam, true);
    } catch (err) {
      logStatus(`Error: ${err.message}`);
    } finally {
      resetButton.disabled = false;
    }
  });

  init().catch((err) => {
    logStatus(`Error: ${err.message}`);
  });
})();
