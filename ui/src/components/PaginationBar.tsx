interface PaginationBarProps {
  page: number;
  pageCount: number;
  loading?: boolean;
  onPageChange: (page: number) => void;
}

export function PaginationBar({ page, pageCount, loading, onPageChange }: PaginationBarProps) {
  if (pageCount <= 1) {
    return null;
  }

  return (
    <div className="pagination row">
      <button
        type="button"
        className="secondary"
        disabled={loading || page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      {Array.from({ length: pageCount }, (_, index) => {
        const pageNumber = index + 1;
        return (
          <button
            key={pageNumber}
            type="button"
            className={pageNumber === page ? "pagination-active" : "secondary"}
            disabled={loading}
            onClick={() => onPageChange(pageNumber)}
          >
            Page {pageNumber}
          </button>
        );
      })}
      <button
        type="button"
        className="secondary"
        disabled={loading || page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </div>
  );
}
