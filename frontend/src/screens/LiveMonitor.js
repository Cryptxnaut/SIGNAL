import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import NavBar from '../components/NavBar';
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';

const HOW_TO_CONNECT = `1. Flash Zephyr firmware to your nRF54LM20 DK board.
   Use the BLE service UUID: 12345678-1234-1234-1234-123456789abc

2. Ensure your host machine has Bluetooth enabled.

3. Install the bleak Python library: pip install bleak

4. Restart the SIGNAL backend — it will auto-detect the device.

5. The board should appear here once paired.`;

function RSSIBars({ rssi }) {
  const level = rssi > -60 ? 4 : rssi > -70 ? 3 : rssi > -80 ? 2 : 1;
  return (
    <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 16 }}>
      {[1, 2, 3, 4].map((bar) => (
        <div
          key={bar}
          style={{
            width: 5,
            height: 4 + bar * 3,
            borderRadius: 1,
            backgroundColor:
              bar <= level ? 'var(--accent-green)' : 'var(--border)',
          }}
        />
      ))}
    </div>
  );
}

export default function LiveMonitor() {
  const { state } = useApp();
  const navigate = useNavigate();
  const { hardware } = state;
  const [showHowTo, setShowHowTo] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [waveformData, setWaveformData] = useState(
    Array.from({ length: 50 }, (_, i) => ({
      t: i,
      ch1: Math.sin(i * 0.2) * 50 + 50,
      ch2: Math.cos(i * 0.15) * 40 + 60,
    }))
  );

  const wsRef = useRef(null);

  useEffect(() => {
    if (!hardware.nrf_connected) return;

    // Connect to WebSocket for live data
    const ws = new WebSocket(
      `ws://${window.location.hostname}:8000/api/ws/live`
    );
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'data' && msg.payload) {
          setWaveformData((prev) => {
            const next = [...prev.slice(-49), { t: Date.now(), ...msg.payload }];
            return next;
          });
        }
      } catch (e) {}
    };

    return () => {
      ws.close();
    };
  }, [hardware.nrf_connected]);

  const handleScan = () => {
    setScanning(true);
    setTimeout(() => setScanning(false), 3000);
  };

  if (!hardware.nrf_connected) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        <NavBar />
        <div
          style={{
            paddingTop: 80,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '80px 24px',
            gap: 16,
          }}
        >
          {/* Radio tower icon */}
          <div
            style={{
              fontSize: 64,
              color: 'var(--border)',
              lineHeight: 1,
              marginBottom: 8,
            }}
          >
            📡
          </div>

          <h2
            style={{
              fontSize: 22,
              fontWeight: 500,
              color: 'var(--text-primary)',
              textAlign: 'center',
            }}
          >
            No hardware connected
          </h2>

          <p
            style={{
              fontSize: 14,
              color: 'var(--text-secondary)',
              textAlign: 'center',
              maxWidth: 420,
            }}
          >
            Connect an nRF54LM20 DK over BLE to stream live sensor data and
            detect anomalies in real-time.
          </p>

          {/* Scan button */}
          <button
            onClick={handleScan}
            disabled={scanning}
            style={{
              padding: '10px 24px',
              borderRadius: 6,
              backgroundColor: scanning ? 'var(--border)' : 'var(--accent-blue)',
              color: scanning ? 'var(--text-muted)' : '#fff',
              fontWeight: 600,
              fontSize: 13,
              cursor: scanning ? 'not-allowed' : 'pointer',
              border: 'none',
              marginTop: 8,
            }}
          >
            {scanning ? (
              <span className="pulse">Scanning for devices...</span>
            ) : (
              'Scan for Devices'
            )}
          </button>

          {/* Collapsible "How to connect" */}
          <div
            style={{
              marginTop: 16,
              width: '100%',
              maxWidth: 500,
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              overflow: 'hidden',
            }}
          >
            <button
              onClick={() => setShowHowTo(!showHowTo)}
              style={{
                width: '100%',
                padding: '12px 16px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: 13,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <span>How to connect nRF54LM20</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {showHowTo ? '▲' : '▼'}
              </span>
            </button>
            {showHowTo && (
              <div
                style={{
                  padding: '0 16px 16px',
                  borderTop: '1px solid var(--border)',
                }}
              >
                <pre
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.7,
                    marginTop: 12,
                  }}
                >
                  {HOW_TO_CONNECT}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Connected state
  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <NavBar />
      <div style={{ paddingTop: 72, padding: '72px 24px 32px' }}>
        {/* Device header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: 'var(--accent-green)',
            }}
          />
          <div>
            <div style={{ fontWeight: 600, fontSize: 16 }}>
              {hardware.nrf_device_name || 'nRF54LM20 DK'}
            </div>
            <div
              style={{
                fontSize: 12,
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              BLE Connected
            </div>
          </div>
          {hardware.rssi && <RSSIBars rssi={hardware.rssi} />}
          <button
            onClick={() => navigate('/add')}
            style={{
              marginLeft: 'auto',
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
            Add to Analysis
          </button>
        </div>

        {/* Waveform chart */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 20,
            marginBottom: 20,
          }}
        >
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
            Live Sensor Feed
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={waveformData}>
              <XAxis hide />
              <YAxis
                tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-surface-raised)',
                  border: '1px solid var(--border)',
                  fontSize: 11,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-primary)',
                }}
              />
              <Line
                type="monotone"
                dataKey="ch1"
                stroke="var(--accent-blue)"
                strokeWidth={1.5}
                dot={false}
                name="Ch1"
              />
              <Line
                type="monotone"
                dataKey="ch2"
                stroke="var(--accent-green)"
                strokeWidth={1.5}
                dot={false}
                name="Ch2"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Anomaly feed */}
        {state.hardware.anomaly_feed.length > 0 && (
          <div>
            <div
              style={{
                fontSize: 12,
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: 10,
              }}
            >
              Anomaly Feed
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {state.hardware.anomaly_feed.slice(0, 10).map((anomaly, i) => (
                <div
                  key={i}
                  style={{
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--accent-red)',
                    borderRadius: 6,
                    padding: '8px 12px',
                    fontSize: 12,
                    color: 'var(--accent-red)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {JSON.stringify(anomaly)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
