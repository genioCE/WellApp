import React, { useState } from 'react';
import axios from 'axios';
import MemoryEntryForm from './MemoryEntryForm';

export default function IngestPanel({ onIngestComplete, onLog }) {
  const [wellId, setWellId] = useState('');
  const [scadaFile, setScadaFile] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);
  const [status, setStatus] = useState('');

  const uploadFile = async (file) => {
    if (!file || !wellId) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('well_id', wellId);
    try {
      await axios.post('http://localhost:8010/ingest', formData);
      onLog?.(`[upload] ${file.name} stored`);
      setStatus('success');
      onIngestComplete?.();
    } catch (err) {
      setStatus('error');
      onLog?.(`[error] ${err.message}`);
    }
  };

  return (
    <div className="space-y-4">
      <input
        data-testid="well-id"
        type="text"
        value={wellId}
        onChange={(e) => setWellId(e.target.value)}
        placeholder="Well ID"
        className="w-full bg-gray-800 border border-gray-700 rounded p-2"
      />
      <div className="space-y-2">
        <input
          data-testid="scada-file"
          type="file"
          accept=".csv"
          onChange={(e) => setScadaFile(e.target.files[0])}
          className="text-sm"
        />
        {scadaFile && (
          <div className="text-xs text-gray-300">{scadaFile.name}</div>
        )}
        <button
          onClick={() => uploadFile(scadaFile)}
          disabled={!scadaFile || !wellId}
          className="w-full bg-green-600 hover:bg-green-700 text-white p-2 rounded"
        >
          Upload SCADA CSV
        </button>
      </div>
      <div className="space-y-2">
        <input
          data-testid="pdf-file"
          type="file"
          accept=".pdf"
          onChange={(e) => setPdfFile(e.target.files[0])}
          className="text-sm"
        />
        {pdfFile && (
          <div className="text-xs text-gray-300">{pdfFile.name}</div>
        )}
        <button
          onClick={() => uploadFile(pdfFile)}
          disabled={!pdfFile || !wellId}
          className="w-full bg-green-600 hover:bg-green-700 text-white p-2 rounded"
        >
          Upload Wellfile PDF
        </button>
      </div>
      {status === 'success' && (
        <div className="text-xs text-green-400">Upload successful</div>
      )}
      {status === 'error' && (
        <div className="text-xs text-red-400">Upload failed</div>
      )}
      <MemoryEntryForm onIngestComplete={onIngestComplete} onLog={onLog} />
    </div>
  );
}
