// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash');
    
    flashMessages.forEach(function(flash) {
        setTimeout(function() {
            flash.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(function() {
                flash.remove();
            }, 300);
        }, 5000);
    });
});

// Animation for slide out
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Confirm before removing favorite
document.querySelectorAll('form[action*="unfavorite"]').forEach(form => {
    form.addEventListener('submit', function(e) {
        if (!confirm('Remove this article from favorites?')) {
            e.preventDefault();
        }
    });
});

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Add scroll to top button if page is long
window.addEventListener('scroll', function() {
    if (window.scrollY > 500) {
        if (!document.querySelector('.scroll-top')) {
            const btn = document.createElement('button');
            btn.className = 'scroll-top';
            btn.innerHTML = '↑';
            btn.onclick = scrollToTop;
            document.body.appendChild(btn);
            
            // Add styles
            btn.style.cssText = `
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                font-size: 24px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                transition: all 0.3s;
                z-index: 999;
            `;
        }
    } else {
        const btn = document.querySelector('.scroll-top');
        if (btn) btn.remove();
    }
});