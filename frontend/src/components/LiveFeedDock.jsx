import React from 'react';

export default function LiveFeedDock() {
  // TODO: connect to websocket for live updates
  return (
    <div>
      <h2 className="text-lg font-semibold mb-2">Live Feed</h2>
      <div className="space-y-2 text-sm text-gray-300">
        <p>Waiting for incoming memories...</p>
      </div>
    </div>
  );
}
