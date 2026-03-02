import { motion, useScroll, useTransform } from 'framer-motion'
import { ArrowRight, Sparkles, Target } from 'lucide-react'
import { useRef } from 'react'

type AnimatedHeroProps = {
  onStartPlanning: () => void
  onExploreDemo: () => void
  onResumeLastPlan?: () => void
  canResume: boolean
}

export default function AnimatedHero({ onStartPlanning, onExploreDemo, onResumeLastPlan, canResume }: AnimatedHeroProps) {
  const sectionRef = useRef<HTMLDivElement | null>(null)
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start start', 'end start'] })
  const y = useTransform(scrollYProgress, [0, 1], [0, 120])
  const scale = useTransform(scrollYProgress, [0, 1], [1, 0.92])

  return (
    <section ref={sectionRef} className="relative min-h-[82vh] overflow-hidden rounded-3xl border border-brand/30 bg-stone-950 p-4 text-white shadow-soft sm:p-6 md:p-10">
      <motion.div className="absolute inset-0" style={{ y }}>
        <div className="absolute -left-32 -top-24 h-96 w-96 rounded-full bg-cyan-500/30 blur-3xl" />
        <div className="absolute right-[-120px] top-20 h-[28rem] w-[28rem] rounded-full bg-violet-500/30 blur-3xl" />
        <div className="absolute bottom-[-120px] left-1/3 h-80 w-80 rounded-full bg-emerald-500/20 blur-3xl" />
      </motion.div>

      <div className="relative z-10 grid min-h-[70vh] items-center gap-8 lg:grid-cols-2">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <p className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200">
            <Sparkles size={14} />
            Admissions Intelligence
          </p>
          <h1 className="mt-5 text-3xl font-semibold leading-tight sm:text-4xl md:text-6xl">
            Build the smartest
            <span className="bg-gradient-to-r from-cyan-300 via-sky-300 to-emerald-300 bg-clip-text text-transparent"> transfer plan </span>
            in one workspace.
          </h1>
          <p className="mt-5 max-w-xl text-sm text-stone-200 md:text-base">
            PathwayIQ combines credit resolution, scenario simulation, and admissions-readiness forecasting so every semester decision is explainable.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <button className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-stone-900 sm:w-auto" onClick={onStartPlanning}>
              Start Planning
              <ArrowRight size={14} />
            </button>
            <button className="min-h-[44px] w-full rounded-xl border border-white/25 bg-white/10 px-4 py-2.5 text-sm font-semibold text-white sm:w-auto" onClick={onExploreDemo}>
              Explore Demo
            </button>
            {canResume && onResumeLastPlan && (
              <button className="min-h-[44px] w-full rounded-xl border border-cyan-300/30 bg-cyan-400/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 sm:w-auto" onClick={onResumeLastPlan}>
                Resume Last Plan
              </button>
            )}
          </div>
        </motion.div>

        <motion.div style={{ scale }} className="relative mx-auto w-full max-w-xl">
          <div className="relative overflow-hidden rounded-2xl border border-white/20 bg-white/10 p-3 backdrop-blur-xl">
            <img
              src="https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1400&q=80"
              alt="Students planning coursework"
              className="h-72 w-full rounded-xl object-cover sm:h-[420px] md:h-[520px]"
            />
            <div className="pointer-events-none absolute inset-0 rounded-xl bg-gradient-to-t from-stone-950/70 via-transparent to-transparent" />
            <div className="absolute bottom-5 left-5 right-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-white/20 bg-black/40 p-3 backdrop-blur">
                <p className="text-xs text-cyan-200">Readiness Score</p>
                <p className="text-2xl font-semibold">86 / 100</p>
              </div>
              <div className="rounded-lg border border-white/20 bg-black/40 p-3 backdrop-blur">
                <p className="text-xs text-emerald-200">Risk Forecast</p>
                <p className="text-sm font-semibold">Low • 0 blockers</p>
              </div>
            </div>
          </div>

          <div className="absolute -left-8 -top-8 rounded-xl border border-white/20 bg-black/40 p-3 backdrop-blur">
            <p className="inline-flex items-center gap-2 text-xs text-cyan-100">
              <Target size={14} />
              Target: UC San Diego CS
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
