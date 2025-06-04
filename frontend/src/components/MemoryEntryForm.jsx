import React, { useState } from 'react';

export default function MemoryEntryForm({ onIngestComplete }) {
  const [content, setContent] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!content.trim()) return;

    try {
      const response = await fetch('http://localhost:8001/memory/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: content }),
      });

      if (response.ok) {
        console.log('✅ Memory ingested');
        setContent('');
        if (typeof onIngestComplete === 'function') {
          onIngestComplete(); // 🔁 trigger timeline reload
        }
      } else {
        console.error('❌ Ingest failed:', await response.text());
      }
    } catch (err) {
      console.error('🚨 Network error:', err);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2 mt-4">
      <textarea
        className="w-full bg-gray-800 border border-gray-700 rounded p-2"
        rows="3"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Add memory snapshot..."
      />
      <button
        type="submit"
        className="w-full bg-blue-600 hover:bg-blue-700 text-white p-2 rounded"
      >
        Ingest Memory
      </button>
    </form>
  );
}
