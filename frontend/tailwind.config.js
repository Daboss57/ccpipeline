/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Academic Deco palette
        navy: '#0a1128',
        'navy-light': '#1c2541',
        'navy-lighter': '#3a4f7a',
        gold: '#f4a127',
        'gold-light': '#f9c74f',
        'gold-dark': '#d68910',
        parchment: '#faf8f3',
        'parchment-dark': '#f0ebe1',
        slate: '#3d5a80',
        'slate-light': '#6c8eae',
        copper: '#b85840',
        sage: '#8fa89e',
        // Legacy aliases for compatibility
        base: '#faf8f3',
        ink: '#0a1128',
        brand: '#3d5a80',
        accent: '#f4a127',
        panel: '#ffffff',
      },
      boxShadow: {
        soft: '0 12px 32px rgba(10, 17, 40, 0.15)',
        deco: '0 8px 24px rgba(244, 161, 39, 0.2), 0 2px 8px rgba(10, 17, 40, 0.1)',
        'deco-lg': '0 16px 48px rgba(244, 161, 39, 0.25), 0 4px 16px rgba(10, 17, 40, 0.15)',
      },
      fontFamily: {
        display: ['Cormorant Garamond', 'Georgia', 'serif'],
        sans: ['Outfit', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(61, 90, 128, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(61, 90, 128, 0.05) 1px, transparent 1px)',
        'deco-gradient': 'linear-gradient(135deg, #0a1128 0%, #1c2541 50%, #3d5a80 100%)',
        'gold-shimmer': 'linear-gradient(120deg, #f4a127 0%, #f9c74f 50%, #f4a127 100%)',
      },
      backgroundSize: {
        'grid': '24px 24px',
      },
    },
  },
  plugins: [],
}
