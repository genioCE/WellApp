import React from 'react';

export default function SearchFilterPanel({ keyword, startDate, endDate, onChange, onClear }) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Search &amp; Filter</h2>
      <input
        className="w-full bg-gray-800 border border-gray-700 rounded p-2"
        type="text"
        value={keyword}
        onChange={(e) => onChange({ keyword: e.target.value })}
        placeholder="Search tags or text"
      />
      <div className="flex space-x-2 text-sm">
        <input
          type="date"
          value={startDate}
          onChange={(e) => onChange({ startDate: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded p-1 flex-1"
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => onChange({ endDate: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded p-1 flex-1"
        />
      </div>
      <button
        onClick={onClear}
        className="text-sm text-blue-400 hover:underline"
      >
        Clear Filters
      </button>
    </div>
  );
}
