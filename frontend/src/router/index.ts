// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Import views
const Home = () => import('../views/Home.vue')
const Login = () => import('../views/Login.vue')
const AdminUsers = () => import('../views/AdminUsers.vue')  // Import the new admin view

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
  },
  // Admin routes
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: AdminUsers,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, _from, next) => {  // Changed 'from' to '_from' to indicate it's unused
  const authStore = useAuthStore()
  
  // Wait for auth to initialize on first navigation
  if (!authStore.user && !authStore.loading) {
    await authStore.initialize()
  }
  
  // Handle routes that require admin role
  if (to.meta.requiresAdmin && !(authStore.userProfile?.role_name === 'ADMIN')) {
    // Redirect non-admins attempting to access admin routes
    next('/')
    return
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