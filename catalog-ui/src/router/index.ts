import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import DomainView from '@/views/DomainView.vue'
import TableView from '@/views/TableView.vue'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/domain/:id', name: 'domain', component: DomainView },
    { path: '/domain', name: 'domain-all', component: DomainView },
    { path: '/table/:id', name: 'table', component: TableView },
  ],
})

export default router
