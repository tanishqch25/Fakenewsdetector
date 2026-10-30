export function Spinner() {
  return (
    <div className="state-block loading-block" role="status">
      <div className="spinner" aria-hidden="true" />
      <p>Running the screening model…</p>
    </div>
  );
}

export function ErrorBlock({ message, onRetry }) {
  return (
    <div className="state-block error-block" role="alert">
      <div className="state-icon">⚠</div>
      <h4>Something went wrong</h4>
      <p>{message}</p>
      {onRetry && (
        <button className="btn btn-outline" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyBlock({ title, message }) {
  return (
    <div className="state-block empty-block">
      <div className="state-icon">◇</div>
      <h4>{title}</h4>
      <p>{message}</p>
    </div>
  );
}
