// The Workbench's file workflows (mirrors backend/app/services/workflows.py). Clicking one fills the task box.
export const workflows = [
  { id: 'revenue_by_product', title: 'Revenue by product', example: 'Show revenue by product from my sales data.' },
  { id: 'totals_by_group', title: 'Totals by a column', example: 'Total sales by region.' },
  { id: 'totals_by_month', title: 'Totals by month', example: 'Monthly sales totals from my orders file.' },
  { id: 'dedupe_rows', title: 'Remove duplicates', example: 'Remove duplicate rows from my customer list.' },
  { id: 'clean_table', title: 'Clean up a table', example: 'Clean up this spreadsheet export.' },
];
