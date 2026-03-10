/**
 * API Configuration Module
 * Provides dynamic API base URL based on environment
 * Replaces hardcoded http://127.0.0.1:5000
 */

// Detect API base URL dynamically
function getAPIBaseURL() {
    // Check if we're in development or production
    const host = window.location.hostname;
    const protocol = window.location.protocol;
    
    // If running on localhost/127.0.0.1, use http://localhost:5000
    if (host === 'localhost' || host === '127.0.0.1') {
        return `${protocol}//localhost:5000`;
    }
    
    // For other hosts, assume same protocol and host
    // but you can customize this logic
    return `${protocol}//${host}`;
}

// Global API base URL
const API_BASE_URL = getAPIBaseURL();

// For backwards compatibility with existing code using API_URL or API
const API_URL = API_BASE_URL;
const API = API_BASE_URL;

console.log('[ZomaClone] API Base URL:', API_BASE_URL);

/**
 * Fetch wrapper with error handling
 * All API calls should use this
 */
async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            console.error(`[API Error] ${endpoint}:`, data);
        }
        
        return {
            ok: response.ok,
            status: response.status,
            data: data
        };
    } catch (error) {
        console.error(`[API Exception] ${endpoint}:`, error);
        return {
            ok: false,
            status: 0,
            error: error.message,
            data: { success: false, message: 'Network error: ' + error.message }
        };
    }
}

/**
 * Standard GET request
 */
async function apiGet(endpoint) {
    return apiFetch(endpoint, { method: 'GET' });
}

/**
 * Standard POST request
 */
async function apiPost(endpoint, data) {
    return apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

/**
 * Standard PUT request
 */
async function apiPut(endpoint, data) {
    return apiFetch(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

/**
 * Standard DELETE request
 */
async function apiDelete(endpoint) {
    return apiFetch(endpoint, { method: 'DELETE' });
}

// Export for modern JavaScript modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        API_BASE_URL,
        API_URL,
        API,
        apiFetch,
        apiGet,
        apiPost,
        apiPut,
        apiDelete
    };
}
