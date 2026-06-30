const state = {
  currentRun: null,
  currentTab: 'extracted',
  runData: null,
};

const els = {
  uploadForm: document.querySelector('#uploadForm'),
  pptFile: document.querySelector('#pptFile'),
  providerSelect: document.querySelector('#providerSelect'),
  runName: document.querySelector('#runName'),
  statusText: document.querySelector('#statusText'),
  runsList: document.querySelector('#runsList'),
  refreshRuns: document.querySelector('#refreshRuns'),
  currentRunTitle: document.querySelector('#currentRunTitle'),
  slideCount: document.querySelector('#slideCount'),
  segmentCount: document.querySelector('#segmentCount'),
  sceneCount: document.querySelector('#sceneCount'),
  promptCount: document.querySelector('#promptCount'),
  tabs: document.querySelectorAll('.tab'),
  editorTitle: document.querySelector('#editorTitle'),
  jsonEditor: document.querySelector('#jsonEditor'),
  formatJson: document.querySelector('#formatJson'),
  saveStoryPlan: document.querySelector('#saveStoryPlan'),
  copyMarkdown: document.querySelector('#copyMarkdown'),
  downloadMarkdown: document.querySelector('#downloadMarkdown'),
  downloadJson: document.querySelector('#downloadJson'),
  promptPreview: document.querySelector('#promptPreview'),
  progressCard: document.querySelector('#progressCard'),
  progressLabel: document.querySelector('#progressLabel'),
  progressPercent: document.querySelector('#progressPercent'),
  progressFill: document.querySelector('#progressFill'),
  stepList: document.querySelector('#stepList'),
};

const tabLabels = {
  extracted: 'Extracted Slides',
  psd: 'PSD',
  story_plan: 'Story Plan',
  storyboard: 'Storyboard',
  video_prompts: 'Prompts JSON',
  video_prompts_md: 'Prompts Markdown',
};

function setStatus(message, kind = '') {
  els.statusText.textContent = message;
  els.statusText.className = kind;
}


function resetProgress() {
  updateProgress({ progress: 0, step: 'queued', message: 'Queued', status: 'idle' });
}

function updateProgress(job) {
  const progress = Math.max(0, Math.min(100, Number(job?.progress || 0)));
  els.progressFill.style.width = `${progress}%`;
  els.progressPercent.textContent = `${progress}%`;
  els.progressLabel.textContent = job?.message || 'Queued';

  const activeStep = job?.step || 'queued';
  const order = ['extract', 'psd', 'story_plan', 'storyboard', 'prompts'];
  const activeIndex = order.indexOf(activeStep);
  els.stepList.querySelectorAll('li').forEach((item) => {
    const step = item.dataset.step;
    const index = order.indexOf(step);
    item.classList.toggle('active', step === activeStep);
    item.classList.toggle('done', activeIndex > index || job?.status === 'done');
    item.classList.toggle('error', job?.status === 'error' && step === activeStep);
  });
}

