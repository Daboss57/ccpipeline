/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#f7f5f0',
        ink: '#1a1917',
        brand: '#14305a',
        accent: '#b8481e',
        panel: '#ffffff',
        muted: '#6b6460',
        border: '#e5e1d8',
      },
      boxShadow: {
        soft: '0 1px 3px rgba(26, 25, 23, 0.08), 0 4px 12px rgba(26, 25, 23, 0.06)',
        card: '0 0 0 1px rgba(26, 25, 23, 0.06), 0 2px 8px rgba(26, 25, 23, 0.06)',
      },
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        mono: ['"DM Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        academic: '0.12em',
        wide: '0.06em',
      },
    },
  },
  plugins: [],
}
