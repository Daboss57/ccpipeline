import { Calendar, Clock, Code, FileText, User } from 'lucide-react'
import RadialOrbitalTimeline, { type TimelineItem } from '@/components/ui/radial-orbital-timeline'

const timelineData: TimelineItem[] = [
  {
    id: 1,
    title: 'Planning',
    date: 'Step 1',
    content: 'Collect profile, goals, target school, and constraints for planning.',
    category: 'Planning',
    icon: Calendar,
    relatedIds: [2],
    status: 'completed',
    energy: 100,
  },
  {
    id: 2,
    title: 'Credit Map',
    date: 'Step 2',
    content: 'Resolve AP/IB/CLEP and transfer credits against policy data.',
    category: 'Credit',
    icon: FileText,
    relatedIds: [1, 3],
    status: 'completed',
    energy: 88,
  },
  {
    id: 3,
    title: 'Generate Plan',
    date: 'Step 3',
    content: 'Build and validate a term-by-term schedule with AI optimization.',
    category: 'Scheduling',
    icon: Code,
    relatedIds: [2, 4],
    status: 'in-progress',
    energy: 72,
  },
  {
    id: 4,
    title: 'Scenario Diff',
    date: 'Step 4',
    content: 'Compare No AP/Fast/Light variants and understand tradeoffs.',
    category: 'Scenarios',
    icon: User,
    relatedIds: [3, 5],
    status: 'pending',
    energy: 45,
  },
  {
    id: 5,
    title: 'Apply Ready',
    date: 'Step 5',
    content: 'Track readiness score, blockers, and finalize the path to submit.',
    category: 'Outcome',
    icon: Clock,
    relatedIds: [4],
    status: 'pending',
    energy: 25,
  },
]

export function RadialOrbitalTimelineDemo() {
  return <RadialOrbitalTimeline timelineData={timelineData} />
}
