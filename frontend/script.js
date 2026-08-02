const imageInput = document.getElementById('imageInput');
const dropzone = document.getElementById('dropzone');
const dzTitle = document.getElementById('dzTitle');
const slide = document.getElementById('slide');
const preview = document.getElementById('preview');
const analyzeBtn = document.getElementById('analyzeBtn');
const statusLine = document.getElementById('statusLine');
const statusText = document.getElementById('statusText');
const fileMeta = document.getElementById('fileMeta');
const report = document.getElementById('report');
const btnSingle = document.getElementById('btnSingle');
const btnField = document.getElementById('btnField');
const btnPlanner = document.getElementById('btnPlanner');
const heatmapImg = document.getElementById('heatmapImg');
const soilForm = document.getElementById('soilForm');
const plannerBtn = document.getElementById('plannerBtn');
const plannerStatusLine = document.getElementById('plannerStatusLine');
const plannerStatusText = document.getElementById('plannerStatusText');
const plannerReport = document.getElementById('plannerReport');
const cropCardList = document.getElementById('cropCardList');
let currentMode = 'single';

btnSingle.addEventListener('click', () => setMode('single'));
btnField.addEventListener('click', () => setMode('field'));
btnPlanner.addEventListener('click', () => setMode('planner'));

function setMode(mode) {
  currentMode = mode;
  btnSingle.classList.toggle('active', mode === 'single');
  btnField.classList.toggle('active', mode === 'field');
  btnPlanner.classList.toggle('active', mode === 'planner');

  const isPlanner = mode === 'planner';
  soilForm.classList.toggle('show', isPlanner);
  dropzone.style.display = isPlanner ? 'none' : '';
  slide.classList.remove('show');
  analyzeBtn.style.display = isPlanner ? 'none' : '';
  statusLine.classList.remove('show');

  report.classList.remove('show');
  plannerReport.classList.remove('show');
}

// Static, plain-language treatment notes — no external API call needed.
const RECOMMENDATIONS = {
  "Pepper_Bacterial_spot": "Remove infected leaves, avoid overhead watering, and apply a copper-based bactericide. Rotate crops next season.",
  "Pepper_healthy": "No action needed. Keep up current watering and spacing to prevent future stress.",
  "Potato_Early_blight": "Remove affected foliage, improve air circulation, and apply a fungicide containing chlorothalonil or mancozeb.",
  "Potato_Late_blight": "Destroy infected plants immediately to prevent spread. Apply a fungicide with metalaxyl and avoid overhead irrigation.",
  "Potato_healthy": "No action needed. Keep up current watering and spacing to prevent future stress.",
  "Tomato_Bacterial_spot": "Remove infected leaves, avoid working with wet plants, and apply a copper-based bactericide.",
  "Tomato_Early_blight": "Remove lower infected leaves, mulch around the base, and apply a fungicide with chlorothalonil.",
  "Tomato_Late_blight": "Destroy infected plants immediately — this spreads fast. Apply a fungicide with metalaxyl or mancozeb.",
  "Tomato_Leaf_Mold": "Improve greenhouse/field ventilation to reduce humidity, and apply a fungicide labeled for leaf mold.",
  "Tomato_Septoria_leaf_spot": "Remove infected lower leaves, avoid overhead watering, and apply a fungicide containing chlorothalonil.",
  "Tomato_Spider_mites": "Spray with insecticidal soap or neem oil, and increase humidity around plants to discourage mites.",
  "Tomato_Target_Spot": "Remove infected leaves and apply a fungicide with chlorothalonil or azoxystrobin.",
  "Tomato_YellowLeaf_Curl_Virus": "Remove and destroy infected plants — this is whitefly-transmitted. Control whitefly populations with insecticide or netting.",
  "Tomato_mosaic_virus": "Remove and destroy infected plants immediately. Disinfect tools between plants — this virus spreads by contact.",
  "Tomato_healthy": "No action needed. Keep up current watering and spacing to prevent future stress.",
  "default": "Consult a local agricultural extension worker for specific treatment guidance."
};

let specimenId = "";

function newSpecimenId() {
  const d = new Date();
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
  const rand = Math.floor(1000 + Math.random() * 9000);
  return `SPC-${stamp}-${rand}`;
}

dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('drag');
  if (e.dataTransfer.files[0]) {
    imageInput.files = e.dataTransfer.files;
    handleFile(e.dataTransfer.files[0]);
  }
});

imageInput.addEventListener('change', e => {
  if (e.target.files[0]) handleFile(e.target.files[0]);
});

function handleFile(file) {
  specimenId = newSpecimenId();
  preview.src = URL.createObjectURL(file);
  slide.classList.add('show');
  dzTitle.textContent = file.name;
  fileMeta.textContent = `${specimenId} · ${(file.size / 1024).toFixed(0)} KB`;
  analyzeBtn.disabled = false;
  analyzeBtn.textContent = "Run diagnostic";
  report.classList.remove('show');
}

