import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import Workspace from './screens/Workspace';
import AddDataset from './screens/AddDataset';
import AnalysisView from './screens/AnalysisView';
import LiveMonitor from './screens/LiveMonitor';
import { getHealth, getHardwareStatus } from './utils/api';

function AppRoutes() {
  const { dispatch } = useApp();

  useEffect(() => {
    // Check LLM health on mount
    getHealth()
      .then((data) => {
        dispatch({ type: 'SET_LLM_ONLINE', payload: data.ollama_online });
      })
      .catch(() => {
        dispatch({ type: 'SET_LLM_ONLINE', payload: false });
      });

    // Poll hardware status every 3 seconds
    const pollHardware = () => {
      getHardwareStatus()
        .then((data) => {
          dispatch({ type: 'SET_HARDWARE', payload: data });
        })
        .catch(() => {});
    };

    pollHardware();
    const interval = setInterval(pollHardware, 3000);
    return () => clearInterval(interval);
  }, [dispatch]);

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/workspace" replace />} />
      <Route path="/workspace" element={<Workspace />} />
      <Route path="/add" element={<AddDataset />} />
      <Route path="/analysis/:datasetId" element={<AnalysisView />} />
      <Route path="/analysis/:datasetId/:tab" element={<AnalysisView />} />
      <Route path="/monitor" element={<LiveMonitor />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AppProvider>
  );
}
