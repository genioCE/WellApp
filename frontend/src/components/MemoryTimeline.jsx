import React from 'react';

export default function MemoryTimeline({ data = [] }) {
  if (!data.length) {
    return (
      <div className="text-gray-400 italic">No memory entries available.</div>
    );
  }

  return (
    <div className="space-y-4">
      {data.map((mem) => (
        <div
          key={mem.id || mem.timestamp}
          className="border border-gray-700 rounded p-4 hover:bg-gray-800 transition-colors"
        >
          <div className="text-sm text-gray-400 flex justify-between">
            <span>{new Date(mem.timestamp).toLocaleString()}</span>
            <span className="font-semibold">
              {mem.weight ? `w:${mem.weight}` : ''}
            </span>
          </div>
          <p className="mt-2">{mem.content || mem.text}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(mem.tags || []).map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-700 px-2 py-1 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
