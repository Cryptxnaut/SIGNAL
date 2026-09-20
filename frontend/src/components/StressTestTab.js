import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';

const STATUS_COLORS = {
  STABLE: 'var(--accent-green)',
  DEGRADED: 'var(--accent-amber)',
  BROKEN: 'var(--accent-red)',
};

const STATUS_BG = {
  STABLE: '#10B98126',
  DEGRADED: '#F59E0B26',
  BROKEN: '#EF444426',
};

function StatusCell({ status, change_pct }) {
  const color = STATUS_COLORS[status] || 'var(--text-muted)';
  const bg = STATUS_BG[status] || 'transparent';
  return (
    <td
      style={{
        padding: '6px 8px',
        backgroundColor: bg,
        textAlign: 'center',
        borderRight: '1px solid var(--border)',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color,
        whiteSpace: 'nowrap',
      }}
    >
      <div>{status}</div>
      <div style={{ color: 'var(--text-muted)', fontSize: 10 }}>
        {change_pct != null ? `${change_pct.toFixed(1)}%` : '—'}
      </div>
    </td>
  );
}

const PERTURBATION_LEVELS = ['-50%', '-25%', '+25%', '+50%', '+100%', 'set_min', 'set_max', 'set_zero'];

export default function StressTestTab({ stressTest, depth, datasetId }) {
  const navigate = useNavigate();

  if (!depth || depth === 'quick') {
    return (
      <div
        style={{
          padding: 48,
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 16,
        }}
      >
        <div style={{ fontSize: 32, opacity: 0.3 }}>🔒</div>
        <div style={{ fontSize: 16, color: 'var(--text-secondary)', fontWeight: 500 }}>
          Run Deep Analysis to unlock stress testing
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Stress testing requires model training, available in Deep Analysis or Full Stress Test.
        </div>
        <button
          onClick={() => navigate(`/add`)}
          style={{
            marginTop: 8,
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
          New Analysis
        </button>
      </div>
    );
  }

  if (!stressTest || !stressTest.perturbation_matrix || stressTest.perturbation_matrix.length === 0) {
    return (
      <div style={{ padding: 32, color: 'var(--text-muted)', textAlign: 'center' }}>
        Stress test data not available. Run a deep or stress analysis first.
      </div>
    );
  }

  const { perturbation_matrix, edge_cases } = stressTest;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Perturbation matrix */}
      <div>
        <div
          style={{
            fontSize: 12,
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: 12,
          }}
        >
          Perturbation Matrix
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              border: '1px solid var(--border)',
              borderRadius: 6,
              overflow: 'hidden',
              fontSize: 12,
            }}
          >
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-surface-raised)' }}>
                <th
                  style={{
                    padding: '8px 12px',
                    textAlign: 'left',
                    color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    fontWeight: 500,
                    borderRight: '1px solid var(--border)',
                    borderBottom: '1px solid var(--border)',
                  }}
                >
                  Feature
                </th>
                {PERTURBATION_LEVELS.map((level) => (
                  <th
                    key={level}
                    style={{
                      padding: '8px 8px',
                      textAlign: 'center',
                      color: 'var(--text-muted)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 10,
                      fontWeight: 500,
                      borderRight: '1px solid var(--border)',
                      borderBottom: '1px solid var(--border)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {level}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {perturbation_matrix.map((row, i) => (
                <tr
                  key={i}
                  style={{
                    borderBottom: '1px solid var(--border)',
                    backgroundColor: i % 2 === 0 ? 'var(--bg-surface)' : 'var(--bg-primary)',
                  }}
                >
                  <td
                    style={{
                      padding: '8px 12px',
                      color: 'var(--text-primary)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 12,
                      borderRight: '1px solid var(--border)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {row.feature}
                  </td>
                  {PERTURBATION_LEVELS.map((level) => {
                    const data = row.perturbations?.[level];
                    return data ? (
                      <StatusCell key={level} status={data.status} change_pct={data.change_pct} />
                    ) : (
                      <td
                        key={level}
                        style={{
                          padding: '6px 8px',
                          textAlign: 'center',
                          color: 'var(--text-muted)',
                          fontSize: 11,
                          borderRight: '1px solid var(--border)',
                        }}
                      >
                        —
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edge cases */}
      {edge_cases && edge_cases.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 12,
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: 12,
            }}
          >
            Critical Edge Cases
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {edge_cases.map((ec, i) => (
              <div
                key={i}
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderLeft: '3px solid var(--accent-red)',
                  borderRadius: 6,
                  padding: 14,
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: 'var(--accent-red)' }}>
                  {ec.title}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {ec.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