async function pollJob(jobId) {
  while (true) {
    const job = await apiJson(`/api/jobs/${encodeURIComponent(jobId)}`);
    updateProgress(job);
    setStatus(job.message || job.status);

    if (job.status === 'done') {
      state.currentRun = job.run_id;
      state.runData = job.result;
      els.currentRunTitle.textContent = job.run_id;
      renderEditor();
      await loadRuns();
      setStatus('Ready');
      return job;
    }

    if (job.status === 'error') {
      throw new Error(job.error || job.message || 'Pipeline failed');
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

function pretty(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

function updateSummary(data) {
  const extracted = data?.extracted || {};
  const storyPlan = data?.story_plan || {};
  const storyboard = data?.storyboard || {};
  const prompts = data?.video_prompts || {};
  els.slideCount.textContent = extracted.slide_count || 0;
  els.segmentCount.textContent = (storyPlan.segments || []).length;
  els.sceneCount.textContent = (storyboard.scenes || []).length;
  els.promptCount.textContent = (prompts.prompts || []).length;
}

function renderEditor() {
  const data = state.runData;
  els.editorTitle.textContent = tabLabels[state.currentTab];
  els.jsonEditor.readOnly = state.currentTab !== 'story_plan';
  els.saveStoryPlan.disabled = state.currentTab !== 'story_plan' || !state.currentRun;

  if (!data) {
    els.jsonEditor.value = '';
    els.promptPreview.textContent = '';
    updateSummary(null);
    return;
  }

  els.jsonEditor.value = pretty(data[state.currentTab]);
  els.promptPreview.textContent = data.video_prompts_md || '';
  updateSummary(data);
}

function renderRuns(runs) {
  els.runsList.innerHTML = '';
  if (!runs.length) {
    const empty = document.createElement('div');
    empty.className = 'run-meta';
    empty.textContent = 'No runs';
    els.runsList.appendChild(empty);
    return;
  }

  runs.forEach((run) => {
    const button = document.createElement('button');
    button.className = `run-item ${run.run_id === state.currentRun ? 'active' : ''}`;
    button.type = 'button';
    button.innerHTML = `<span class="run-title"></span><span class="run-meta"></span>`;
    button.querySelector('.run-title').textContent = run.run_id;
    button.querySelector('.run-meta').textContent = `${run.slide_count || 0} slides · ${run.segments || 0} segments · ${run.prompts || 0} prompts`;
    button.addEventListener('click', () => loadRun(run.run_id));
    els.runsList.appendChild(button);
  });
}

async function loadRuns() {
  const data = await apiJson('/api/runs');
  renderRuns(data.runs || []);
}

async function loadRun(runId) {
  setStatus('Loading');
  const data = await apiJson(`/api/runs/${encodeURIComponent(runId)}`);
  state.currentRun = data.run_id;
  state.runData = data;
  els.currentRunTitle.textContent = data.run_id;
  renderEditor();
  await loadRuns();
  setStatus('Ready');
}

els.uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!els.pptFile.files.length) {
    setStatus('Choose a PPTX file', 'is-warn');
    return;
  }

  const formData = new FormData();
  formData.append('ppt', els.pptFile.files[0]);
  formData.append('provider', els.providerSelect.value);
  formData.append('run_name', els.runName.value);

  try {
    els.uploadForm.querySelector('button[type="submit"]').disabled = true;
    setStatus('Uploading');
    resetProgress();
    const job = await apiJson('/api/run', { method: 'POST', body: formData });
    state.currentRun = job.run_id;
    els.currentRunTitle.textContent = job.run_id;
    updateProgress(job);
    await pollJob(job.job_id);
  } catch (error) {
    setStatus(error.message, 'is-error');
  } finally {
    els.uploadForm.querySelector('button[type="submit"]').disabled = false;
  }
});

els.tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    els.tabs.forEach((item) => item.classList.remove('active'));
    tab.classList.add('active');
    state.currentTab = tab.dataset.tab;
    renderEditor();
  });
});

els.refreshRuns.addEventListener('click', async () => {
  try {
    setStatus('Refreshing');
    await loadRuns();
    setStatus('Ready');
  } catch (error) {
    setStatus(error.message, 'is-error');
  }
});

els.formatJson.addEventListener('click', () => {
  if (state.currentTab === 'video_prompts_md') return;
  try {
    els.jsonEditor.value = JSON.stringify(JSON.parse(els.jsonEditor.value), null, 2);
    setStatus('Formatted');
  } catch (error) {
    setStatus('Invalid JSON', 'is-error');
  }
});

els.saveStoryPlan.addEventListener('click', async () => {
  if (!state.currentRun || state.currentTab !== 'story_plan') return;
  try {
    const storyPlan = JSON.parse(els.jsonEditor.value);
    setStatus('Rebuilding from Story Plan');
    els.saveStoryPlan.disabled = true;
    const provider = els.providerSelect.value;
    const data = await apiJson(`/api/runs/${encodeURIComponent(state.currentRun)}/story-plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ story_plan: storyPlan, provider }),
    });
    state.runData = data;
    renderEditor();
    await loadRuns();
    setStatus('Ready');
  } catch (error) {
    setStatus(error.message, 'is-error');
  } finally {
    els.saveStoryPlan.disabled = false;
  }
});

els.copyMarkdown.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(state.runData?.video_prompts_md || '');
    setStatus('Copied');
  } catch (error) {
    setStatus('Copy failed', 'is-error');
  }
});

function download(filename) {
  if (!state.currentRun) return;
  window.location.href = `/api/runs/${encodeURIComponent(state.currentRun)}/download/${filename}`;
}

els.downloadMarkdown.addEventListener('click', () => download('video_prompts.md'));
els.downloadJson.addEventListener('click', () => download('video_prompts.json'));

resetProgress();
loadRuns().catch((error) => setStatus(error.message, 'is-error'));
