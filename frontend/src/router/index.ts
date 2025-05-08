import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Import views
const Home = () => import('../views/Home.vue')
const Login = () => import('../views/Login.vue')

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Wait for auth to initialize on first navigation
  if (!authStore.user && !authStore.loading) {
    await authStore.initialize()
  }
  
  // Handle protected routes
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } 
  // Prevent authenticated users from accessing login page
  else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next('/')
  }
  else {
    next()
  }
})

export default router