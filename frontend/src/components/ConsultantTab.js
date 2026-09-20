import React, { useState, useRef, useEffect } from 'react';
import { streamConsultant } from '../utils/api';

const SUGGESTED_QUESTIONS = [
  'What are the most significant patterns in this dataset?',
  'Which features have the strongest predictive power?',
  'What anomalies should I investigate further?',
];

function Message({ role, content }) {
  const isUser = role === 'user';
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 12,
        gap: 8,
        alignItems: 'flex-start',
      }}
    >
      {!isUser && (
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            backgroundColor: 'var(--accent-blue)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 12,
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          S
        </div>
      )}
      <div
        style={{
          maxWidth: '72%',
          padding: '10px 14px',
          borderRadius: isUser ? '12px 12px 2px 12px' : '2px 12px 12px 12px',
          backgroundColor: isUser ? 'var(--bg-surface-raised)' : 'transparent',
          border: isUser ? '1px solid var(--border)' : 'none',
          fontSize: 13,
          color: 'var(--text-primary)',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
        }}
      >
        {content}
      </div>
    </div>
  );
}

export default function ConsultantTab({ datasetId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    if (!text.trim() || streaming) return;
    setShowSuggestions(false);

    const userMsg = { role: 'user', content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setStreaming(true);

    // Add empty assistant message
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    try {
      await streamConsultant(
        datasetId,
        text,
        messages,
        (token) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
              };
            }
            return updated;
          });
        },
        () => {
          setStreaming(false);
        }
      );
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === 'assistant' && last.content === '') {
          updated[updated.length - 1] = {
            ...last,
            content: `Error: ${err.message}`,
          };
        }
        return updated;
      });
      setStreaming(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,
      }}
    >
      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 0',
          minHeight: 0,
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              color: 'var(--text-muted)',
              paddingTop: 32,
              fontSize: 13,
            }}
          >
            Ask anything about your dataset
          </div>
        )}
        {messages.map((msg, i) => (
          <Message key={i} role={msg.role} content={msg.content} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      {showSuggestions && messages.length === 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          {SUGGESTED_QUESTIONS.map((q, i) => (
            <button
              key={i}
              onClick={() => sendMessage(q)}
              style={{
                padding: '6px 12px',
                borderRadius: 16,
                border: '1px solid var(--border)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-secondary)',
                fontSize: 12,
                cursor: 'pointer',
                transition: 'border-color 0.15s',
              }}
              onMouseEnter={(e) =>
                (e.target.style.borderColor = 'var(--accent-blue)')
              }
              onMouseLeave={(e) =>
                (e.target.style.borderColor = 'var(--border)')
              }
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          padding: '12px 0 0',
          borderTop: '1px solid var(--border)',
        }}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your dataset..."
          disabled={streaming}
          rows={2}
          style={{
            flex: 1,
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '10px 12px',
            color: 'var(--text-primary)',
            fontSize: 13,
            resize: 'none',
            outline: 'none',
            fontFamily: 'Inter, sans-serif',
            lineHeight: 1.5,
          }}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || streaming}
          style={{
            padding: '10px 16px',
            borderRadius: 8,
            backgroundColor:
              !input.trim() || streaming ? 'var(--border)' : 'var(--accent-blue)',
            color: !input.trim() || streaming ? 'var(--text-muted)' : '#fff',
            fontWeight: 600,
            fontSize: 13,
            cursor: !input.trim() || streaming ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.15s',
            alignSelf: 'flex-end',
            border: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          {streaming ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
