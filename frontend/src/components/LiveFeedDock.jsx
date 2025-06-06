import React from 'react';
import SpiralCanvas from './SpiralCanvas';

export default function LiveFeedDock({ messages = [], memories = [] }) {
  return (
    <div className="flex flex-col h-full">
      <h2 className="text-lg font-semibold mb-2">Live Feed</h2>
      <div className="flex-1 overflow-y-auto space-y-1 text-sm text-gray-300 bg-gray-800 p-2 rounded">
        {messages.length ? (
          messages.map((m, i) => (
            <div key={i} className="whitespace-pre-wrap">{m}</div>
          ))
        ) : (
          <p>Waiting for incoming memories...</p>
        )}
      </div>
      <SpiralCanvas memories={memories} />
    </div>
  );
}
