import { Download, ShieldCheck } from 'lucide-react';

// A finished revenue-by-product run, as a table a person can read and download.
const number = (value) => Number(value).toLocaleString(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function toCsv(products, total) {
  const cell = (value) => (/[",\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value);
  const lines = ['product,revenue,rows', ...products.map((item) => [cell(String(item.product)), item.revenue, item.row_count ?? ''].join(','))];

  return `${lines.join('\n')}\ntotal,${total},\n`;
}

export function TaskResult({ result }) {
  if (!Array.isArray(result?.products)) {
    return null;
  }

  const products = [...result.products].sort((a, b) => Number(b.revenue) - Number(a.revenue));
  const top = Math.max(...products.map((item) => Math.abs(Number(item.revenue))), 1);
  const checks = result.validation?.checks?.length;

  const download = () => {
    const url = URL.createObjectURL(new Blob([toCsv(products, result.total_revenue)], { type: 'text/csv' }));
    const link = Object.assign(document.createElement('a'), { href: url, download: 'revenue_by_product.csv' });

    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="task-result" aria-label="Result">
      <header>
        <div>
          <p className="sf-process__eyebrow">Result</p>
          <strong className="task-result__total">{number(result.total_revenue)}</strong>
          <span className="sf-process__muted">
            total across {products.length} products · {result.rows_processed} rows
          </span>
        </div>

        <button type="button" className="sf-process__secondary" onClick={download}>
          <Download size={14} />
          Download CSV
        </button>
      </header>

      <table>
        <thead>
          <tr>
            <th scope="col">Product</th>
            <th scope="col">Revenue</th>
            <th scope="col">Rows</th>
          </tr>
        </thead>
        <tbody>
          {products.map((item) => (
            <tr key={item.product}>
              <th scope="row">
                <span className="task-result__bar" style={{ '--width': `${Math.round((100 * Math.abs(Number(item.revenue))) / top)}%` }} aria-hidden="true" />
                {item.product}
              </th>
              <td>{number(item.revenue)}</td>
              <td>{item.row_count ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="task-result__proof">
        <ShieldCheck size={13} />
        {result.skill?.id} v{result.skill?.version}
        {result.skill?.repaired_from ? ` (repaired from v${result.skill.repaired_from})` : ''}
        {checks ? ` · ${checks} checks passed` : ''}
      </p>
    </section>
  );
}
