import React, { createContext, useContext, useReducer } from 'react';

const initialState = {
  datasets: {},
  hardware: {
    nrf_connected: false,
    nrf_device_name: null,
    last_reading: null,
    anomaly_feed: [],
  },
  token_savings: {
    total_tokens: 0,
    estimated_savings_usd: 0,
  },
  llm_online: true,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_DATASET': {
      return {
        ...state,
        datasets: {
          ...state.datasets,
          [action.payload.id]: {
            ...(state.datasets[action.payload.id] || {}),
            ...action.payload.data,
          },
        },
      };
    }
    case 'UPDATE_DATASET_STATUS': {
      const { id, ...updates } = action.payload;
      return {
        ...state,
        datasets: {
          ...state.datasets,
          [id]: {
            ...(state.datasets[id] || {}),
            ...updates,
          },
        },
      };
    }
    case 'SET_HARDWARE': {
      return {
        ...state,
        hardware: { ...state.hardware, ...action.payload },
      };
    }
    case 'SET_LLM_ONLINE': {
      return { ...state, llm_online: action.payload };
    }
    case 'ADD_TOKEN_SAVINGS': {
      const { tokens, savings_usd } = action.payload;
      return {
        ...state,
        token_savings: {
          total_tokens: state.token_savings.total_tokens + (tokens || 0),
          estimated_savings_usd:
            state.token_savings.estimated_savings_usd + (savings_usd || 0),
        },
      };
    }
    case 'ADD_ANOMALY': {
      return {
        ...state,
        hardware: {
          ...state.hardware,
          anomaly_feed: [action.payload, ...state.hardware.anomaly_feed].slice(0, 50),
        },
      };
    }
    default:
      return state;
  }
}

export const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
