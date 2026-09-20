import React, { useState } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

const TYPE_COLORS = {
  correlation: 'var(--accent-blue)',
  anomaly: 'var(--accent-red)',
  trend: 'var(--accent-green)',
  leading_indicator: 'var(--accent-purple)',
  regime_change: 'var(--accent-amber)',
};

const TYPE_LABELS = {
  correlation: 'CORRELATION',
  anomaly: 'ANOMALY',
  trend: 'TREND',
  leading_indicator: 'LEADING INDICATOR',
  regime_change: 'REGIME CHANGE',
};

function PValueBadge({ pValue }) {
  if (pValue === null || pValue === undefined) return null;
  let color = 'var(--text-muted)';
  let border = '1px solid var(--border)';
  if (pValue < 0.01) { color = 'var(--accent-green)'; border = '1px solid var(--accent-green)'; }
  else if (pValue < 0.05) { color = 'var(--accent-amber)'; border = '1px solid var(--accent-amber)'; }

  return (
    <span
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        padding: '2px 5px',
        borderRadius: 3,
        border,
        color,
      }}
    >
      p={pValue.toExponential(2)}
    </span>
  );
}

function buildSparklineData(finding) {
  const type = finding.type;
  if (type === 'correlation' && finding.correlations) {
    return finding.correlations.map((c, i) => ({
      v: Math.abs(c.pearson_r || 0),
    }));
  }
  if (type === 'anomaly' && finding.anomalous_rows) {
    return finding.anomalous_rows.slice(0, 20).map((r) => ({
      v: Math.abs(r.score || 0),
    }));
  }
  if (type === 'regime_change' && finding.changepoints) {
    return finding.changepoints.slice(0, 20).map((c) => ({
      v: c.magnitude || 0,
    }));
  }
  // Default: generate from significance score
  return Array.from({ length: 10 }, (_, i) => ({
    v: (finding.significance_score || 0.5) * Math.sin(i * 0.7 + 1) * 0.5 + 0.5,
  }));
}

export default function FindingCard({ finding }) {
  const [expanded, setExpanded] = useState(false);
  const type = finding.type || 'correlation';
  const typeColor = TYPE_COLORS[type] || 'var(--text-muted)';
  const typeLabel = TYPE_LABELS[type] || type.toUpperCase();
  const sparkData = buildSparklineData(finding);

  // Get primary p-value
  let pValue = null;
  if (type === 'correlation' && finding.top_correlation) {
    pValue = finding.top_correlation.p;
  } else if (type === 'leading_indicator' && finding.granger_results?.length) {
    pValue = Math.min(...finding.granger_results.map((r) => r.p_value));
  }

  // Key metric text
  let keyMetric = null;
  if (type === 'correlation' && finding.top_correlation) {
    keyMetric = `r = ${finding.top_correlation.r?.toFixed(3)} (${finding.top_correlation.column})`;
  } else if (type === 'anomaly') {
    keyMetric = `anomaly rate: ${((finding.anomaly_rate || 0) * 100).toFixed(1)}%`;
  } else if (type === 'trend') {
    keyMetric = `trend: ${finding.trend_direction || 'unknown'}`;
  } else if (type === 'leading_indicator' && finding.granger_results?.length) {
    const best = finding.granger_results[0];
    keyMetric = `best lag: ${best.best_lag} (${best.column})`;
  } else if (type === 'regime_change') {
    keyMetric = `${finding.changepoints?.length || 0} changepoints`;
  }

  // Affected columns
  const affectedCols = [
    finding.target_column,
    ...(finding.feature_columns || []),
  ].filter(Boolean).slice(0, 4);

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 16,
        cursor: 'pointer',
        transition: 'border-color 0.15s ease',
        marginBottom: 10,
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontWeight: 600, fontSize: 14, flex: 1 }}>
          {finding.name || 'Unnamed Finding'}
        </span>
        <span
          style={{
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            padding: '2px 6px',
            borderRadius: 3,
            backgroundColor: typeColor + '22',
            color: typeColor,
            border: `1px solid ${typeColor}44`,
            whiteSpace: 'nowrap',
          }}
        >
          {typeLabel}
        </span>
        <PValueBadge pValue={pValue} />
        {/* Sparkline */}
        <div style={{ width: 60, height: 24, flexShrink: 0 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparkData}>
              <Line
                type="monotone"
                dataKey="v"
                stroke={typeColor}
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Explanation */}
      {finding.explanation && (
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 8, lineHeight: 1.5 }}>
          {finding.explanation}
        </p>
      )}

      {/* Key metric + columns */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {keyMetric && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-primary)' }}>
            {keyMetric}
          </span>
        )}
        {affectedCols.map((col) => (
          <span
            key={col}
            style={{
              fontSize: 11,
              padding: '2px 6px',
              borderRadius: 3,
              backgroundColor: 'var(--bg-surface-raised)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
            }}
          >
            {col}
          </span>
        ))}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div
          style={{
            marginTop: 14,
            paddingTop: 14,
            borderTop: '1px solid var(--border)',
          }}
        >
          <pre
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              color: 'var(--text-secondary)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              maxHeight: 200,
              overflowY: 'auto',
            }}
          >
            {JSON.stringify(finding, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
