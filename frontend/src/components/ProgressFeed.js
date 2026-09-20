import React from 'react';

function StatusDot({ active, done }) {
  if (done) {
    return (
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: 'var(--accent-green)',
          flexShrink: 0,
        }}
      />
    );
  }
  if (active) {
    return (
      <div
        className="spin"
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          border: '2px solid var(--accent-blue)',
          borderTopColor: 'transparent',
          flexShrink: 0,
        }}
      />
    );
  }
  return (
    <div
      style={{
        width: 8,
        height: 8,
        borderRadius: '50%',
        backgroundColor: 'var(--border)',
        flexShrink: 0,
      }}
    />
  );
}

export default function ProgressFeed({ events, progress, isComplete }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Progress bar */}
      <div
        style={{
          height: 2,
          backgroundColor: 'var(--border)',
          borderRadius: 1,
          marginBottom: 24,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progress}%`,
            backgroundColor: 'var(--accent-blue)',
            borderRadius: 1,
            transition: 'width 0.4s ease',
          }}
        />
      </div>

      {/* Event rows */}
      {events.map((event, idx) => {
        const isActive = !isComplete && idx === events.length - 1;
        const isDone = isComplete || idx < events.length - 1;

        return (
          <div
            key={idx}
            className="fade-in"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '8px 0',
              borderBottom: idx < events.length - 1 ? '1px solid var(--border)' : 'none',
            }}
          >
            <StatusDot active={isActive} done={isDone} />
            <span
              style={{
                flex: 1,
                color: isDone ? 'var(--text-secondary)' : 'var(--text-primary)',
                fontSize: 13,
              }}
            >
              {event.message}
            </span>
            {event.timestamp && (
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  flexShrink: 0,
                }}
              >
                {event.timestamp}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
