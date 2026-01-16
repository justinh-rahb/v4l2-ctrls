(() => {
  const GROUPS = [
    { key: 'focus', title: 'Focus', match: (name) => name.includes('focus') },
    { key: 'exposure', title: 'Exposure', match: (name) => name.includes('exposure') },
    {
      key: 'white_balance',
      title: 'White Balance',
      match: (name) => name.includes('white_balance'),
    },
    {
      key: 'color',
      title: 'Color',
      match: (name) =>
        ['brightness', 'contrast', 'saturation', 'hue', 'gain', 'gamma'].some((t) =>
          name.includes(t),
        ),
    },
    {
      key: 'image',
      title: 'Image',
      match: (name) => ['sharpness', 'zoom', 'pan', 'tilt'].some((t) => name.includes(t)),
    },
  ];

  function apiUrl(path) {
    const baseTag = document.querySelector('base');
    const baseHref = baseTag ? baseTag.href : window.location.href;
    return new URL(path.replace(/^\/+/, ''), baseHref).toString();
  }

  function appendCacheBuster(url) {
    const marker = url.includes('?') ? '&' : '?';
    return `${url}${marker}t=${Date.now()}`;
  }

  function buildCameraUrl(camInfo, mode, baseUrl) {
    const suffix =
      camInfo.streams && camInfo.streams[mode]
        ? camInfo.streams[mode]
        : mode === 'webrtc'
          ? `${camInfo.prefix}webrtc`
          : mode === 'mjpg'
            ? `${camInfo.prefix}stream.mjpg`
            : `${camInfo.prefix}snapshot.jpg`;
    let base = baseUrl.trim();
    let url;
    if (base.includes('{path}')) {
      url = base.replace('{path}', suffix);
    } else if (
      base.includes('{prefix}') ||
      base.includes('{mode}') ||
      base.includes('{cam}') ||
      base.includes('{device}') ||
      base.includes('{index}') ||
      base.includes('{basename}')
    ) {
      url = base
        .replace('{prefix}', camInfo.prefix)
        .replace('{mode}', mode)
        .replace('{cam}', camInfo.cam)
        .replace('{device}', camInfo.device)
        .replace('{index}', camInfo.index)
        .replace('{basename}', camInfo.basename);
    } else {
      if (!base.endsWith('/')) {
        base += '/';
      }
      const cleanSuffix = suffix.startsWith('/') ? suffix.substring(1) : suffix;
      url = `${base}${cleanSuffix}`;
    }
    if (mode === 'snapshot') {
      return appendCacheBuster(url);
    }
    return url;
  }

  function groupFor(name) {
    for (const group of GROUPS) {
      if (group.match(name)) {
        return group.key;
      }
    }
    return 'other';
  }

  function checkModified(wrapper, control, currentValue) {
    const defaultValue = control.default;
    if (defaultValue !== null && defaultValue !== undefined && currentValue !== defaultValue) {
      wrapper.classList.add('modified');
    } else {
      wrapper.classList.remove('modified');
    }
  }

  function buildControl(control, onChange) {
    const wrapper = document.createElement('div');
    wrapper.className = 'control';
    wrapper.dataset.controlName = control.name;
    const title = document.createElement('div');
    title.className = 'control-title';
    title.textContent = control.name;
    if (control.default !== null && control.default !== undefined) {
      const badge = document.createElement('span');
      badge.className = 'default-badge';
      badge.textContent = ` [default: ${control.default}]`;
      title.appendChild(badge);
    }
    if (control.readonly) {
      const badge = document.createElement('span');
      badge.className = 'default-badge';
      badge.textContent = ' (read-only)';
      title.appendChild(badge);
      title.style.opacity = '0.6';
    }
    wrapper.appendChild(title);
    checkModified(wrapper, control, control.value);

    if (control.type === 'int') {
      const row = document.createElement('div');
      row.className = 'slider-row';
      const range = document.createElement('input');
      range.type = 'range';
      range.min = control.min;
      range.max = control.max;
      range.step = control.step || 1;
      range.value = control.value;
      range.dataset.control = control.name;
      range.dataset.role = 'value';
      range.disabled = control.readonly || false;
      const pill = document.createElement('div');
      pill.className = 'value-pill';
      pill.textContent = String(control.value);
      const number = document.createElement('input');
      number.type = 'number';
      number.min = control.min;
      number.max = control.max;
      number.step = control.step || 1;
      number.value = control.value;
      number.dataset.control = control.name;
      number.dataset.role = 'value';
      number.disabled = control.readonly || false;
      range.addEventListener('input', () => {
        number.value = range.value;
        pill.textContent = range.value;
        checkModified(wrapper, control, parseInt(range.value, 10));
      });
      range.addEventListener('change', onChange);
      number.addEventListener('input', () => {
        range.value = number.value;
        pill.textContent = number.value;
        checkModified(wrapper, control, parseInt(number.value, 10));
      });
      number.addEventListener('change', onChange);
      row.appendChild(range);
      row.appendChild(pill);
      wrapper.appendChild(row);
      wrapper.appendChild(number);
    } else if (control.type === 'bool') {
      const select = document.createElement('select');
      select.dataset.control = control.name;
      select.dataset.role = 'value';
      select.disabled = control.readonly || false;
      select.add(new Option('Off', '0'));
      select.add(new Option('On', '1'));
      select.value = String(control.value || 0);
      select.addEventListener('change', () => {
        checkModified(wrapper, control, parseInt(select.value, 10));
        onChange();
      });
      wrapper.appendChild(select);
    } else if (control.type === 'menu') {
      const select = document.createElement('select');
      select.dataset.control = control.name;
      select.dataset.role = 'value';
      select.disabled = control.readonly || false;
      (control.menu || []).forEach((item) => {
        select.add(new Option(item.label, String(item.value)));
      });
      select.value = String(control.value || 0);
      select.addEventListener('change', () => {
        checkModified(wrapper, control, parseInt(select.value, 10));
        onChange();
      });
      wrapper.appendChild(select);
    } else {
      const span = document.createElement('div');
      span.textContent = `Unsupported control type: ${control.type}`;
      wrapper.appendChild(span);
    }

    return wrapper;
  }

  function renderControls(container, controls, onChange) {
    container.innerHTML = '';
    const buckets = {};
    controls.forEach((control) => {
      const key = groupFor(control.name);
      if (!buckets[key]) {
        buckets[key] = [];
      }
      buckets[key].push(control);
    });
    const ordered = [...GROUPS.map((group) => group.key), 'other'];
    ordered.forEach((key) => {
      const items = buckets[key] || [];
      if (!items.length) {
        return;
      }
      const title = document.createElement('div');
      const group = GROUPS.find((g) => g.key === key);
      title.className = 'section-title';
      title.textContent = group ? group.title : 'Other';
      container.appendChild(title);
      const grid = document.createElement('div');
      grid.className = 'control-grid';
      items.forEach((control) => {
        grid.appendChild(buildControl(control, onChange));
      });
      container.appendChild(grid);
    });
  }

  async function fetchControls(cam, { silent = false, statusBox } = {}) {
    if (!silent && statusBox) {
      statusBox.textContent = 'Loading controls...';
    }
    const response = await fetch(apiUrl(`api/v4l2/ctrls?cam=${encodeURIComponent(cam)}`));
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Failed to load controls');
    }
    if (!silent && statusBox) {
      statusBox.textContent = `Loaded ${data.controls.length} controls.`;
    }
    return data.controls || data;
  }

  async function fetchInfo(cam, statusBox) {
    const response = await fetch(apiUrl(`api/v4l2/info?cam=${encodeURIComponent(cam)}`));
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Failed to fetch info');
    }
    const data = await response.json();
    if (statusBox) {
      statusBox.textContent = data.info || 'No info.';
    }
    return data;
  }

  function controlMap(controls) {
    const map = {};
    (controls || []).forEach((control) => {
      map[control.name] = control;
    });
    return map;
  }

  async function applyControlChanges(cam, controlsContainer, lastControls) {
    const payload = {};
    const previous = controlMap(lastControls);
    controlsContainer.querySelectorAll('[data-control][data-role="value"]').forEach((el) => {
      if (el.disabled) {
        return;
      }
      const name = el.dataset.control;
      const parsed = parseInt(el.value, 10);
      if (Number.isNaN(parsed)) {
        return;
      }
      const before = previous[name];
      if (!before || before.value !== parsed) {
        payload[name] = parsed;
      }
    });
    if (!Object.keys(payload).length) {
      return { applied: false, message: 'No changes to apply.' };
    }

    const response = await fetch(apiUrl(`api/v4l2/set?cam=${encodeURIComponent(cam)}`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      const error = new Error(data.stderr || data.error || 'Failed to apply controls');
      error.payload = payload;
      error.failed = data.failed || [];
      throw error;
    }
    return { applied: true, data, payload };
  }

  window.V4L2Ctrls = {
    GROUPS,
    apiUrl,
    appendCacheBuster,
    buildCameraUrl,
    renderControls,
    fetchControls,
    fetchInfo,
    controlMap,
    applyControlChanges,
  };
})();