analyzeBtn.addEventListener('click', async () => {
  const file = imageInput.files[0];
  if (!file) return;

  analyzeBtn.disabled = true;
  slide.classList.add('scanning');
  statusLine.classList.add('show');
  statusText.textContent = 'Running diagnostic…';
  report.classList.remove('show');

  const formData = new FormData();
  formData.append('file', file);

  const endpoint = currentMode === 'single'
    ? 'http://127.0.0.1:8000/predict'
    : 'http://127.0.0.1:8000/api/diagnose/field';

  try {
    const response = await fetch(endpoint, { method: 'POST', body: formData });
    if (!response.ok) throw new Error('Backend error');
    const data = await response.json();
    currentMode === 'single' ? renderReport(data) : renderFieldReport(data);
  } catch (err) {
    statusText.textContent = "Couldn't reach the backend — check it's running on port 8000.";
    slide.classList.remove('scanning');
    analyzeBtn.disabled = false;
    return;
  }

  slide.classList.remove('scanning');
  statusLine.classList.remove('show');
  analyzeBtn.disabled = false;
  analyzeBtn.textContent = "Run another diagnostic";
});

function renderFieldReport(data) {
  document.getElementById('specimenIdOut').textContent = specimenId;
  document.getElementById('diseaseName').textContent = 'Field Stress Map';

  heatmapImg.src = data.heatmap_url;
  heatmapImg.style.display = 'block';

  document.getElementById('confValue').textContent = '—';
  document.getElementById('confBar').style.width = '0%';

  const stamp = document.getElementById('stamp');
  stamp.textContent = 'Scan complete';
  stamp.className = 'stamp uncertain';

  document.getElementById('recText').textContent = data.note ||
    'Red/yellow zones indicate lower vegetation health. Zoom into flagged zones and run a single-leaf scan for a specific diagnosis.';

  report.classList.add('show');
}

function renderReport(data) {
  heatmapImg.style.display = 'none';
  const rawName = (data.disease || 'Unknown').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  const isHealthy = /healthy/i.test(rawName);
  const confidence = Number(data.confidence) || 0;

  document.getElementById('specimenIdOut').textContent = specimenId;
  document.getElementById('diseaseName').textContent = rawName;
  document.getElementById('confValue').textContent = confidence.toFixed(1) + '%';

  const stamp = document.getElementById('stamp');
  if (confidence < 60) {
    stamp.textContent = 'Low confidence';
    stamp.className = 'stamp uncertain';
  } else if (isHealthy) {
    stamp.textContent = 'Healthy';
    stamp.className = 'stamp healthy';
  } else {
    stamp.textContent = 'Disease detected';
    stamp.className = 'stamp diseased';
  }

  document.getElementById('recText').textContent =
  confidence < 60
    ? "Confidence is low — retake the photo in even lighting with the leaf filling the frame, then try again."
    : (RECOMMENDATIONS[data.disease] || RECOMMENDATIONS.default);

  requestAnimationFrame(() => {
    document.getElementById('confBar').style.width = Math.min(confidence, 100) + '%';
  });

  report.classList.add('show');
}

soilForm.addEventListener('submit', async e => {
  e.preventDefault();

  const payload = {
    location: document.getElementById('fLocation').value,
    temperature: Number(document.getElementById('fTemperature').value),
    humidity: Number(document.getElementById('fHumidity').value),
    rainfall: Number(document.getElementById('fRainfall').value),
    ph: Number(document.getElementById('fPh').value),
    nitrogen: Number(document.getElementById('fNitrogen').value),
    phosphorus: Number(document.getElementById('fPhosphorus').value),
    potassium: Number(document.getElementById('fPotassium').value),
  };

  plannerBtn.disabled = true;
  plannerStatusLine.classList.add('show');
  plannerStatusText.textContent = 'Scoring soil against crop database…';
  plannerReport.classList.remove('show');

  try {
    const response = await fetch('http://127.0.0.1:8000/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error('Backend error');
    const data = await response.json();
    renderPlannerReport(data, payload.location);
  } catch (err) {
    plannerStatusText.textContent = "Couldn't reach the backend — check it's running on port 8000.";
    plannerBtn.disabled = false;
    return;
  }

  plannerStatusLine.classList.remove('show');
  plannerBtn.disabled = false;
});

function renderPlannerReport(data, location) {
  document.getElementById('plannerLocationOut').textContent = location || '—';
  cropCardList.innerHTML = '';

  const recs = data.recommendations || [];
  recs.forEach(rec => {
    const card = document.createElement('div');
    card.className = 'crop-card';
    card.innerHTML = `
      <div class="crop-card-head">
        <div class="crop-card-title">
          <span class="crop-rank">#${rec.rank}</span>
          <span class="crop-name">${rec.crop}</span>
        </div>
        <span class="crop-cycle">${rec.growth_cycle}</span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="width:0%"></div></div>
      <span class="crop-score-value">${rec.suitability_score}% suitability</span>
      <p class="crop-reasoning">${rec.reasoning}</p>
    `;
    cropCardList.appendChild(card);
    requestAnimationFrame(() => {
      card.querySelector('.bar-fill').style.width = Math.min(rec.suitability_score, 100) + '%';
    });
  });

  plannerReport.classList.add('show');
}