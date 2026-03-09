interface PaginationProps {
  hasMore: boolean;
  loading: boolean;
  onLoadMore: () => void;
  total?: number;
  loaded?: number;
}

function Pagination({ hasMore, loading, onLoadMore, total, loaded }: PaginationProps) {
  if (!hasMore && !total) return null;

  return (
    <div className="flex items-center justify-between py-4">
      <div className="text-sm text-gray-500">
        {loaded != null && total != null
          ? `Showing ${loaded} of ${total}`
          : loaded != null
            ? `Showing ${loaded} alerts`
            : null}
      </div>
      {hasMore && (
        <button
          onClick={onLoadMore}
          disabled={loading}
          className="px-4 py-2 text-sm font-medium text-canary-700 bg-canary-50 rounded-md hover:bg-canary-100 disabled:opacity-50 transition-colors"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-canary-300 border-t-canary-600 rounded-full animate-spin" />
              Loading...
            </span>
          ) : (
            "Load More"
          )}
        </button>
      )}
    </div>
  );
}

export default Pagination;
