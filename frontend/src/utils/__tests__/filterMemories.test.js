import { filterMemories } from '../filterMemories';

describe('filterMemories', () => {
  const data = [
    { timestamp: '2023-01-01T00:00:00Z', content: 'Hello world', tags: ['greet'] },
    { timestamp: '2023-02-01T00:00:00Z', content: 'Another entry', tags: ['test'] },
  ];

  it('filters by keyword', () => {
    const result = filterMemories(data, { keyword: 'hello' });
    expect(result).toHaveLength(1);
    expect(result[0].content).toBe('Hello world');
  });

  it('filters by date range', () => {
    const result = filterMemories(data, { startDate: '2023-01-15', endDate: '2023-03-01' });
    expect(result).toHaveLength(1);
    expect(result[0].content).toBe('Another entry');
  });
});
