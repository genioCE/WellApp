import React from 'react';
import { render, screen } from '@testing-library/react';
import MemoryTimeline from '../MemoryTimeline';

jest.mock('../../hooks/useMockMemory', () => ({
  useMockMemory: () => [
    { id: 1, timestamp: 0, weight: 1, tags: ['test'], content: 'Hello' },
  ],
}));

describe('MemoryTimeline', () => {
  it('renders memory entries', () => {
    render(<MemoryTimeline />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
