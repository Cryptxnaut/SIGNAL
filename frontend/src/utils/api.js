const BASE_URL = '';

export const uploadDataset = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Upload failed: ${err}`);
  }
  return res.json();
};

export const startAnalysis = async (datasetId, intent, depth, onEvent) => {
  const res = await fetch(`${BASE_URL}/api/analyse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, intent, depth }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Analysis failed: ${err}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const event = JSON.parse(trimmed);
        onEvent(event);
      } catch (e) {
        // skip malformed lines
      }
    }
  }

  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer.trim());
      onEvent(event);
    } catch (e) {
      // skip
    }
  }
};

export const getDataset = async (id) => {
  const res = await fetch(`${BASE_URL}/api/dataset/${id}`);
  if (!res.ok) throw new Error('Dataset not found');
  return res.json();
};

export const getFindings = async (id) => {
  const res = await fetch(`${BASE_URL}/api/findings/${id}`);
  if (!res.ok) throw new Error('Findings not found');
  return res.json();
};

export const getModel = async (id) => {
  const res = await fetch(`${BASE_URL}/api/model/${id}`);
  if (!res.ok) throw new Error('Model not found');
  return res.json();
};

export const getStress = async (id) => {
  const res = await fetch(`${BASE_URL}/api/stress/${id}`);
  if (!res.ok) throw new Error('Stress test not found');
  return res.json();
};

export const getReport = async (id) => {
  const res = await fetch(`${BASE_URL}/api/report/${id}`);
  if (!res.ok) throw new Error('Report not found');
  return res.json();
};

export const getHealth = async () => {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
};

export const getHardwareStatus = async () => {
  const res = await fetch(`${BASE_URL}/api/hardware/status`);
  if (!res.ok) throw new Error('Hardware status failed');
  return res.json();
};

export const streamConsultant = async (datasetId, message, history, onToken, onDone) => {
  const res = await fetch(`${BASE_URL}/api/consultant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, message, history }),
  });

  if (!res.ok) {
    throw new Error('Consultant request failed');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim();
        if (data === '[DONE]') {
          onDone && onDone();
          return;
        }
        try {
          const token = JSON.parse(data);
          onToken(token);
        } catch (e) {
          // skip
        }
      }
    }
  }

  onDone && onDone();
};
