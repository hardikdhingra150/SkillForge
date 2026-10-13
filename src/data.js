export const stages = ['Discover', 'Create', 'Execute', 'Evaluate', 'Repair', 'Version', 'Reuse'];
export const initialSkills = [
  { id: 'sales_analysis', name: 'Sales analysis', description: 'Messy spreadsheets in. Clear revenue stories out.', version: '1.1', kind: 'byte', category: 'Data', tests: 3, runs: 28, tools: ['read_csv', 'aggregate', 'save_report'], tag: 'THE NUMBER WHISPERER' },
  { id: 'document_summary', name: 'Document summary', description: 'Find the signal. Leave the twenty-page read behind.', version: '2.0', kind: 'patch', category: 'Research', tests: 5, runs: 42, tools: ['read_document', 'summarize', 'save_report'], tag: 'BIG DOCS, SMALL SUMMARIES' },
  { id: 'code_review', name: 'Code review', description: 'A second pair of eyes. And a few less “oops” moments.', version: '1.3', kind: 'scout', category: 'Code', tests: 8, runs: 16, tools: ['read_file', 'analyze_code', 'save_report'], tag: 'YOUR FRIENDLY BUG HUNTER' },
  { id: 'data_cleanup', name: 'Data cleanup', description: 'Fix the blanks, duplicates, and columns that refuse to agree.', version: '2.1', kind: 'byte', category: 'Data', tests: 7, runs: 36, tools: ['read_csv', 'normalize', 'save_csv'], tag: 'A FRESH START FOR YOUR DATA' },
  { id: 'web_research', name: 'Web research', description: 'Follow the interesting questions. Bring back the sources.', version: '1.0', kind: 'patch', category: 'Research', tests: 6, runs: 19, tools: ['search_web', 'read_page', 'save_report'], tag: 'CURIOUS BY DEFAULT' },
  { id: 'test_generator', name: 'Test generator', description: 'Give your code the edge cases it did not see coming.', version: '1.0', kind: 'scout', category: 'Code', tests: 5, runs: 12, tools: ['read_file', 'generate_tests', 'run_pytest'], tag: 'EXPECT THE UNEXPECTED' },
];
export const initialRuns = [
  { id: 'run-108', name: 'Summarize Q3 research', skill: 'document_summary', result: 'Passed', version: '2.0', time: '12 min ago', duration: '2.4s', kind: 'patch' },
  { id: 'run-107', name: 'Analyze quarterly sales', skill: 'sales_analysis', result: 'Repaired', version: '1.1', time: '38 min ago', duration: '9.0s', kind: 'byte' },
  { id: 'run-106', name: 'Review authentication flow', skill: 'code_review', result: 'Passed', version: '1.3', time: '1 hour ago', duration: '3.2s', kind: 'scout' },
];
export const crew = [
  { kind: 'byte', name: 'Byte', role: 'THE BUILDER', description: 'Turns a “can you?” into a working skill.', speech: ['Ready to make something?', 'New skill. Who dis?', 'Beep. Let’s build.', 'Tiny pixels. Big plans.'] },
  { kind: 'patch', name: 'Patch', role: 'THE FIXER', description: 'Finds the problem. Learns from the fix.', speech: ['I can fix that.', 'A bug is just a plot twist.', 'Tests first. Victory dance after.', 'Good as new. Better, actually.'] },
  { kind: 'scout', name: 'Scout', role: 'THE EXPLORER', description: 'Finds the right capability for the job.', speech: ['Found something useful!', 'There’s a skill for that.', 'Let me look around.', 'Curiosity: fully charged.'] },
];
