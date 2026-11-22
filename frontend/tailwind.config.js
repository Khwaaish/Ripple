/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0b0e13',
        panel: '#11151c',
        line: '#202630',
        muted: '#8993a4',
        mint: '#58d6b0',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 30px rgba(88, 214, 176, .08)',
      },
    },
  },
  plugins: [],
}
