import { motion } from 'framer-motion'
import { ArrowRight, BookOpen, BarChart2 } from 'lucide-react'
import { useRef } from 'react'

type AnimatedHeroProps = {
  onStartPlanning: () => void
  onExploreDemo: () => void
  onResumeLastPlan?: () => void
  canResume: boolean
}

export default function AnimatedHero({ onStartPlanning, onExploreDemo, onResumeLastPlan, canResume }: AnimatedHeroProps) {
  const sectionRef = useRef<HTMLDivElement | null>(null)

  const fadeIn = (delay = 0) => ({
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1], delay },
  })

  return (
    <section
      ref={sectionRef}
      className="relative overflow-hidden rounded-2xl border border-border bg-brand text-white"
      style={{ minHeight: '72vh' }}
    >
      {/* Subtle grid texture */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(255,255,255,0.6) 39px, rgba(255,255,255,0.6) 40px), repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(255,255,255,0.6) 39px, rgba(255,255,255,0.6) 40px)',
        }}
      />
      {/* Warm accent bleed — top-right corner */}
      <div className="pointer-events-none absolute right-0 top-0 h-64 w-64 rounded-bl-full bg-accent/20" />

      <div className="relative z-10 grid min-h-[72vh] items-center gap-10 px-8 py-14 sm:px-12 md:px-16 lg:grid-cols-[1fr_auto]">
        {/* LEFT — headline */}
        <div className="max-w-2xl">
          <motion.p {...fadeIn(0)} className="mb-4 flex items-center gap-2 font-mono text-[10px] uppercase tracking-academic text-white/50">
            <BookOpen size={11} />
            PathwayIQ · Admissions Intelligence
          </motion.p>

          <motion.h1
            {...fadeIn(0.08)}
            className="font-serif text-4xl font-semibold leading-[1.12] tracking-tight sm:text-5xl md:text-6xl"
          >
            The smartest
            <br />
            <span className="italic text-accent/90">transfer plan</span>
            <br />
            in one workspace.
          </motion.h1>

          <motion.div {...fadeIn(0.16)} className="mt-5 h-px w-12 bg-accent/70" />

          <motion.p {...fadeIn(0.22)} className="mt-5 max-w-lg text-sm leading-relaxed text-white/65 md:text-base">
            PathwayIQ combines credit resolution, scenario simulation, and admissions-readiness forecasting — so every semester decision is explainable and evidence-backed.
          </motion.p>

          <motion.div {...fadeIn(0.3)} className="mt-9 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <button
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg border border-white/90 bg-white px-5 py-2.5 text-sm font-medium text-brand transition-colors hover:bg-white/90 sm:w-auto"
              onClick={onStartPlanning}
            >
              Start Planning
              <ArrowRight size={14} />
            </button>
            <button
              className="min-h-[44px] w-full rounded-lg border border-white/20 bg-white/8 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/15 sm:w-auto"
              onClick={onExploreDemo}
            >
              Explore Demo
            </button>
            {canResume && onResumeLastPlan && (
              <button
                className="min-h-[44px] w-full rounded-lg border border-accent/40 bg-accent/10 px-5 py-2.5 text-sm font-medium text-white/90 transition-colors hover:bg-accent/20 sm:w-auto"
                onClick={onResumeLastPlan}
              >
                Resume Last Plan
              </button>
            )}
          </motion.div>
        </div>

        {/* RIGHT — stat cards */}
        <motion.div
          {...fadeIn(0.2)}
          className="hidden flex-col gap-4 lg:flex"
          style={{ minWidth: '220px' }}
        >
          {[
            { label: 'Readiness Score', value: '86 / 100', sub: 'Low risk · 0 blockers', icon: BarChart2 },
            { label: 'Major Prep Coverage', value: '92%', sub: 'UC San Diego — CS', icon: BookOpen },
            { label: 'Transferable Units', value: '76 units', sub: 'Resolved via AP + CC', icon: BookOpen },
          ].map(({ label, value, sub, icon: Icon }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.28 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
              className="rounded-xl border border-white/12 bg-white/8 px-5 py-4 backdrop-blur-sm"
            >
              <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-academic text-white/45">
                <Icon size={10} />
                {label}
              </p>
              <p className="mt-1.5 font-serif text-2xl font-semibold">{value}</p>
              <p className="mt-0.5 text-xs text-white/45">{sub}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
