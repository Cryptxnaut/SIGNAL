import React from 'react';
import { useNavigate } from 'react-router-dom';

function qualityColor(score) {
  if (score === null || score === undefined) return 'var(--text-muted)';
  if (score > 0.7) return 'var(--accent-green)';
  if (score > 0.4) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}

function sourceBadge(source) {
  const styles = {
    UPLOADED: { border: '1px solid var(--text-muted)', color: 'var(--text-muted)', bg: 'transparent' },
    LIVE: { border: 'none', color: '#fff', bg: 'var(--accent-blue)' },
    PUBLIC: { border: 'none', color: '#fff', bg: 'var(--accent-purple)' },
  };
  const s = styles[source] || styles.UPLOADED;
  return (
    <span
      style={{
        fontSize: 10,
        fontFamily: 'var(--font-mono)',
        padding: '2px 6px',
        borderRadius: 3,
        border: s.border,
        color: s.color,
        backgroundColor: s.bg,
        letterSpacing: '0.05em',
      }}
    >
      {source || 'UPLOADED'}
    </span>
  );
}

export default function DatasetCard({ datasetId, dataset }) {
  const navigate = useNavigate();
  const [hovered, setHovered] = React.useState(false);

  const meta = dataset?.meta || {};
  const quality = meta.quality_score;
  const uploadedAt = meta.uploaded_at
    ? new Date(meta.uploaded_at).toLocaleString()
    : '';

  return (
    <div
      onClick={() => navigate(`/analysis/${datasetId}`)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        backgroundColor: 'var(--bg-surface)',
        border: `1px solid ${hovered ? 'var(--accent-blue)' : 'var(--border)'}`,
        borderRadius: 8,
        padding: 16,
        cursor: 'pointer',
        transition: 'border-color 0.15s ease',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      {/* Top row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <span style={{ fontWeight: 500, fontSize: 14, color: 'var(--text-primary)', wordBreak: 'break-all' }}>
          {meta.name || 'Untitled Dataset'}
        </span>
        {sourceBadge(meta.source)}
      </div>

      {/* Middle row */}
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          color: 'var(--text-muted)',
        }}
      >
        {meta.rows?.toLocaleString() || '—'} rows · {meta.columns || '—'} columns
      </div>

      {/* Health bar */}
      <div>
        <div
          style={{
            height: 3,
            width: '100%',
            backgroundColor: 'var(--border)',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: quality != null ? `${Math.round(quality * 100)}%` : '0%',
              backgroundColor: qualityColor(quality),
              borderRadius: 2,
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>

      {/* Bottom: timestamp */}
      {uploadedAt && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {uploadedAt}
        </div>
      )}
    </div>
  );
}
