import { Download, ShieldCheck } from 'lucide-react';

// A finished Workbench run as something a person can read and download: totals become a ranked table,
// cleaned or de-duplicated files become a preview plus the full file.
const number = (value) => Number(value).toLocaleString(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const cell = (value) => {
  const text = String(value ?? '');
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const toCsv = (headers, rows) => `${[headers, ...rows].map((row) => row.map(cell).join(',')).join('\n')}\n`;

function download(filename, text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv' }));
  const link = Object.assign(document.createElement('a'), { href: url, download: filename });
  link.click();
  URL.revokeObjectURL(url);
}

const every = (items, ...keys) => items.every((item) => item && keys.every((key) => key in item));

/** The shape each built-in spreadsheet skill returns, normalized to one of two views. Anything else (a skill
 * created in Studio, with its own output) is shown field by field instead. */
function describe(result) {
  if (!result || typeof result.rows_processed !== 'number') return null;
  if (Array.isArray(result.products) && 'total_revenue' in result && every(result.products, 'product', 'revenue')) {
    return { kind: 'totals', title: 'Revenue by product', label: 'Product', valueLabel: 'Revenue',
      items: result.products.map((item) => ({ name: item.product, total: item.revenue, rows: item.row_count })),
      total: result.total_revenue, sort: 'value', file: 'revenue_by_product.csv', unit: ['product', 'products'] };
  }
  if (Array.isArray(result.groups) && 'total' in result && every(result.groups, 'group', 'total')) {
    return { kind: 'totals', title: `Totals by ${result.group_column || 'group'}`, label: result.group_column || 'Group',
      valueLabel: 'Total', items: result.groups.map((item) => ({ name: item.group, total: item.total, rows: item.row_count })),
      total: result.total, sort: 'value', file: 'totals_by_group.csv', unit: ['group', 'groups'] };
  }
  if (Array.isArray(result.periods) && 'total' in result && every(result.periods, 'period', 'total')) {
    return { kind: 'totals', title: 'Totals by month', label: 'Month', valueLabel: 'Total',
      items: result.periods.map((item) => ({ name: item.period, total: item.total, rows: item.row_count })),
      total: result.total, sort: 'name', file: 'totals_by_month.csv', unit: ['month', 'months'] };
  }
  if (Array.isArray(result.rows) && Array.isArray(result.headers)) {
    const deduped = result.operation === 'dedupe_rows';
    const changes = result.changes || {};
    const facts = deduped
      ? [['Rows kept', result.kept], ['Duplicates removed', result.removed], ['Compared by', result.key_column || 'whole row']]
      : [['Cells trimmed', changes.cells_trimmed], ['Placeholders cleared', changes.placeholders_cleared],
          ['Empty rows removed', changes.blank_rows_removed], ['Headers tidied', changes.headers_tidied]];
    return { kind: 'table', title: deduped ? 'Duplicates removed' : 'Cleaned table', facts,
      file: deduped ? 'deduplicated.csv' : 'cleaned.csv' };
  }
  return null;
}

function Proof({ result }) {
  const checks = result.validation?.checks?.length;
  return (
    <p className="task-result__proof">
      <ShieldCheck size={13} />
      {result.skill?.id} v{result.skill?.version}
      {result.skill?.repaired_from ? ` (repaired from v${result.skill.repaired_from})` : ''}
      {checks ? ` · ${checks} checks passed` : ''}
    </p>
  );
}

/** Whether a skill's output is one of the spreadsheet results this component can show as a table. */
export const isTableResult = (result) => describe(result) !== null;

export function TaskResult({ result }) {
  const view = describe(result);
  if (!view) return null;

  if (view.kind === 'table') {
    const preview = result.rows.slice(0, 20);
    return (
      <section className="task-result" aria-label="Result">
        <header>
          <div>
            <p className="sf-process__eyebrow">Result · {view.title}</p>
            <strong className="task-result__total">{result.rows.length.toLocaleString()}</strong>
            <span className="sf-process__muted">rows in the new file, from {result.rows_processed.toLocaleString()}</span>
          </div>
          <button type="button" className="sf-process__secondary" onClick={() => download(view.file, toCsv(result.headers, result.rows))}>
            <Download size={14} />
            Download CSV
          </button>
        </header>
        <dl className="task-result__facts">
          {view.facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? '—'}</dd></div>)}
        </dl>
        <div className="task-result__scroll">
          <table>
            <thead><tr>{result.headers.map((header) => <th key={header} scope="col">{header}</th>)}</tr></thead>
            <tbody>{preview.map((row, index) => (
              <tr key={index}>{row.map((value, column) => <td key={column}>{value || <span className="task-result__blank">—</span>}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
        {result.rows.length > preview.length && (
          <p className="sf-process__muted">Showing the first {preview.length} rows. The download has all of them.</p>
        )}
        <Proof result={result} />
      </section>
    );
  }

  const items = [...view.items].sort(view.sort === 'name'
    ? (a, b) => String(a.name).localeCompare(String(b.name))
    : (a, b) => Number(b.total) - Number(a.total));
  const top = Math.max(...items.map((item) => Math.abs(Number(item.total))), 1);
  const csv = toCsv([view.label, view.valueLabel.toLowerCase(), 'rows'],
    [...items.map((item) => [item.name, item.total, item.rows ?? '']), ['total', view.total, '']]);

  return (
    <section className="task-result" aria-label="Result">
      <header>
        <div>
          <p className="sf-process__eyebrow">Result · {view.title}</p>
          <strong className="task-result__total">{number(view.total)}</strong>
          <span className="sf-process__muted">
            total across {items.length} {view.unit[items.length === 1 ? 0 : 1]} · {result.rows_processed} rows read
          </span>
        </div>

        <button type="button" className="sf-process__secondary" onClick={() => download(view.file, csv)}>
          <Download size={14} />
          Download CSV
        </button>
      </header>

      <table>
        <thead>
          <tr>
            <th scope="col">{view.label}</th>
            <th scope="col">{view.valueLabel}</th>
            <th scope="col">Rows</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.name}>
              <th scope="row">
                <span className="task-result__bar" style={{ '--width': `${Math.round((100 * Math.abs(Number(item.total))) / top)}%` }} aria-hidden="true" />
                {item.name}
              </th>
              <td>{number(item.total)}</td>
              <td>{item.rows ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <Proof result={result} />
    </section>
  );
}
