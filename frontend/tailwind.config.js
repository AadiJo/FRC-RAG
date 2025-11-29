/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html",
        "./templates/**/*.html",
        "./static/**/*.js",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Shadcn-inspired color system
                border: "hsl(0 0% 20%)",
                input: "hsl(0 0% 20%)",
                ring: "hsl(217 91% 60%)",
                background: "hsl(0 0% 8%)",
                foreground: "hsl(0 0% 98%)",
                primary: {
                    DEFAULT: "hsl(217 91% 60%)",
                    foreground: "hsl(0 0% 100%)",
                },
                secondary: {
                    DEFAULT: "hsl(0 0% 13%)",
                    foreground: "hsl(0 0% 98%)",
                },
                destructive: {
                    DEFAULT: "hsl(0 72% 51%)",
                    foreground: "hsl(0 0% 98%)",
                },
                muted: {
                    DEFAULT: "hsl(0 0% 15%)",
                    foreground: "hsl(0 0% 71%)",
                },
                accent: {
                    DEFAULT: "hsl(217 91% 60%)",
                    foreground: "hsl(0 0% 98%)",
                },
                popover: {
                    DEFAULT: "hsl(0 0% 8%)",
                    foreground: "hsl(0 0% 98%)",
                },
                card: {
                    DEFAULT: "hsl(0 0% 10%)",
                    foreground: "hsl(0 0% 98%)",
                },
            },
            borderRadius: {
                lg: "0.5rem",
                md: "calc(0.5rem - 2px)",
                sm: "calc(0.5rem - 4px)",
            },
            keyframes: {
                fadeInUp: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideIn: {
                    '0%': { transform: 'translateX(-100%)' },
                    '100%': { transform: 'translateX(0)' },
                },
                pulse: {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.5' },
                },
            },
            animation: {
                fadeInUp: 'fadeInUp 0.3s ease-out',
                slideIn: 'slideIn 0.3s ease-out',
                pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
        },
    },
    plugins: [],
}
