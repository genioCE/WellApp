import React from 'react';
import MemoryTimeline from '../components/MemoryTimeline';
import MemoryEntryForm from '../components/MemoryEntryForm';
import LiveFeedDock from '../components/LiveFeedDock';
import SearchFilterPanel from '../components/SearchFilterPanel';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="md:w-1/4 p-4 border-r border-gray-700">
        <SearchFilterPanel />
        <MemoryEntryForm />
      </aside>
      <main className="flex-1 p-4 overflow-y-auto space-y-4">
        <MemoryTimeline />
      </main>
      <div className="md:w-1/5 border-l border-gray-700 p-4">
        <LiveFeedDock />
      </div>
    </div>
  );
}
