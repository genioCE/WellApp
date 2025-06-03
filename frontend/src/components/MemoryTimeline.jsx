import React from 'react';
import { useMockMemory } from '../hooks/useMockMemory';

export default function MemoryTimeline() {
  const memories = useMockMemory();

  return (
    <div className="space-y-4">
      {memories.map((mem) => (
        <div
          key={mem.id}
          className="border border-gray-700 rounded p-4 hover:bg-gray-800 transition-colors"
        >
          <div className="text-sm text-gray-400 flex justify-between">
            <span>{new Date(mem.timestamp).toLocaleString()}</span>
            <span className="font-semibold">w:{mem.weight}</span>
          </div>
          <p className="mt-2">{mem.content}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {mem.tags.map((tag) => (
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
