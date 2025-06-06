/**
 * Filter a list of memory objects based on keyword and date range.
 * @param {Array} memories - Memory objects with at least `content`, `tags`, and `timestamp` fields.
 * @param {Object} filters - Filters { keyword?: string, startDate?: string, endDate?: string }
 * @returns {Array} Filtered memories.
 */
export function filterMemories(memories, { keyword = '', startDate = '', endDate = '' } = {}) {
  const kw = keyword.trim().toLowerCase();
  const start = startDate ? new Date(startDate) : null;
  const end = endDate ? new Date(endDate) : null;

  return memories.filter((m) => {
    if (kw) {
      const haystack = `${m.content ?? ''} ${Array.isArray(m.tags) ? m.tags.join(' ') : ''}`.toLowerCase();
      if (!haystack.includes(kw)) {
        return false;
      }
    }
    if (start && new Date(m.timestamp) < start) return false;
    if (end && new Date(m.timestamp) > end) return false;
    return true;
  });
}
