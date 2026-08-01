  const imageInput = document.getElementById('imageInput');
  const dropzone   = document.getElementById('dropzone');
  const dzTitle    = document.getElementById('dzTitle');
  const slide      = document.getElementById('slide');
  const preview    = document.getElementById('preview');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const statusLine = document.getElementById('statusLine');
  const statusText = document.getElementById('statusText');
  const fileMeta   = document.getElementById('fileMeta');
  const report     = document.getElementById('report');

  // Static, plain-language treatment notes — no external API call needed.
  const RECOMMENDATIONS = {
    healthy: "No action needed. Keep up current watering and spacing to prevent future stress.",
    default: "Remove and destroy affected leaves. Avoid overhead watering, and apply a suitable fungicide/bactericide as per local agricultural guidance."
  };

  let specimenId = "";

  function newSpecimenId(){
    const d = new Date();
    const stamp = `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`;
    const rand = Math.floor(1000 + Math.random()*9000);
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

  function handleFile(file){
    specimenId = newSpecimenId();
    preview.src = URL.createObjectURL(file);
    slide.classList.add('show');
    dzTitle.textContent = file.name;
    fileMeta.textContent = `${specimenId} · ${(file.size/1024).toFixed(0)} KB`;
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

    try {
      const response = await fetch('http://127.0.0.1:8000/predict', { method: 'POST', body: formData });
      if (!response.ok) throw new Error('Backend error');
      const data = await response.json();
      renderReport(data);
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

  function renderReport(data){
    const rawName = (data.disease || 'Unknown').replace(/_/g, ' ').replace(/\s+/g,' ').trim();
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
        : (isHealthy ? RECOMMENDATIONS.healthy : RECOMMENDATIONS.default);

    requestAnimationFrame(() => {
      document.getElementById('confBar').style.width = Math.min(confidence,100) + '%';
    });

    report.classList.add('show');
  }