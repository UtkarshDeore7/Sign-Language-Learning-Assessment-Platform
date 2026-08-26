/**
 * ASL Platform — Environment Configuration
 * ==========================================
 * Change API_BASE here for different environments.
 * This file is loaded BEFORE index.html's inline script,
 * so window.API_BASE is available when the app initialises.
 *
 * Development:  http://localhost:8000/api
 * Docker:       http://localhost:8000/api  (nginx proxies /api to backend)
 * Production:   https://your-domain.com/api
 */
window.API_BASE = 'http://localhost:8000/api';