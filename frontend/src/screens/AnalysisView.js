import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import NavBar from '../components/NavBar';
import ProgressFeed from '../components/ProgressFeed';
import FindingCard from '../components/FindingCard';
import ModelTab from '../components/ModelTab';
import StressTestTab from '../components/StressTestTab';
import ConsultantTab from '../components/ConsultantTab';
import ReportTab from '../components/ReportTab';
import { startAnalysis } from '../utils/api';

const NAV_ITEMS = [
  { key: 'overview', label: 'Overview', icon: '◎' },
  { key: 'findings', label: 'Findings', icon: '◈' },
  { key: 'model', label: 'Model', icon: '▣' },
  { key: 'stress', label: 'Stress Test', icon: '⚡' },
  { key: 'consultant', label: 'Consultant', icon: '✦' },
  { key: 'report', label: 'Report', icon: '⊞' },
];

const FINDING_TYPES = ['ALL', 'CORRELATION', 'ANOMALY', 'TREND', 'LEADING_INDICATOR', 'REGIME_CHANGE'];

export default function AnalysisView() {
  const { datasetId, tab: tabParam } = useParams();
  const activeTab = tabParam || 'overview';
  const navigate = useNavigate();
  const { state, dispatch } = useApp();
  const dataset = state.datasets[datasetId] || {};

  const [events, setEvents] = useState([]);
  const [progress, setProgress] = useState(0);
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const [findingFilter, setFindingFilter] = useState('ALL');
  const hasStartedRef = useRef(false);

  const status = dataset.status || 'pending';
  const isComplete = status === 'complete';
  const findings = dataset.findings || [];
  const model = dataset.model || {};
  const stressTest = dataset.stress_test || {};
  const report = {};
  const meta = dataset.meta || {};
  const depth = dataset.depth || 'deep';

  // Build report from dataset data
  const reportData = {
    dataset_name: meta.name,
    intent: dataset.intent,
    generated_at: new Date().toISOString(),
    schema_summary: dataset.schema_summary || null,
    quality: dataset.quality || null,
    findings: findings,
    model: model,
    stress_test: stressTest,
    executive_summary: dataset.executive_summary || null,
  };

  // Auto-start analysis if status is 'analysing' and not yet started
  useEffect(() => {
    if (
      status === 'analysing' &&
      !hasStartedRef.current &&
      dataset.intent
    ) {
      hasStartedRef.current = true;
      setAnalysisStarted(true);

      startAnalysis(
        datasetId,
        dataset.intent,
        dataset.depth || 'deep',
        (event) => {
          const timestamp = new Date().toLocaleTimeString();
          setEvents((prev) => [...prev, { ...event, timestamp }]);
          setProgress(event.progress || 0);

          if (event.stage === 'complete') {
            dispatch({
              type: 'UPDATE_DATASET_STATUS',
              payload: {
                id: datasetId,
                status: 'complete',
                findings: event.findings || [],
                model: event.model || {},
                stress_test: event.stress_test || {},
                quality: event.quality || {},
                depth: dataset.depth || 'deep',
              },
            });
            if (meta && event.quality) {
              dispatch({
                type: 'UPDATE_DATASET_STATUS',
                payload: {
                  id: datasetId,
                  meta: { ...meta, quality_score: event.quality?.overall_quality ?? null },
                },
              });
            }
          }
        }
      ).catch((err) => {
        dispatch({
          type: 'UPDATE_DATASET_STATUS',
          payload: { id: datasetId, status: 'error', error: err.message },
        });
        setEvents((prev) => [
          ...prev,
          { stage: 'error', message: `Error: ${err.message}`, progress: 0, timestamp: new Date().toLocaleTimeString() },
        ]);
      });
    }
  }, [datasetId, status, dataset.intent, dataset.depth]);

  const navigateTab = (key) => {
    navigate(`/analysis/${datasetId}/${key}`);
  };

  // Filter findings
  const filteredFindings =
    findingFilter === 'ALL'
      ? findings
      : findings.filter(
          (f) => f.type?.toLowerCase() === findingFilter.toLowerCase()
        );

  if (!datasetId || !state.datasets[datasetId]) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        <NavBar />
        <div
          style={{
            paddingTop: 80,
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: 14,
          }}
        >
          Dataset not found. Go back to{' '}
          <span
            style={{ color: 'var(--accent-blue)', cursor: 'pointer' }}
            onClick={() => navigate('/workspace')}
          >
            workspace
          </span>.
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)', display: 'flex', flexDirection: 'column' }}>
      <NavBar />

      <div style={{ display: 'flex', flex: 1, paddingTop: 48, minHeight: 0 }}>
        {/* Sidebar */}
        <aside
          style={{
            width: 220,
            flexShrink: 0,
            backgroundColor: 'var(--bg-surface)',
            borderRight: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            height: 'calc(100vh - 48px)',
            position: 'sticky',
            top: 48,
            overflowY: 'auto',
          }}
        >
          {/* Dataset info */}
          <div style={{ padding: '16px 16px 12px' }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, wordBreak: 'break-all' }}>
              {meta.name || 'Dataset'}
            </div>
            <span
              style={{
                fontSize: 10,
                fontFamily: 'var(--font-mono)',
                padding: '1px 5px',
                borderRadius: 3,
                border: '1px solid var(--text-muted)',
                color: 'var(--text-muted)',
              }}
            >
              {meta.source || 'UPLOADED'}
            </span>
          </div>

          <div style={{ height: 1, backgroundColor: 'var(--border)', margin: '0 16px' }} />

          {/* Nav items */}
          <nav style={{ padding: '8px 0', flex: 1 }}>
            {NAV_ITEMS.map((item) => {
              const isActive = activeTab === item.key;
              return (
                <div
                  key={item.key}
                  onClick={() => navigateTab(item.key)}
                  style={{
                    height: 36,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '0 16px',
                    cursor: 'pointer',
                    borderLeft: isActive ? '2px solid var(--accent-blue)' : '2px solid transparent',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontSize: 13,
                    transition: 'all 0.1s',
                    backgroundColor: isActive ? '#3B82F608' : 'transparent',
                  }}
                >
                  <span style={{ fontSize: 14, width: 16, textAlign: 'center', flexShrink: 0 }}>
                    {item.icon}
                  </span>
                  {item.label}
                </div>
              );
            })}
          </nav>

          {/* Bottom stats */}
          <div
            style={{
              padding: 14,
              borderTop: '1px solid var(--border)',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              color: 'var(--text-muted)',
              lineHeight: 2,
            }}
          >
            <div>Rows: {(meta.rows || 0).toLocaleString()}</div>
            <div>Columns: {meta.columns || 0}</div>
            <div>
              Quality:{' '}
              {meta.quality_score != null
                ? `${Math.round(meta.quality_score * 100)}%`
                : '—'}
            </div>
          </div>
        </aside>

        {/* Main panel */}
        <main
          style={{
            flex: 1,
            padding: 24,
            overflowY: 'auto',
            height: 'calc(100vh - 48px)',
            minWidth: 0,
          }}
        >
          {/* Overview tab */}
          {activeTab === 'overview' && (
            <div>
              {!isComplete && (
                <>
                  <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 16 }}>
                    {status === 'analysing' ? 'Analysis in Progress' : 'Waiting to start'}
                  </h2>
                  <ProgressFeed
                    events={events}
                    progress={progress}
                    isComplete={isComplete}
                  />
                </>
              )}

              {isComplete && (
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 16 }}>
                    Analysis Complete
                  </h2>
                  {/* Summary card */}
                  <div
                    style={{
                      backgroundColor: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                      padding: 20,
                      marginBottom: 20,
                      display: 'flex',
                      gap: 24,
                      flexWrap: 'wrap',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14 }}>
                      <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
                        {findings.length}
                      </span>{' '}
                      <span style={{ color: 'var(--text-muted)' }}>findings</span>
                    </div>
                    {model.metric_name && (
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Model </span>
                        <span style={{ color: 'var(--accent-green)' }}>
                          {model.metric_name}: {(model.metric_value || 0).toFixed(3)}
                        </span>
                      </div>
                    )}
                    {stressTest.edge_cases && (
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14 }}>
                        <span style={{ color: 'var(--accent-amber)', fontWeight: 600 }}>
                          {stressTest.edge_cases.length}
                        </span>{' '}
                        <span style={{ color: 'var(--text-muted)' }}>edge cases</span>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => navigateTab('findings')}
                    style={{
                      padding: '10px 20px',
                      borderRadius: 6,
                      backgroundColor: 'var(--accent-blue)',
                      color: '#fff',
                      fontWeight: 600,
                      fontSize: 13,
                      cursor: 'pointer',
                      border: 'none',
                    }}
                  >
                    View Findings
                  </button>

                  {/* Show log of events if we have them */}
                  {events.length > 0 && (
                    <div style={{ marginTop: 24 }}>
                      <ProgressFeed
                        events={events}
                        progress={100}
                        isComplete={true}
                      />
                    </div>
                  )}
                </div>
              )}

              {status === 'error' && (
                <div
                  style={{
                    padding: 20,
                    backgroundColor: '#EF444410',
                    border: '1px solid var(--accent-red)',
                    borderRadius: 8,
                    color: 'var(--accent-red)',
                  }}
                >
                  Analysis failed: {dataset.error || 'Unknown error'}
                </div>
              )}
            </div>
          )}

          {/* Findings tab */}
          {activeTab === 'findings' && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 16 }}>Findings</h2>

              {/* Filter bar */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                {FINDING_TYPES.map((ft) => (
                  <button
                    key={ft}
                    onClick={() => setFindingFilter(ft)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: 4,
                      border: `1px solid ${findingFilter === ft ? 'var(--accent-blue)' : 'var(--border)'}`,
                      backgroundColor:
                        findingFilter === ft ? 'var(--accent-blue)' : 'var(--bg-surface)',
                      color:
                        findingFilter === ft ? '#fff' : 'var(--text-secondary)',
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    {ft}
                  </button>
                ))}
              </div>

              {filteredFindings.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: '32px 0', textAlign: 'center' }}>
                  {findings.length === 0
                    ? 'No findings yet. Complete an analysis first.'
                    : 'No findings match this filter.'}
                </div>
              ) : (
                filteredFindings.map((finding, i) => (
                  <FindingCard key={i} finding={finding} />
                ))
              )}
            </div>
          )}

          {/* Model tab */}
          {activeTab === 'model' && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 20 }}>Model</h2>
              <ModelTab model={model} />
            </div>
          )}

          {/* Stress test tab */}
          {activeTab === 'stress' && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 20 }}>Stress Test</h2>
              <StressTestTab
                stressTest={stressTest}
                depth={depth}
                datasetId={datasetId}
              />
            </div>
          )}

          {/* Consultant tab */}
          {activeTab === 'consultant' && (
            <div
              style={{
                height: 'calc(100vh - 48px - 48px - 48px)',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 16 }}>AI Consultant</h2>
              <div style={{ flex: 1, minHeight: 0 }}>
                <ConsultantTab datasetId={datasetId} />
              </div>
            </div>
          )}

          {/* Report tab */}
          {activeTab === 'report' && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: 20 }}>Report</h2>
              <ReportTab report={reportData} />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
