export function A2uiRenderer({ component }) {
  if (!component) {
    return null;
  }

  switch (component.type) {
    case "Card":
      return <A2uiCard component={component} />;
    case "Table":
      return <A2uiTable component={component} />;
    case "Text":
      return <A2uiText component={component} />;
    default:
      return (
        <div className="unsupported" role="alert">
          Unsupported component
        </div>
      );
  }
}

function A2uiCard({ component }) {
  return (
    <article className="a2ui-card">
      <header className="a2ui-card__header">
        <p className="eyebrow">A2UI Card</p>
        <h2>{component.props.title}</h2>
      </header>
      <div className="a2ui-card__body">
        {component.children.map((child, index) => (
          <A2uiRenderer key={`${child.type}-${index}`} component={child} />
        ))}
      </div>
    </article>
  );
}

function A2uiTable({ component }) {
  const columns = component.props.columns ?? [];
  const rows = component.props.rows ?? [];

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={row.join("-") || rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function A2uiText({ component }) {
  return <p className="a2ui-note">{component.props.text}</p>;
}
