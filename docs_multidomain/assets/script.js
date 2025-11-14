// Genropy Multidomain Workspace - Interactive Scripts

document.addEventListener('DOMContentLoaded', function() {
    // Initialize syntax highlighting
    if (typeof hljs !== 'undefined') {
        hljs.highlightAll();
    }

    // Set active menu item based on current page
    setActiveMenuItem();

    // Mobile menu toggle
    setupMobileMenu();

    // Smooth scroll for anchor links
    setupSmoothScroll();

    // Collapsible sections
    setupCollapsibleSections();

    // Copy code button
    setupCodeCopyButtons();

    // Search functionality
    setupSearch();
});

/**
 * Set active menu item based on current page
 */
function setActiveMenuItem() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const menuLinks = document.querySelectorAll('.nav-menu a');

    menuLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });
}

/**
 * Mobile menu toggle
 */
function setupMobileMenu() {
    // Create hamburger button for mobile
    if (window.innerWidth <= 1024) {
        const hamburger = document.createElement('button');
        hamburger.className = 'mobile-menu-toggle';
        hamburger.innerHTML = '☰';
        hamburger.style.cssText = `
            position: fixed;
            top: 1rem;
            left: 1rem;
            z-index: 1001;
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            font-size: 1.5rem;
            cursor: pointer;
            display: none;
        `;

        if (window.innerWidth <= 1024) {
            hamburger.style.display = 'block';
        }

        document.body.appendChild(hamburger);

        const sidebar = document.querySelector('.sidebar');
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !hamburger.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }
}

/**
 * Smooth scroll for anchor links
 */
function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Collapsible sections
 */
function setupCollapsibleSections() {
    const collapsibleHeaders = document.querySelectorAll('[data-collapsible]');

    collapsibleHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.style.userSelect = 'none';

        // Add indicator
        const indicator = document.createElement('span');
        indicator.textContent = ' ▼';
        indicator.style.transition = 'transform 0.3s';
        header.appendChild(indicator);

        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            const isHidden = content.style.display === 'none';

            content.style.display = isHidden ? 'block' : 'none';
            indicator.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
        });
    });
}

/**
 * Add copy buttons to code blocks
 */
function setupCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre code');

    codeBlocks.forEach((block, index) => {
        const pre = block.parentElement;
        pre.style.position = 'relative';

        const button = document.createElement('button');
        button.textContent = 'Copy';
        button.className = 'code-copy-btn';
        button.style.cssText = `
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 0.25rem 0.75rem;
            border-radius: 0.25rem;
            cursor: pointer;
            font-size: 0.75rem;
            opacity: 0;
            transition: opacity 0.2s;
        `;

        pre.style.paddingTop = '2.5rem';
        pre.appendChild(button);

        pre.addEventListener('mouseenter', () => {
            button.style.opacity = '1';
        });

        pre.addEventListener('mouseleave', () => {
            button.style.opacity = '0';
        });

        button.addEventListener('click', async () => {
            const code = block.textContent;
            try {
                await navigator.clipboard.writeText(code);
                button.textContent = 'Copied!';
                setTimeout(() => {
                    button.textContent = 'Copy';
                }, 2000);
            } catch (err) {
                console.error('Failed to copy:', err);
                button.textContent = 'Failed';
                setTimeout(() => {
                    button.textContent = 'Copy';
                }, 2000);
            }
        });
    });
}

/**
 * Simple search functionality
 */
function setupSearch() {
    // This is a placeholder for search functionality
    // In a real implementation, you would index all content and provide search results
    console.log('Search functionality ready (placeholder)');
}

/**
 * Highlight external links
 */
function highlightExternalLinks() {
    const links = document.querySelectorAll('a[href^="http"]');
    links.forEach(link => {
        if (!link.href.includes(window.location.hostname)) {
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
            link.innerHTML += ' ↗';
        }
    });
}

/**
 * Add anchor links to headings
 */
function addAnchorLinks() {
    const headings = document.querySelectorAll('h2, h3, h4');
    headings.forEach(heading => {
        if (heading.id) {
            const anchor = document.createElement('a');
            anchor.href = `#${heading.id}`;
            anchor.className = 'anchor-link';
            anchor.textContent = '#';
            anchor.style.cssText = `
                margin-left: 0.5rem;
                color: var(--primary-color);
                text-decoration: none;
                opacity: 0;
                transition: opacity 0.2s;
            `;
            heading.appendChild(anchor);

            heading.addEventListener('mouseenter', () => {
                anchor.style.opacity = '1';
            });

            heading.addEventListener('mouseleave', () => {
                anchor.style.opacity = '0';
            });
        }
    });
}

// Initialize additional features
highlightExternalLinks();
addAnchorLinks();

// Handle window resize
window.addEventListener('resize', () => {
    const hamburger = document.querySelector('.mobile-menu-toggle');
    if (hamburger) {
        hamburger.style.display = window.innerWidth <= 1024 ? 'block' : 'none';
    }
});
