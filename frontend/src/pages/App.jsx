import React, { useState, useEffect } from 'react';
import MemoryTimeline from '../components/MemoryTimeline';
import MemoryEntryForm from '../components/MemoryEntryForm';
import LiveFeedDock from '../components/LiveFeedDock';
import SearchFilterPanel from '../components/SearchFilterPanel';

export default function App() {
  const [timelineData, setTimelineData] = useState([]);

const fetchTimeline = async () => {
  try {
    const res = await fetch('http://localhost:8007/memory/replay');
    const data = await res.json();

    const mapped = data.map((item, index) => ({
      id: item.uuid || index,
      timestamp: item.timestamp,
      content: item.tokens ? item.tokens.join(' ') : '(no content)',
      weight: item.weight || 1.0,
      tags: item.tags || []
    }));

    setTimelineData(mapped);
  } catch (err) {
    console.error('Error fetching timeline:', err);
  }
};

  useEffect(() => {
    fetchTimeline();
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col md:flex-row">
      <aside className="md:w-1/4 p-4 border-r border-gray-700">
        <SearchFilterPanel />
        <MemoryEntryForm onIngestComplete={fetchTimeline} />
      </aside>
      <main className="flex-1 p-4 overflow-y-auto space-y-4">
        <MemoryTimeline data={timelineData} />
      </main>
      <div className="md:w-1/5 border-l border-gray-700 p-4">
        <LiveFeedDock />
      </div>
    </div>
  );
}
