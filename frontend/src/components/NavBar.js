import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';

export default function NavBar() {
  const { state } = useApp();
  const navigate = useNavigate();
  const { hardware, llm_online } = state;

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 48,
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        zIndex: 1000,
      }}
    >
      {/* Left: Wordmark */}
      <span
        onClick={() => navigate('/workspace')}
        style={{
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 18,
          color: 'var(--text-primary)',
          letterSpacing: '0.15em',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        SIGNAL
      </span>

      {/* Right: Status indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        {/* Hardware dot */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: hardware.nrf_connected
                ? 'var(--accent-green)'
                : '#444460',
              flexShrink: 0,
            }}
          />
          <span
            style={{
              color: 'var(--text-secondary)',
              fontSize: 12,
            }}
          >
            Hardware
          </span>
        </div>

        {/* LLM status */}
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            color: llm_online ? 'var(--accent-green)' : 'var(--accent-amber)',
          }}
        >
          {llm_online ? 'GX10 · 1 PFLOP' : 'LLM offline'}
        </div>
      </div>
    </nav>
  );
}
