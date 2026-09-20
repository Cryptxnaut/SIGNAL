import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import NavBar from '../components/NavBar';
import { uploadDataset, startAnalysis } from '../utils/api';

function GameForgeCard({ onDatasetCreated }) {
  const [status, setStatus] = useState('idle'); // idle | loading | done | error
  const [msg, setMsg] = useState('');

  const importData = async () => {
    setStatus('loading');
    setMsg('');
    try {
      const resp = await fetch('http://localhost:8000/api/gameforge/dataset', { method: 'POST' });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'No events recorded yet — play GameForge first.');
      }
      const data = await resp.json();
      setStatus('done');
      setMsg(`${data.rows} events imported`);
      setTimeout(() => onDatasetCreated(data.dataset_id), 600);
    } catch (e) {
      setStatus('error');
      setMsg(e.message);
    }
  };

  return (
    <div
      style={{
        border: `1px solid ${status === 'done' ? 'var(--accent-green)' : status === 'error' ? 'var(--accent-red)' : 'var(--accent-blue)'}`,
        borderRadius: 10,
        padding: 20,
        cursor: status === 'loading' ? 'wait' : 'pointer',
        backgroundColor: 'var(--bg-surface)',
        transition: 'border-color 0.15s',
      }}
      onClick={status === 'idle' || status === 'error' ? importData : undefined}
    >
      <div style={{ fontSize: 28, marginBottom: 10 }}>🎮</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>GameForge</div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
        Import live player event data
      </div>
      <div style={{ fontSize: 12, color: status === 'error' ? 'var(--accent-red)' : status === 'done' ? 'var(--accent-green)' : 'var(--text-muted)' }}>
        {status === 'idle' && 'Click to pull events from GameForge'}
        {status === 'loading' && 'Importing…'}
        {status === 'done' && `✓ ${msg}`}
        {status === 'error' && msg}
      </div>
    </div>
  );
}

// Curated public datasets — Voloridge challenge + Wolfram Data Repository
const PUBLIC_DATASETS = [
  // ── Voloridge challenge datasets ──
  {
    category: 'Climate',
    name: 'NOAA ISD Sample — Global Weather Stations',
    desc: 'Hourly surface observations: temp, pressure, wind, precipitation',
    rows: '~50k',
    url: 'https://voloridge-hack-mit-2026.s3.us-east-1.amazonaws.com/noaa-isd-sample.csv',
    tag: 'VOLORIDGE',
  },
  {
    category: 'Transportation',
    name: 'NYC Taxi Trips — Jan 2024',
    desc: 'Yellow cab pickup/dropoff locations, fares, distances, durations',
    rows: '~2.9M',
    url: 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet',
    tag: 'VOLORIDGE',
  },
  {
    category: 'Air Quality',
    name: 'OpenAQ — Global Air Quality',
    desc: 'PM2.5, NO2, O3, CO measurements from government monitoring stations worldwide',
    rows: '~50k',
    url: 'https://voloridge-hack-mit-2026.s3.us-east-1.amazonaws.com/openaq-sample.csv',
    tag: 'VOLORIDGE',
  },
  {
    category: 'Energy',
    name: 'PUDL — US Electricity Generation',
    desc: 'EIA power plant generation, capacity, fuel consumption, emissions',
    rows: '~50k',
    url: 'https://voloridge-hack-mit-2026.s3.us-east-1.amazonaws.com/pudl-sample.csv',
    tag: 'VOLORIDGE',
  },
  // ── Wolfram Data Repository ──
  {
    category: 'Economics',
    name: 'Country Economic Indicators',
    desc: 'GDP, inflation, unemployment, trade balance across 200+ countries',
    rows: '~5k',
    url: 'https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv',
    tag: 'WOLFRAM',
  },
  {
    category: 'Climate',
    name: 'Global Surface Temperature Anomalies',
    desc: 'NASA GISS monthly land+ocean temperature anomalies since 1880',
    rows: '~1.7k',
    url: 'https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv',
    tag: 'WOLFRAM',
  },
  {
    category: 'Healthcare',
    name: 'WHO Global Health Statistics',
    desc: 'Life expectancy, mortality rates, disease burden by country and year',
    rows: '~10k',
    url: 'https://raw.githubusercontent.com/datasets/country-list/main/data.csv',
    tag: 'WOLFRAM',
  },
  {
    category: 'Economics',
    name: 'World Bank — S&P Global Indices',
    desc: 'Daily S&P 500 closing prices and volume since 1927',
    rows: '~24k',
    url: 'https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/all_stocks_5yr.csv',
    tag: 'WOLFRAM',
  },
];

