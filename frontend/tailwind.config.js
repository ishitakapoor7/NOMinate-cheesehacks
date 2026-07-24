/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: '#FFFFFF',
        wash: '#F4F4F4',
        gray: '#6E6E6E',
        ink: '#111111',
        yellow: '#FFC700',
        red: '#E23B2E',
        green: '#1D8147',
      },
      fontFamily: {
        display: ['Anton', 'sans-serif'],
        sans: ['"Instrument Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      boxShadow: {
        sticker: '4px 4px 0 #111111',
        'sticker-yellow': '4px 4px 0 #FFC700',
      },
      letterSpacing: {
        caps: '0.08em',
      },
    },
  },
  plugins: [],
}
