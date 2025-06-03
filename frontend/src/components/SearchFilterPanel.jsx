import React from 'react';

export default function SearchFilterPanel() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Search &amp; Filter</h2>
      <input
        className="w-full bg-gray-800 border border-gray-700 rounded p-2"
        type="text"
        placeholder="Search tags or text"
      />
      <div className="flex space-x-2 text-sm">
        <input type="date" className="bg-gray-800 border border-gray-700 rounded p-1 flex-1" />
        <input type="date" className="bg-gray-800 border border-gray-700 rounded p-1 flex-1" />
      </div>
    </div>
  );
}
