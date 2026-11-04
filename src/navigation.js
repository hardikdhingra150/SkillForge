import {
  Box,
  Gauge,
  History,
  Layers3,
  MessagesSquare,
  ShieldCheck,
  Terminal,
} from 'lucide-react';

// The workspace pages in the top navigation, in order.
export const views = [
  {
    id: 'workbench',
    label: 'Workbench',
    icon: Box,
  },
  {
    id: 'chat',
    label: 'Chat',
    icon: MessagesSquare,
  },
  {
    id: 'library',
    label: 'Skill library',
    icon: Layers3,
  },
  {
    id: 'models',
    label: 'Models',
    icon: Gauge,
  },
  {
    id: 'review',
    label: 'Review',
    icon: ShieldCheck,
  },
  {
    id: 'console',
    label: 'Live console',
    icon: Terminal,
  },
  {
    id: 'activity',
    label: 'Activity',
    icon: History,
  },
];

// Every page reachable by #hash; anything else shows the landing page.
export const VIEW_IDS = [...views.map((item) => item.id), 'governance'];
