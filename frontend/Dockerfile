FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./
RUN npm install

# Install Tailwind CSS v3 and its dependencies
RUN npm uninstall tailwindcss @tailwindcss/postcss
RUN npm install -D tailwindcss@3 postcss autoprefixer

# Copy the rest of the application
COPY . .

RUN npm install -D @vue/tsconfig
# Fix App.vue
RUN echo '<template><router-view /></template>' > src/App.vue

# Create PostCSS config as CommonJS
RUN echo "module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };" > postcss.config.cjs

# Create Tailwind config as CommonJS
RUN echo "/** @type {import('tailwindcss').Config} */ module.exports = { content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'], theme: { extend: {} }, plugins: [] };" > tailwind.config.cjs

# Ensure CSS file exists
RUN mkdir -p src/assets
RUN echo "@tailwind base; @tailwind components; @tailwind utilities;" > src/assets/main.css

# Create TypeScript config files if they don't exist
RUN echo '{ "compilerOptions": { "target": "ES2020", "useDefineForClassFields": true, "module": "ESNext", "lib": ["ES2020", "DOM", "DOM.Iterable"], "skipLibCheck": true, "moduleResolution": "bundler", "allowImportingTsExtensions": true, "resolveJsonModule": true, "isolatedModules": true, "noEmit": true, "jsx": "preserve", "strict": true, "noUnusedLocals": true, "noUnusedParameters": true, "noFallthroughCasesInSwitch": true }, "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"], "references": [{ "path": "./tsconfig.node.json" }] }' > tsconfig.json

# Node config
RUN echo '{ "compilerOptions": { "composite": true, "skipLibCheck": true, "module": "ESNext", "moduleResolution": "bundler", "allowSyntheticDefaultImports": true }, "include": ["vite.config.ts"] }' > tsconfig.node.json



EXPOSE 5173

CMD ["npm", "run", "dev"]