import { motion, useScroll, useTransform } from 'framer-motion'
import { ArrowRight, Award, BookOpen, Target } from 'lucide-react'
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
  const y = useTransform(scrollYProgress, [0, 1], [0, 100])

  return (
    <section ref={sectionRef} className="relative min-h-[90vh] overflow-hidden">
      {/* Art Deco geometric background */}
      <motion.div
        className="absolute inset-0 bg-deco-gradient"
        style={{ y }}
      >
        {/* Geometric sunburst pattern */}
        <div className="absolute inset-0 opacity-10">
          <div
            className="absolute top-1/2 left-1/2 w-[800px] h-[800px] -translate-x-1/2 -translate-y-1/2"
            style={{
              background: `repeating-conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(244, 161, 39, 0.3) 2deg, transparent 4deg)`
            }}
          />
        </div>

        {/* Ornamental grid lines */}
        <div className="absolute inset-0 bg-grid-pattern bg-grid opacity-20" />

        {/* Radial gold accent */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] rounded-full bg-gradient-to-br from-gold/20 to-transparent blur-3xl" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] rounded-full bg-gradient-to-tr from-slate/20 to-transparent blur-3xl" />
      </motion.div>

      {/* Content container with geometric frame */}
      <div className="relative z-10 container mx-auto px-6 py-16 md:py-24 max-w-7xl">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left column - Text content */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Badge with Art Deco styling */}
            <motion.div
              className="inline-flex items-center gap-3 mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6 }}
            >
              <div className="h-px w-8 bg-gold" />
              <span className="text-xs uppercase tracking-[0.25em] text-gold-light font-medium">
                Admissions Intelligence
              </span>
              <div className="h-px w-8 bg-gold" />
            </motion.div>

            {/* Main heading with serif display font */}
            <h1 className="font-display text-5xl md:text-7xl lg:text-8xl font-semibold text-white leading-[0.95] mb-6">
              Navigate Your
              <span className="block mt-2 text-gold-light italic">Academic Journey</span>
            </h1>

            <p className="text-slate-light text-lg md:text-xl leading-relaxed mb-8 max-w-lg">
              PathwayIQ orchestrates credit resolution, scenario simulation, and admissions forecasting—
              <span className="text-white font-medium"> every semester decision, fully transparent.</span>
            </p>

            {/* Action buttons with geometric styling */}
            <div className="flex flex-wrap gap-4">
              <button
                onClick={onStartPlanning}
                className="group relative px-8 py-4 bg-gold text-navy font-semibold text-sm uppercase tracking-wider overflow-hidden transition-all duration-300 hover:shadow-deco-lg"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Start Planning
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </span>
                <div className="absolute inset-0 bg-gold-light transform scale-x-0 group-hover:scale-x-100 transition-transform origin-left duration-300" />
              </button>

              <button
                onClick={onExploreDemo}
                className="px-8 py-4 border-2 border-gold/40 text-gold-light font-semibold text-sm uppercase tracking-wider hover:bg-gold/10 hover:border-gold transition-all duration-300"
              >
                Explore Demo
              </button>

              {canResume && onResumeLastPlan && (
                <button
                  onClick={onResumeLastPlan}
                  className="px-8 py-4 border-2 border-slate-light/30 text-slate-light font-semibold text-sm uppercase tracking-wider hover:bg-slate-light/10 hover:border-slate-light transition-all duration-300"
                >
                  Resume Last Plan
                </button>
              )}
            </div>

            {/* Decorative Art Deco accent line */}
            <div className="mt-12 flex items-center gap-3">
              <div className="w-12 h-[2px] bg-gradient-to-r from-transparent to-gold" />
              <div className="w-2 h-2 bg-gold rotate-45" />
              <div className="w-12 h-[2px] bg-gradient-to-l from-transparent to-gold" />
            </div>
          </motion.div>

          {/* Right column - Visual showcase */}
          <motion.div
            className="relative"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Main card with geometric frame */}
            <div className="relative">
              {/* Corner decorations */}
              <div className="absolute -top-4 -left-4 w-16 h-16 border-t-2 border-l-2 border-gold" />
              <div className="absolute -top-4 -right-4 w-16 h-16 border-t-2 border-r-2 border-gold" />
              <div className="absolute -bottom-4 -left-4 w-16 h-16 border-b-2 border-l-2 border-gold" />
              <div className="absolute -bottom-4 -right-4 w-16 h-16 border-b-2 border-r-2 border-gold" />

              {/* Main content card */}
              <div className="relative bg-navy-light border-2 border-gold/30 p-8 shadow-deco-lg">
                {/* Blueprint-style header */}
                <div className="mb-6 pb-4 border-b border-gold/20">
                  <div className="flex items-center gap-3 text-gold">
                    <Target className="w-5 h-5" />
                    <span className="text-sm uppercase tracking-wider font-semibold">Pathway Blueprint</span>
                  </div>
                  <p className="text-white font-display text-2xl mt-2">UC San Diego • Computer Science</p>
                </div>

                {/* Stats grid with geometric styling */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-navy/50 border border-gold/20 p-4">
                    <div className="flex items-center gap-2 text-gold-light mb-2">
                      <Award className="w-4 h-4" />
                      <span className="text-xs uppercase tracking-wide">Readiness</span>
                    </div>
                    <p className="font-display text-4xl text-white font-semibold">86<span className="text-xl text-slate-light">/100</span></p>
                  </div>

                  <div className="bg-navy/50 border border-gold/20 p-4">
                    <div className="flex items-center gap-2 text-gold-light mb-2">
                      <BookOpen className="w-4 h-4" />
                      <span className="text-xs uppercase tracking-wide">Risk Level</span>
                    </div>
                    <p className="font-display text-2xl text-white font-semibold">Low</p>
                    <p className="text-xs text-slate-light">0 blockers</p>
                  </div>
                </div>

                {/* Timeline visualization */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-gold rotate-45 flex-shrink-0" />
                    <div className="flex-1 h-1 bg-gradient-to-r from-gold to-gold/20" />
                    <span className="text-xs text-slate-light uppercase tracking-wide">2026</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-gold-light rotate-45 flex-shrink-0" />
                    <div className="flex-1 h-1 bg-gradient-to-r from-gold-light to-gold-light/20" />
                    <span className="text-xs text-slate-light uppercase tracking-wide">2027</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-gold/60 rotate-45 flex-shrink-0" />
                    <div className="flex-1 h-1 bg-gradient-to-r from-gold/60 to-transparent" />
                    <span className="text-xs text-slate-light uppercase tracking-wide">2028</span>
                  </div>
                </div>

                {/* Art Deco ornament at bottom */}
                <div className="mt-6 pt-4 border-t border-gold/20 flex justify-center">
                  <div className="flex items-center gap-2">
                    <div className="w-1 h-1 bg-gold rotate-45" />
                    <div className="w-2 h-2 bg-gold rotate-45" />
                    <div className="w-1 h-1 bg-gold rotate-45" />
                  </div>
                </div>
              </div>
            </div>

            {/* Floating accent elements */}
            <motion.div
              className="absolute -top-8 -right-8 w-24 h-24 border-2 border-gold/20 rotate-45"
              animate={{ rotate: [45, 50, 45], opacity: [0.2, 0.4, 0.2] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute -bottom-6 -left-6 w-16 h-16 border-2 border-slate-light/20"
              animate={{ y: [0, -10, 0], opacity: [0.2, 0.3, 0.2] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
