import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import IngestPanel from '../IngestPanel';

global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => ({ rows_ingested: 1 }) }));

describe('IngestPanel', () => {
  it('uploads selected CSV file', async () => {
    render(<IngestPanel />);
    const input = screen.getByTestId('csv-file');
    const file = new File(['DateTime\n'], 'test.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByText('Upload CSV'));
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(fetch.mock.calls[0][0]).toMatch('/ingest/scada');
  });
});
