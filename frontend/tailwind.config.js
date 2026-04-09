/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dark: {
          50: '#e8e9f0',
          100: '#c5c6d0',
          200: '#9b9ca8',
          300: '#6b6c7a',
          400: '#4a4b59',
          500: '#3a3b47',
          600: '#2c2d3a',
          700: '#23242e',
          800: '#1a1b23',
          900: '#111218',
          950: '#0b0c10',
        },
        accent: {
          DEFAULT: '#e63946',
          light: '#ff4d5a',
          dark: '#c5303c',
        },
        danger: '#ef4444',
        success: '#22c55e',
        warning: '#f59e0b',
      },
    },
  },
  plugins: [],
}
