/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#f5f3ef',
        ink: '#1c1814',
        brand: '#005f73',
        accent: '#ca6702',
        panel: '#fffdf8',
      },
      boxShadow: {
        soft: '0 12px 32px rgba(28, 24, 20, 0.12)',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '"Segoe UI"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