function PublicDatasetCard({ onDatasetCreated }) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('All');
  const [loading, setLoading] = useState(null); // dataset name loading
  const [error, setError] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [customName, setCustomName] = useState('');

  const categories = ['All', ...new Set(PUBLIC_DATASETS.map(d => d.category))];
  const visible = filter === 'All' ? PUBLIC_DATASETS : PUBLIC_DATASETS.filter(d => d.category === filter);

  const load = async (url, name) => {
    setLoading(name);
    setError('');
    try {
      const resp = await fetch('/api/load_url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, name }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to load dataset');
      }
      const data = await resp.json();
      onDatasetCreated(data.dataset_id);
    } catch (e) {
      setError(e.message);
      setLoading(null);
    }
  };

  const tagColor = (tag) => tag === 'VOLORIDGE' ? 'var(--accent-blue)' : 'var(--accent-purple)';

  return (
    <div
      style={{
        border: `1px solid ${open ? 'var(--accent-purple)' : 'var(--border)'}`,
        borderRadius: 10,
        padding: 20,
        backgroundColor: 'var(--bg-surface)',
        transition: 'border-color 0.15s',
        cursor: open ? 'default' : 'pointer',
        gridColumn: open ? 'span 2' : undefined,
      }}
      onClick={() => !open && setOpen(true)}
    >
      <div style={{ fontSize: 28, marginBottom: 10 }}>🌐</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Public Datasets</div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: open ? 16 : 0 }}>
        Voloridge challenge · Wolfram Data Repository
      </div>

      {open && (
        <div onClick={e => e.stopPropagation()}>
          {/* Category filter */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                style={{
                  padding: '3px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
                  border: `1px solid ${filter === cat ? 'var(--accent-purple)' : 'var(--border)'}`,
                  background: filter === cat ? 'var(--accent-purple)' : 'var(--bg-primary)',
                  color: filter === cat ? '#fff' : 'var(--text-secondary)',
                }}
              >{cat}</button>
            ))}
          </div>

          {/* Dataset list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {visible.map(ds => (
              <div
                key={ds.name}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 12px', borderRadius: 6,
                  border: '1px solid var(--border)',
                  background: 'var(--bg-primary)',
                  opacity: loading && loading !== ds.name ? 0.5 : 1,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{ds.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 5px', borderRadius: 3,
                      background: tagColor(ds.tag), color: '#fff', fontWeight: 700, letterSpacing: '0.05em',
                    }}>{ds.tag}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{ds.desc}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'monospace' }}>{ds.category} · {ds.rows} rows</div>
                </div>
                <button
                  disabled={!!loading}
                  onClick={() => load(ds.url, ds.name)}
                  style={{
                    padding: '6px 14px', borderRadius: 6, fontSize: 12, cursor: loading ? 'wait' : 'pointer',
                    border: '1px solid var(--accent-purple)', background: 'transparent',
                    color: 'var(--accent-purple)', flexShrink: 0, fontWeight: 500,
                  }}
                >
                  {loading === ds.name ? 'Loading…' : 'Load'}
                </button>
              </div>
            ))}
          </div>

          {/* Custom URL */}
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>Or load any CSV / Parquet URL (Wolfram, S3, etc.)</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                placeholder="Dataset name"
                value={customName}
                onChange={e => setCustomName(e.target.value)}
                style={{
                  width: 140, padding: '6px 10px', borderRadius: 6, fontSize: 12,
                  border: '1px solid var(--border)', background: 'var(--bg-primary)', color: 'var(--text-primary)',
                }}
              />
              <input
                placeholder="https://..."
                value={customUrl}
                onChange={e => setCustomUrl(e.target.value)}
                style={{
                  flex: 1, padding: '6px 10px', borderRadius: 6, fontSize: 12,
                  border: '1px solid var(--border)', background: 'var(--bg-primary)', color: 'var(--text-primary)',
                }}
              />
              <button
                disabled={!customUrl || !!loading}
                onClick={() => load(customUrl, customName || customUrl.split('/').pop() || 'dataset')}
                style={{
                  padding: '6px 14px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                  border: '1px solid var(--accent-blue)', background: 'var(--accent-blue)',
                  color: '#fff', fontWeight: 500, flexShrink: 0,
                }}
              >Load URL</button>
            </div>
          </div>

          {error && <div style={{ marginTop: 8, fontSize: 12, color: 'var(--accent-red)' }}>{error}</div>}
        </div>
      )}
    </div>
  );
}

