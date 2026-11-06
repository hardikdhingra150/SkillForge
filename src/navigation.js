import {
  Gauge,
  Layers3,
  Sparkles,
} from 'lucide-react';

// The pages in the top navigation, in order. Studio is where everything happens: questions, tasks and
// spreadsheets in one place, with skills created, reused and repaired as you go.
export const views = [
  {
    id: 'chat',
    label: 'Studio',
    icon: Sparkles,
  },
  {
    id: 'library',
    label: 'Skills',
    icon: Layers3,
  },
  {
    id: 'models',
    label: 'Models',
    icon: Gauge,
  },
];

// Pages linked from the footer rather than the top navigation.
export const morePages = [
  { id: 'activity', label: 'Past runs' },
  { id: 'review', label: 'Review' },
  { id: 'console', label: 'Live console' },
  { id: 'workbench', label: 'Classic workbench' },
  { id: 'governance', label: 'Guardrails' },
];

// Every page reachable by #hash; anything else shows the landing page.
export const VIEW_IDS = [...views.map((item) => item.id), ...morePages.map((item) => item.id)];

export const PAGE_LABEL = Object.fromEntries([...views, ...morePages].map((item) => [item.id, item.label]));
