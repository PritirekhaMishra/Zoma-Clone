/* ========================================
   THEME MANAGER
   ZomaClone - Premium Nightlife
======================================== */

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
  // Check for saved theme preference, default to dark
  const savedTheme = localStorage.getItem('theme') || 'dark';
  
  if (savedTheme === 'light') {
    document.body.classList.add('light');
    updateThemeButton(true);
  } else {
    document.body.classList.remove('light');
    updateThemeButton(false);
  }
});

// Toggle theme function (called from button onclick)
function toggleTheme() {
  const isLight = document.body.classList.toggle('light');
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
  updateThemeButton(isLight);
}

// Update button text/icon based on current theme
function updateThemeButton(isLight) {
  const themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    if (isLight) {
      themeBtn.innerHTML = '<i class="fas fa-moon"></i> Night';
    } else {
      themeBtn.innerHTML = '<i class="fas fa-sun"></i> Day';
    }
  }
}

// Also update when DOM is fully loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    updateThemeButton(document.body.classList.contains('light'));
  });
} else {
  updateThemeButton(document.body.classList.contains('light'));
}
