/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.html", "./docs/*.html"],
  theme: {
    extend: {
      colors: {
        'indigo': {
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
        },
        'gray': {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        }
      }
    },
  },
  plugins: [],
}
