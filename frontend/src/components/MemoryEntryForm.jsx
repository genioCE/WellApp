import React, { useState } from 'react';

export default function MemoryEntryForm() {
  const [content, setContent] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: wire to /memory/ingest endpoint
    console.log('submit', content);
    setContent('');
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
