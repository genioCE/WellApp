import React from 'react';
import { render, screen } from '@testing-library/react';
import MemoryTimeline from '../MemoryTimeline';

describe('MemoryTimeline', () => {
  it('renders memory entries', () => {
    const data = [
      { id: 1, timestamp: Date.now(), weight: 1, tags: ['test'], content: 'Hello' }
    ];
    render(<MemoryTimeline data={data} />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
