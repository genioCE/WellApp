import React, { useState } from 'react';
import axios from 'axios';

export default function ChatInterface() {
  const [wellId, setWellId] = useState('');
  const [persona, setPersona] = useState('default');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);

  const sendQuestion = async () => {
    if (!question.trim() || !wellId) return;
    const payload = { well_id: wellId, question, persona };
    try {
      const res = await axios.post('http://localhost:8006/chat', payload);
      setMessages((m) => [
        ...m,
        { role: 'user', text: question },
        { role: 'bot', text: res.data.answer },
      ]);
      setQuestion('');
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'error', text: 'Request failed' },
      ]);
    }
  };

  return (
    <div className="space-y-2">
      <h2 className="text-lg font-semibold">Ask the Well</h2>
      <input
        data-testid="chat-well-id"
        type="text"
        value={wellId}
        onChange={(e) => setWellId(e.target.value)}
        placeholder="Well ID"
        className="w-full bg-gray-800 border border-gray-700 rounded p-2"
      />
      <select
        data-testid="persona-select"
        value={persona}
        onChange={(e) => setPersona(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded p-2"
      >
        <option value="default">Default</option>
        <option value="friendly">Friendly</option>
        <option value="formal">Formal</option>
      </select>
      <div className="flex space-x-2">
        <input
          data-testid="question-input"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="flex-1 bg-gray-800 border border-gray-700 rounded p-2"
          placeholder="Ask a question..."
        />
        <button
          onClick={sendQuestion}
          className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded"
        >
          Send
        </button>
      </div>
      <div className="space-y-1 text-sm">
        {messages.map((m, i) => (
          <div key={i} className="whitespace-pre-wrap">
            <b>{m.role}:</b> {m.text}
          </div>
        ))}
      </div>
    </div>
  );
}
