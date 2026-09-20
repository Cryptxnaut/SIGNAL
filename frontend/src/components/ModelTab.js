import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

export default function ModelTab({ model }) {
  if (!model || model.model_type === 'none' || !model.model_type) {
    return (
      <div
        style={{
          padding: 32,
          textAlign: 'center',
          color: 'var(--text-muted)',
        }}
      >
        No model trained yet. Run an analysis first.
      </div>
    );
  }

  const featureImportance = model.feature_importance || {};
  const featureData = Object.entries(featureImportance)
    .map(([name, value]) => ({ name, value: Math.abs(value) }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  const trainedDate = model.trained_at
    ? new Date(model.trained_at).toLocaleDateString()
    : 'recently';

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
      {/* Left: SHAP chart */}
      <div style={{ flex: '1 1 360px', minWidth: 0 }}>
        <div
          style={{
            fontSize: 12,
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
            marginBottom: 12,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
          }}
        >
          Feature Importance (SHAP)
        </div>
        {featureData.length > 0 ? (
          <ResponsiveContainer width="100%" height={Math.max(200, featureData.length * 32)}>
            <BarChart
              data={featureData}
              layout="vertical"
              margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
            >
              <XAxis
                type="number"
                tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-surface-raised)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  color: 'var(--text-primary)',
                  fontSize: 12,
                  fontFamily: 'var(--font-mono)',
                }}
                formatter={(v) => [v.toFixed(4), 'SHAP']}
              />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                {featureData.map((_, idx) => (
                  <Cell key={idx} fill="var(--accent-blue)" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            No feature importance data available.
          </div>
        )}
      </div>

      {/* Right: metric cards */}
      <div style={{ flex: '0 0 220px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Accuracy */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 16,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
            {model.metric_name || 'METRIC'}
          </div>
          <div
            style={{
              fontSize: 36,
              fontFamily: 'var(--font-mono)',
              fontWeight: 500,
              color: 'var(--accent-blue)',
            }}
          >
            {(model.metric_value != null ? model.metric_value : 0).toFixed(3)}
          </div>
        </div>

        {/* Training rows */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 12,
          }}
        >
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
            TRAINING ROWS
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, color: 'var(--text-primary)' }}>
            {(model.training_rows || 0).toLocaleString()}
          </div>
        </div>

        {/* Training time */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 12,
          }}
        >
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
            TRAINING TIME
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, color: 'var(--text-primary)' }}>
            {model.training_time_ms || 0} ms
          </div>
        </div>

        {/* Trained on */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 12,
          }}
        >
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
            TRAINED ON
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--text-primary)' }}>
            {model.trained_on || 'Local'}
          </div>
        </div>

        {/* Target column */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
          Target: {model.target_column || '—'}
        </div>

        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
          Trained on {trainedDate}
        </div>
      </div>
    </div>
  );
}
