import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import NavBar from '../components/NavBar';
import DatasetCard from '../components/DatasetCard';

export default function Workspace() {
  const { state } = useApp();
  const navigate = useNavigate();
  const { datasets, token_savings } = state;

  const datasetEntries = Object.entries(datasets);
  const savings = token_savings?.estimated_savings_usd || 0;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <NavBar />

      {/* Hero section */}
      <div
        style={{
          paddingTop: 48, // NavBar height
          minHeight: 280,
          background: 'radial-gradient(ellipse at 50% 0%, #1A1A3A 0%, #0A0A0F 70%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '80px 24px 40px',
        }}
      >
        <h1
          style={{
            fontSize: 32,
            fontWeight: 300,
            color: 'var(--text-primary)',
            marginBottom: 10,
            letterSpacing: '-0.02em',
          }}
        >
          What do you want to understand?
        </h1>
        <p
          style={{
            fontSize: 15,
            color: 'var(--text-secondary)',
            maxWidth: 480,
          }}
        >
          Upload a dataset or connect a data source to begin
        </p>
      </div>

      {/* Toolbar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          padding: '16px 24px 8px',
        }}
      >
        <button
          onClick={() => navigate('/add')}
          style={{
            padding: '8px 18px',
            borderRadius: 6,
            backgroundColor: 'var(--accent-blue)',
            color: '#fff',
            fontWeight: 600,
            fontSize: 13,
            cursor: 'pointer',
            border: 'none',
          }}
        >
          + Add Dataset
        </button>
      </div>

      {/* Dataset grid or empty state */}
      {datasetEntries.length === 0 ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '60px 24px',
            gap: 16,
          }}
        >
          <div
            style={{
              fontSize: 48,
              color: 'var(--border)',
              lineHeight: 1,
            }}
          >
            +
          </div>
          <div style={{ fontSize: 16, color: 'var(--text-secondary)', fontWeight: 500 }}>
            Add your first dataset
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
            <button
              onClick={() => navigate('/add')}
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
              Upload CSV
            </button>
            <button
              onClick={() => navigate('/monitor')}
              style={{
                padding: '10px 20px',
                borderRadius: 6,
                backgroundColor: 'var(--bg-surface-raised)',
                color: 'var(--text-secondary)',
                fontWeight: 500,
                fontSize: 13,
                cursor: 'pointer',
                border: '1px solid var(--border)',
              }}
            >
              Connect hardware
            </button>
          </div>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
            gap: 16,
            padding: '8px 24px 32px',
          }}
        >
          {datasetEntries.map(([id, dataset]) => (
            <DatasetCard key={id} datasetId={id} dataset={dataset} />
          ))}
        </div>
      )}

      {/* Token savings counter */}
      {savings > 0 && (
        <div
          style={{
            position: 'fixed',
            bottom: 20,
            right: 20,
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 20,
            padding: '6px 14px',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            color: 'var(--accent-green)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
        >
          Saved vs cloud API: ${savings.toFixed(2)}
        </div>
      )}
    </div>
  );
}
