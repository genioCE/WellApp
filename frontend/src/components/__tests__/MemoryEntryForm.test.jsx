import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MemoryEntryForm from '../MemoryEntryForm';

global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => ({}) }));

describe('MemoryEntryForm', () => {
  it('calls ingest endpoint and clears textarea', async () => {
    const onIngestComplete = jest.fn();
    render(<MemoryEntryForm onIngestComplete={onIngestComplete} />);
    const textarea = screen.getByPlaceholderText('Add memory snapshot...');
    fireEvent.change(textarea, { target: { value: 'test memory' } });
    fireEvent.submit(textarea.closest('form'));

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(fetch.mock.calls[0][0]).toMatch('/memory/ingest');
    expect(onIngestComplete).toHaveBeenCalled();
    expect(textarea.value).toBe('');
  });
});
