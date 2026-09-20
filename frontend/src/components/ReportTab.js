import React from 'react';

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <h2
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: '#111',
          marginBottom: 12,
          paddingBottom: 8,
          borderBottom: '2px solid #e5e7eb',
        }}
      >
        {title}
      </h2>
      {children}
    </div>
  );
}

export default function ReportTab({ report }) {
  if (!report || Object.keys(report).length === 0) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
        Report not yet generated. Complete an analysis first.
      </div>
    );
  }

  const handlePrint = () => window.print();

  const handleCopyLink = () => {
    navigator.clipboard
      .writeText(window.location.href)
      .then(() => alert('Link copied!'))
      .catch(() => alert('Copy failed — please copy the URL manually.'));
  };

  return (
    <div>
      {/* Action buttons */}
      <div
        style={{
          display: 'flex',
          gap: 10,
          marginBottom: 24,
        }}
      >
        <button
          onClick={handlePrint}
          style={{
            padding: '8px 16px',
            borderRadius: 6,
            backgroundColor: 'var(--accent-blue)',
            color: '#fff',
            fontWeight: 600,
            fontSize: 13,
            cursor: 'pointer',
            border: 'none',
          }}
        >
          Export PDF
        </button>
        <button
          onClick={handleCopyLink}
          style={{
            padding: '8px 16px',
            borderRadius: 6,
            backgroundColor: 'var(--bg-surface-raised)',
            color: 'var(--text-secondary)',
            fontWeight: 500,
            fontSize: 13,
            cursor: 'pointer',
            border: '1px solid var(--border)',
          }}
        >
          Copy Link
        </button>
      </div>

      {/* Report document */}
      <div
        id="report-document"
        style={{
          backgroundColor: '#ffffff',
          color: '#111',
          borderRadius: 8,
          padding: 40,
          maxWidth: 800,
          boxShadow: '0 2px 16px rgba(0,0,0,0.3)',
          fontFamily: 'Inter, sans-serif',
        }}
      >
        {/* Cover */}
        <div style={{ marginBottom: 40, borderBottom: '3px solid #111', paddingBottom: 24 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.15em', color: '#666', marginBottom: 8 }}>
            SIGNAL · DATA ANALYSIS REPORT
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 600, color: '#111', marginBottom: 8 }}>
            {report.dataset_name || 'Analysis Report'}
          </h1>
          <div style={{ fontSize: 13, color: '#666' }}>
            Generated {report.generated_at ? new Date(report.generated_at).toLocaleString() : '—'}
          </div>
          {report.intent && (
            <div
              style={{
                marginTop: 12,
                padding: 12,
                backgroundColor: '#f3f4f6',
                borderRadius: 6,
                fontSize: 13,
                color: '#374151',
                fontStyle: 'italic',
              }}
            >
              Intent: "{report.intent}"
            </div>
          )}
        </div>

        {/* Executive Summary */}
        {report.executive_summary && (
          <Section title="Executive Summary">
            <p style={{ fontSize: 14, lineHeight: 1.7, color: '#374151' }}>
              {report.executive_summary}
            </p>
          </Section>
        )}

        {/* Dataset Stats */}
        {report.schema_summary && (
          <Section title="Dataset Overview">
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              {[
                ['Rows', report.schema_summary.n_rows?.toLocaleString()],
                ['Columns', report.schema_summary.n_columns],
                ['Time Series', report.schema_summary.n_time_series],
                ['Quality', report.quality ? `${Math.round(report.quality.overall_quality * 100)}%` : '—'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  style={{
                    flex: '1 0 120px',
                    padding: 16,
                    backgroundColor: '#f9fafb',
                    borderRadius: 6,
                    border: '1px solid #e5e7eb',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: 11, color: '#9ca3af', letterSpacing: '0.08em', marginBottom: 4 }}>
                    {label}
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 600, color: '#111' }}>
                    {value ?? '—'}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Top Findings */}
        {report.findings && report.findings.length > 0 && (
          <Section title="Top Findings">
            {report.findings.slice(0, 5).map((f, i) => (
              <div
                key={i}
                style={{
                  padding: 14,
                  marginBottom: 10,
                  backgroundColor: '#f9fafb',
                  borderRadius: 6,
                  border: '1px solid #e5e7eb',
                  borderLeft: '3px solid #3b82f6',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
                  {i + 1}. {f.name}
                </div>
                {f.explanation && (
                  <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>
                    {f.explanation}
                  </div>
                )}
                <div style={{ marginTop: 6, fontSize: 11, color: '#9ca3af', fontFamily: 'monospace' }}>
                  type: {f.type} · significance: {(f.significance_score || 0).toFixed(3)}
                </div>
              </div>
            ))}
          </Section>
        )}

        {/* Model Card */}
        {report.model && report.model.model_type && report.model.model_type !== 'none' && (
          <Section title="Model Card">
            <div
              style={{
                padding: 16,
                backgroundColor: '#f9fafb',
                borderRadius: 6,
                border: '1px solid #e5e7eb',
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <tbody>
                  {[
                    ['Model Type', report.model.model_type],
                    ['Target Column', report.model.target_column],
                    [report.model.metric_name || 'Metric', (report.model.metric_value || 0).toFixed(4)],
                    ['Training Rows', report.model.training_rows?.toLocaleString()],
                    ['Training Time', `${report.model.training_time_ms} ms`],
                    ['Trained On', report.model.trained_on || 'Local'],
                  ].map(([label, value]) => (
                    <tr key={label} style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <td style={{ padding: '8px 4px', color: '#6b7280', width: 160 }}>{label}</td>
                      <td style={{ padding: '8px 4px', fontWeight: 500, fontFamily: 'monospace' }}>
                        {value ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        )}

        {/* Stress Test Summary */}
        {report.stress_test && report.stress_test.edge_cases?.length > 0 && (
          <Section title="Stress Test Summary">
            {report.stress_test.edge_cases.map((ec, i) => (
              <div
                key={i}
                style={{
                  padding: 12,
                  marginBottom: 8,
                  backgroundColor: '#fef2f2',
                  borderRadius: 6,
                  border: '1px solid #fecaca',
                  borderLeft: '3px solid #ef4444',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13, color: '#dc2626', marginBottom: 4 }}>
                  {ec.title}
                </div>
                <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>
                  {ec.description}
                </div>
              </div>
            ))}
          </Section>
        )}
      </div>
    </div>
  );
}
