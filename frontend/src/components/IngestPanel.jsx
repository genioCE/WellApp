import React, { useState } from 'react';
import MemoryEntryForm from './MemoryEntryForm';

export default function IngestPanel({ onIngestComplete, onLog }) {
  const [file, setFile] = useState(null);
  const [rows, setRows] = useState(null);

  const handleUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('http://localhost:8001/ingest/scada', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        onLog?.(`[scada] ${data.rows_ingested} rows ingested`);
        setRows(data.rows_ingested);
        onIngestComplete?.();
      } else {
        onLog?.(`[error] ${data.errors?.join(', ')}`);
      }
    } catch (err) {
      onLog?.(`[error] ${err}`);
    }
  };

  return (
    <div className="space-y-4">
      <MemoryEntryForm onIngestComplete={onIngestComplete} onLog={onLog} />
      <div className="space-y-2">
        <input
          data-testid="csv-file"
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files[0])}
          className="text-sm"
        />
        {file && (
          <div className="text-xs text-gray-300">{file.name}</div>
        )}
        <button
          onClick={handleUpload}
          disabled={!file}
          className="w-full bg-green-600 hover:bg-green-700 text-white p-2 rounded"
        >
          Upload CSV
        </button>
        {rows !== null && (
          <div className="text-xs">Rows processed: {rows}</div>
        )}
      </div>
    </div>
  );
}
