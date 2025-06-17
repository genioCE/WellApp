import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import IngestPanel from '../IngestPanel';
import axios from 'axios';

jest.mock('axios');

describe('IngestPanel', () => {
  it('uploads selected CSV file', async () => {
    axios.post.mockResolvedValue({ data: {} });
    render(<IngestPanel />);
    fireEvent.change(screen.getByTestId('well-id'), { target: { value: 'w1' } });
    const input = screen.getByTestId('scada-file');
    const file = new File(['DateTime\n'], 'test.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByText('Upload SCADA CSV'));
    await waitFor(() => expect(axios.post).toHaveBeenCalled());
    expect(axios.post.mock.calls[0][0]).toMatch('/ingest');
  });
});