const DEPTH_OPTIONS = [
  {
    key: 'quick',
    title: 'Quick Scan',
    time: '~2 minutes',
    desc: 'Schema analysis, correlation sweep, top findings. No model training.',
    recommended: false,
  },
  {
    key: 'deep',
    title: 'Deep Analysis',
    time: '~8 minutes',
    desc: 'Full statistical suite, model training, ranked findings.',
    recommended: true,
  },
  {
    key: 'stress',
    title: 'Full Stress Test',
    time: '~20 minutes',
    desc: 'Everything above plus adversarial testing.',
    recommended: false,
  },
];

const INTENT_CHIPS = [
  'Find leading indicators of X in this data',
  'Detect anomalies and explain what\'s driving them',
  'Identify the most significant trends and what\'s causing them',
];

function Stepper({ current }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
      {[1, 2, 3].map((step) => (
        <React.Fragment key={step}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              border: `2px solid ${step <= current ? 'var(--accent-blue)' : 'var(--border)'}`,
              backgroundColor: step < current ? 'var(--accent-blue)' : 'transparent',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              fontWeight: 600,
              color: step <= current ? (step < current ? '#fff' : 'var(--accent-blue)') : 'var(--text-muted)',
              transition: 'all 0.2s',
            }}
          >
            {step}
          </div>
          {step < 3 && (
            <div
              style={{
                flex: 1,
                height: 2,
                backgroundColor: step < current ? 'var(--accent-blue)' : 'var(--border)',
                maxWidth: 80,
                transition: 'background-color 0.2s',
              }}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function AddDataset() {
  const navigate = useNavigate();
  const { dispatch } = useApp();
  const [step, setStep] = useState(1);
  const [datasetId, setDatasetId] = useState(null);
  const [datasetMeta, setDatasetMeta] = useState(null);
  const [intent, setIntent] = useState('');
  const [depth, setDepth] = useState('deep');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [showDropZone, setShowDropZone] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadError('');
    try {
      const result = await uploadDataset(file);
      setDatasetId(result.dataset_id);
      setDatasetMeta(result);
      dispatch({
        type: 'SET_DATASET',
        payload: {
          id: result.dataset_id,
          data: {
            meta: {
              name: result.name,
              rows: result.rows,
              columns: result.columns,
              source: 'UPLOADED',
              quality_score: null,
            },
          },
        },
      });
      setStep(2);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleBeginAnalysis = () => {
    if (!intent.trim() || !datasetId) return;

    dispatch({
      type: 'UPDATE_DATASET_STATUS',
      payload: {
        id: datasetId,
        status: 'analysing',
        intent,
        depth,
        events: [],
        progress: 0,
      },
    });

    navigate(`/analysis/${datasetId}`);

    // Start analysis in background
    startAnalysis(datasetId, intent, depth, (event) => {
      dispatch({
        type: 'UPDATE_DATASET_STATUS',
        payload: {
          id: datasetId,
          progress: event.progress,
          lastEvent: event,
        },
      });
      if (event.stage === 'complete') {
        dispatch({
          type: 'UPDATE_DATASET_STATUS',
          payload: {
            id: datasetId,
            status: 'complete',
            findings: event.findings,
            model: event.model,
            stress_test: event.stress_test,
            quality: event.quality,
            depth,
          },
        });
        dispatch({
          type: 'UPDATE_DATASET_STATUS',
          payload: {
            id: datasetId,
            meta: {
              name: datasetMeta?.name || datasetId,
              rows: datasetMeta?.rows,
              columns: datasetMeta?.columns,
              source: 'UPLOADED',
              quality_score: event.quality?.overall_quality ?? null,
            },
          },
        });
      }
    }).catch((err) => {
      dispatch({
        type: 'UPDATE_DATASET_STATUS',
        payload: { id: datasetId, status: 'error', error: err.message },
      });
    });
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <NavBar />
      <div
        style={{
          paddingTop: 72,
          maxWidth: 800,
          margin: '0 auto',
          padding: '72px 24px 48px',
        }}
      >
        <Stepper current={step} />

        {/* Step 1 — Source */}
        {step === 1 && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 500, marginBottom: 6 }}>
              Choose a data source
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 28, fontSize: 14 }}>
              Select how you want to bring data into SIGNAL.
            </p>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 16,
              }}
            >
              {/* Upload card */}
              <div
                style={{
                  border: `1px solid ${showDropZone ? 'var(--accent-blue)' : 'var(--border)'}`,
                  borderRadius: 10,
                  padding: 20,
                  cursor: 'pointer',
                  transition: 'border-color 0.15s',
                  backgroundColor: 'var(--bg-surface)',
                }}
                onClick={() => {
                  setShowDropZone(true);
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 10 }}>↑</div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Upload File</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  CSV or Parquet, up to 500MB
                </div>

                {showDropZone && (
                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={handleDrop}
                    onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                    style={{
                      marginTop: 14,
                      border: `2px dashed ${dragging ? 'var(--accent-blue)' : 'var(--border)'}`,
                      borderRadius: 6,
                      padding: 20,
                      textAlign: 'center',
                      color: 'var(--text-muted)',
                      fontSize: 12,
                      backgroundColor: dragging ? '#3B82F610' : 'var(--bg-primary)',
                      transition: 'all 0.15s',
                      cursor: 'pointer',
                    }}
                  >
                    {uploading ? (
                      <span className="pulse">Uploading...</span>
                    ) : (
                      'Drop file here or click to browse'
                    )}
                  </div>
                )}

                {uploadError && (
                  <div style={{ marginTop: 8, color: 'var(--accent-red)', fontSize: 12 }}>
                    {uploadError}
                  </div>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.parquet"
                  style={{ display: 'none' }}
                  onChange={(e) => handleFileSelect(e.target.files[0])}
                />
              </div>

              {/* Hardware card */}
              <div
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: 10,
                  padding: 20,
                  backgroundColor: 'var(--bg-surface)',
                  opacity: 0.7,
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 10 }}>〜</div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Live Hardware</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  nRF54LM20 over BLE
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Not detected — connect nRF54LM20 DK
                </div>
              </div>

              {/* Public dataset card */}
              <PublicDatasetCard onDatasetCreated={(id) => { setDatasetId(id); setStep(2); }} />

              {/* GameForge card */}
              <GameForgeCard onDatasetCreated={(id) => { setDatasetId(id); setStep(2); }} />
            </div>
          </div>
        )}

        {/* Step 2 — Intent */}
        {step === 2 && (
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            {/* Left: textarea */}
            <div style={{ flex: '1 1 380px', minWidth: 0 }}>
              <h2 style={{ fontSize: 22, fontWeight: 500, marginBottom: 6 }}>
                What are you trying to understand?
              </h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: 16, fontSize: 14 }}>
                Describe your analytical goal. The more specific, the better.
              </p>

              <textarea
                autoFocus
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                placeholder="e.g. Find early warning signals for extreme weather events 48 hours before they occur"
                rows={5}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: '12px 14px',
                  color: 'var(--text-primary)',
                  fontSize: 14,
                  resize: 'vertical',
                  outline: 'none',
                  lineHeight: 1.6,
                  marginBottom: 12,
                }}
              />

              {/* Chips */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
                {INTENT_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => setIntent(chip)}
                    style={{
                      padding: '5px 10px',
                      borderRadius: 12,
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--bg-surface)',
                      color: 'var(--text-secondary)',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    {chip}
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  onClick={() => setStep(1)}
                  style={{
                    padding: '10px 18px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    backgroundColor: 'transparent',
                    color: 'var(--text-secondary)',
                    fontSize: 13,
                    cursor: 'pointer',
                  }}
                >
                  Back
                </button>
                <button
                  onClick={() => intent.trim() && setStep(3)}
                  disabled={!intent.trim()}
                  style={{
                    padding: '10px 20px',
                    borderRadius: 6,
                    backgroundColor: intent.trim() ? 'var(--accent-blue)' : 'var(--border)',
                    color: intent.trim() ? '#fff' : 'var(--text-muted)',
                    fontWeight: 600,
                    fontSize: 13,
                    cursor: intent.trim() ? 'pointer' : 'not-allowed',
                    border: 'none',
                  }}
                >
                  Next
                </button>
              </div>
            </div>

            {/* Right: preview */}
            {datasetMeta && (
              <div
                style={{
                  flex: '0 0 220px',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: 16,
                  alignSelf: 'flex-start',
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>
                  {datasetMeta.name}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
                  {(datasetMeta.rows || 0).toLocaleString()} rows · {datasetMeta.columns || 0} columns
                </div>
                {datasetMeta.preview && datasetMeta.preview.length > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Columns:</div>
                    {Object.keys(datasetMeta.preview[0]).map((col) => (
                      <div
                        key={col}
                        style={{
                          fontSize: 11,
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--text-secondary)',
                          padding: '2px 0',
                          borderBottom: '1px solid var(--border)',
                        }}
                      >
                        {col}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Step 3 — Depth */}
        {step === 3 && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 500, marginBottom: 6 }}>
              Choose analysis depth
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24, fontSize: 14 }}>
              More depth = more insight, but takes longer.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
              {DEPTH_OPTIONS.map((opt) => (
                <div
                  key={opt.key}
                  onClick={() => setDepth(opt.key)}
                  style={{
                    border: `2px solid ${depth === opt.key ? 'var(--accent-blue)' : 'var(--border)'}`,
                    borderRadius: 10,
                    padding: 16,
                    cursor: 'pointer',
                    backgroundColor: depth === opt.key ? '#3B82F608' : 'var(--bg-surface)',
                    transition: 'all 0.15s',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                  }}
                >
                  <div
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      border: `2px solid ${depth === opt.key ? 'var(--accent-blue)' : 'var(--border)'}`,
                      backgroundColor: depth === opt.key ? 'var(--accent-blue)' : 'transparent',
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{opt.title}</span>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {opt.time}
                      </span>
                      {opt.recommended && (
                        <span
                          style={{
                            fontSize: 10,
                            padding: '1px 6px',
                            borderRadius: 3,
                            backgroundColor: 'var(--accent-blue)',
                            color: '#fff',
                            fontWeight: 600,
                          }}
                        >
                          RECOMMENDED
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{opt.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={() => setStep(2)}
                style={{
                  padding: '10px 18px',
                  borderRadius: 6,
                  border: '1px solid var(--border)',
                  backgroundColor: 'transparent',
                  color: 'var(--text-secondary)',
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                Back
              </button>
              <button
                onClick={handleBeginAnalysis}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  borderRadius: 6,
                  backgroundColor: 'var(--accent-blue)',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: 'pointer',
                  border: 'none',
                }}
              >
                Begin Analysis
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
