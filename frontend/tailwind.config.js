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
        cyan: {
          400: '#22d3ee',
          500: '#06b6d4',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(230, 57, 70, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(230, 57, 70, 0.4)' },
        },
      },
    },
  },
  plugins: [],
}
