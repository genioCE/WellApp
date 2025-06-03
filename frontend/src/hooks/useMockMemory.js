import { useState } from 'react';

export function useMockMemory() {
  const [memories] = useState(() => [
    {
      id: 1,
      timestamp: Date.now() - 1000 * 60 * 60,
      weight: 0.8,
      tags: ['start', 'mock'],
      content: 'Initial memory snapshot of Genio.',
    },
    {
      id: 2,
      timestamp: Date.now() - 1000 * 30,
      weight: 0.5,
      tags: ['update'],
      content: 'Second memory entry demonstrating the timeline.',
    },
  ]);

  return memories;
}
