import React, { useState, useEffect, useMemo } from 'react';
import MemoryTimeline from '../components/MemoryTimeline';
import IngestPanel from '../components/IngestPanel';
import LiveFeedDock from '../components/LiveFeedDock';
import SearchFilterPanel from '../components/SearchFilterPanel';
import { filterMemories } from '../utils/filterMemories';

export default function App() {
  const [timelineData, setTimelineData] = useState([]);
  const [feedMessages, setFeedMessages] = useState([]);
  const [filters, setFilters] = useState({ keyword: '', startDate: '', endDate: '' });

  const fetchTimeline = async () => {
    try {
      const res = await fetch('http://localhost:8007/memory/replay');
      const data = await res.json();
      const mapped = data.map((item, index) => ({
        id: item.uuid || index,
        timestamp: item.timestamp,
        content: item.tokens ? item.tokens.join(' ') : '(no content)',
        weight: item.weight || 1.0,
        tags: item.tags || [],
      }));
      setTimelineData(mapped);
    } catch (err) {
      console.error('Error fetching timeline:', err);
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, []);

  const filteredTimeline = useMemo(
    () => filterMemories(timelineData, filters),
    [timelineData, filters]
  );

  const handleLog = (msg) => {
    setFeedMessages((m) => [...m.slice(-50), msg]);
  };

  const handleFilterChange = (patch) => {
    setFilters((f) => ({ ...f, ...patch }));
  };

  const handleClearFilters = () => setFilters({ keyword: '', startDate: '', endDate: '' });

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col md:flex-row">
      <aside className="md:w-1/4 p-4 border-r border-gray-700 space-y-4">
        <SearchFilterPanel
          keyword={filters.keyword}
          startDate={filters.startDate}
          endDate={filters.endDate}
          onChange={handleFilterChange}
          onClear={handleClearFilters}
        />
        <IngestPanel onIngestComplete={fetchTimeline} onLog={handleLog} />
      </aside>
      <main className="flex-1 p-4 overflow-y-auto space-y-4">
        <MemoryTimeline data={filteredTimeline} />
      </main>
      <div className="md:w-1/5 border-l border-gray-700 p-4 flex flex-col">
        <LiveFeedDock messages={feedMessages} memories={timelineData} />
      </div>
    </div>
  );
}
