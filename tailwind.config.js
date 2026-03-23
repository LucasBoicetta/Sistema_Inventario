/** @type {import('tailwindcss').Config} */
module.exports = {
  // Le dice a Tailwind dónde buscar clases para generar el CSS
  darkMode: "class", // Habilita el modo oscuro basado en una clase CSS
  content: [
    "./app/templates/**/*.html",           // Templates globales (base.html, index.html)
    "./app/modules/**/templates/**/*.html", // Templates de cada módulo (auth, inventory, orders)
    "./app/static/js/**/*.js"              // Clases CSS referenciadas en JavaScript
  ],
  theme: {
    extend: {
      // Paleta de colores del diseño INSTISTOCK
      colors: {
        "primary": "#FACC15",
        "charcoal": {
          "950": "#121212",
          "900": "#1a1a1c",
          "800": "#222225",
          "700": "#2d2d31",
          "600": "#3f3f46"
        },
        "graphite": "#1c1c1e"
      },
      // Fuente principal
      fontFamily: {
        "display": ["Inter", "sans-serif"]
      },
      //borderRadius extendido.
      borderRadius: {
        "DEFAULT": "0.375rem",
        "lg": "0.5rem",
        "xl": "1rem",
        "2xl": "1.5rem"
      },
      // Sombra premium del diseño
      boxShadow: {
        "premium": "0 25px 50px -12px rgba(0, 0, 0, 0.7)"
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'), // Plugin para estilos de formularios
  ],
}