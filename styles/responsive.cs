/* styles/responsive.css - Responsive Design for Multi-Tenant Admin Panel */

/* ==================== RESPONSIVE BREAKPOINTS ==================== */
/* 
   Mobile-first approach with breakpoints:
   - Mobile: 320px - 768px
   - Tablet: 769px - 1024px  
   - Desktop: 1025px+
   - Large Desktop: 1400px+
*/

/* ==================== LARGE DESKTOP (1400px+) ==================== */
@media (min-width: 1400px) {
    .container {
        max-width: 1600px;
        padding: 0 var(--spacing-xl);
    }
    
    .main-title {
        font-size: var(--font-size-4xl);
    }
    
    .system-grid {
        grid-template-columns: repeat(4, 1fr);
    }
    
    .admin-grid {
        grid-template-columns: repeat(3, 1fr);
    }
    
    .card {
        padding: var(--spacing-xxl);
    }
}

/* ==================== DESKTOP (1025px - 1399px) ==================== */
@media (min-width: 1025px) and (max-width: 1399px) {
    .container {
        max-width: 1200px;
        padding: 0 var(--spacing-lg);
    }
    
    .system-grid {
        grid-template-columns: repeat(3, 1fr);
    }
    
    .admin-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* ==================== TABLET (769px - 1024px) ==================== */
@media (min-width: 769px) and (max-width: 1024px) {
    body {
        padding: var(--spacing-md);
    }
    
    .container {
        max-width: 100%;
        padding: 0;
    }
    
    /* Header adjustments */
    .header-content {
        flex-direction: column;
        gap: var(--spacing-md);
        text-align: center;
    }
    
    .main-title {
        font-size: var(--font-size-3xl);
        justify-content: center;
    }
    
    .company-selector {
        width: 100%;
        justify-content: center;
    }
    
    .company-select {
        width: 250px;
    }
    
    /* Grid adjustments */
    .system-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: var(--spacing-md);
    }
    
    .admin-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: var(--spacing-md);
    }
    
    /* Form adjustments */
    .form-row {
        flex-direction: column;
    }
    
    .form-group-small {
        flex: 1;
    }
    
    /* Action buttons */
    .action-buttons {
        justify-content: center;
        flex-wrap: wrap;
    }
    
    /* Chat messages */
    .chat-message {
        max-width: 90%;
    }
    
    /* Modal adjustments */
    .modal-content {
        max-width: 90vw;
        margin: var(--spacing-lg);
    }
    
    /* Toast adjustments */
    .toast-container {
        left: var(--spacing-md);
        right: var(--spacing-md);
        max-width: none;
    }
    
    /* Table adjustments */
    .table-container {
        font-size: var(--font-size-sm);
    }
    
    .data-table th,
    .data-table td {
        padding: var(--spacing-xs) var(--spacing-sm);
    }
}

/* ==================== MOBILE LANDSCAPE (568px - 768px) ==================== */
@media (min-width: 568px) and (max-width: 768px) and (orientation: landscape) {
    .main-header {
        padding: var(--spacing-lg);
    }
    
    .header-content {
        flex-direction: row;
        align-items: center;
    }
    
    .main-title {
        font-size: var(--font-size-2xl);
    }
    
    .company-selector {
        width: auto;
    }
    
    .system-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

/* ==================== MOBILE (320px - 768px) ==================== */
@media (max-width: 768px) {
    :root {
        /* Adjust spacing for mobile */
        --spacing-xs: 0.25rem;
        --spacing-sm: 0.375rem;
        --spacing-md: 0.75rem;
        --spacing-lg: 1rem;
        --spacing-xl: 1.25rem;
        --spacing-xxl: 1.5rem;
        
        /* Adjust font sizes for mobile */
        --font-size-xs: 0.7rem;
        --font-size-sm: 0.8rem;
        --font-size-base: 0.9rem;
        --font-size-lg: 1rem;
        --font-size-xl: 1.1rem;
        --font-size-2xl: 1.3rem;
        --font-size-3xl: 1.6rem;
        --font-size-4xl: 2rem;
    }
    
    body {
        padding: var(--spacing-sm);
        font-size: var(--font-size-base);
    }
    
    /* Container */
    .container {
        max-width: 100%;
        padding: 0;
    }
    
    /* Header mobile */
    .main-header {
        padding: var(--spacing-lg);
        margin-bottom: var(--spacing-lg);
    }
    
    .header-content {
        flex-direction: column;
        align-items: stretch;
        text-align: center;
        gap: var(--spacing-lg);
    }
    
    .main-title {
        font-size: var(--font-size-3xl);
        justify-content: center;
        line-height: 1.2;
    }
    
    .title-icon {
        font-size: var(--font-size-2xl);
    }
    
    .company-selector {
        justify-content: center;
        flex-direction: column;
        gap: var(--spacing-sm);
        padding: var(--spacing-md);
    }
    
    .company-select {
        min-width: auto;
        width: 100%;
    }
    
    /* Section titles */
    .section-title {
        font-size: var(--font-size-xl);
        text-align: center;
        margin-bottom: var(--spacing-lg);
    }
    
    /* Cards mobile */
    .card {
        padding: var(--spacing-lg);
        margin-bottom: var(--spacing-md);
    }
    
    .card-header {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
    }
    
    .card-title {
        font-size: var(--font-size-lg);
    }
    
    .card-actions {
        width: 100%;
        justify-content: center;
    }
    
    /* Grid mobile */
    .system-grid {
        grid-template-columns: 1fr;
        gap: var(--spacing-md);
    }
    
    .admin-grid {
        grid-template-columns: 1fr;
        gap: var(--spacing-md);
    }
    
    /* Forms mobile */
    .form-row {
        flex-direction: column;
        gap: var(--spacing-sm);
    }
    
    .form-group-small {
        flex: 1;
    }
    
    .form-actions {
        flex-direction: column;
        gap: var(--spacing-sm);
        text-align: center;
    }
    
    .form-textarea {
        min-height: 100px;
        font-size: var(--font-size-base);
    }
    
    /* Buttons mobile */
    .action-buttons {
        justify-content: center;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
    }
    
    .button-group {
        justify-content: center;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
    }
    
    .btn {
        font-size: var(--font-size-sm);
        padding: var(--spacing-sm) var(--spacing-md);
    }
    
    .btn-sm {
        padding: var(--spacing-xs) var(--spacing-sm);
        font-size: var(--font-size-xs);
    }
    
    /* Admin buttons mobile */
    .admin-buttons {
        gap: var(--spacing-xs);
    }
    
    .admin-buttons .btn {
        justify-content: center;
        text-align: center;
    }
    
    /* Chat mobile */
    .chat-messages {
        max-height: 300px;
        font-size: var(--font-size-sm);
    }
    
    .chat-message {
        max-width: 95%;
        padding: var(--spacing-sm);
        font-size: var(--font-size-sm);
    }
    
    .chat-input-form .input-group {
        flex-direction: column;
        gap: var(--spacing-sm);
    }
    
    .chat-input {
        border-radius: var(--radius-md);
    }
    
    /* Multimedia controls mobile */
    .multimedia-controls {
        gap: var(--spacing-sm);
    }
    
    .control-group .button-group {
        flex-direction: column;
        gap: var(--spacing-xs);
    }
    
    .file-inputs {
        flex-direction: column;
        gap: var(--spacing-xs);
    }
    
    /* Modals mobile */
    .modal-content {
        max-width: 95vw;
        max-height: 90vh;
        margin: var(--spacing-sm);
    }
    
    .modal-header {
        padding: var(--spacing-md);
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
    }
    
    .modal-title {
        font-size: var(--font-size-lg);
    }
    
    .modal-body {
        padding: var(--spacing-md);
        max-height: 60vh;
    }
    
    .modal-footer {
        padding: var(--spacing-md);
        flex-direction: column;
        gap: var(--spacing-sm);
    }
    
    .modal-footer .btn {
        width: 100%;
        justify-content: center;
    }
    
    /* Camera modal mobile */
    .camera-modal .modal-content {
        max-width: 95vw;
    }
    
    .camera-container video {
        max-height: 250px;
    }
    
    /* Toast mobile */
    .toast-container {
        left: var(--spacing-sm);
        right: var(--spacing-sm);
        top: var(--spacing-sm);
        max-width: none;
    }
    
    .toast {
        padding: var(--spacing-sm) var(--spacing-md);
        font-size: var(--font-size-sm);
    }
    
    /* Tables mobile */
    .table-container {
        font-size: var(--font-size-xs);
        border-radius: var(--radius-sm);
    }
    
    .data-table th,
    .data-table td {
        padding: var(--spacing-xs) var(--spacing-sm);
        font-size: var(--font-size-xs);
    }
    
    .data-table th {
        font-size: var(--font-size-sm);
    }
    
    /* Document items mobile */
    .document-item {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
        padding: var(--spacing-md);
    }
    
    .document-actions {
        width: 100%;
        justify-content: center;
    }
    
    /* Search results mobile */
    .search-result {
        padding: var(--spacing-sm);
    }
    
    .search-result-score {
        font-size: var(--font-size-xs);
    }
    
    /* Status items mobile */
    .company-status {
        grid-template-columns: 1fr;
        gap: var(--spacing-sm);
    }
    
    .status-item {
        padding: var(--spacing-sm);
        text-align: center;
    }
    
    .status-label {
        font-size: var(--font-size-xs);
    }
    
    .status-value {
        font-size: var(--font-size-base);
    }
    
    /* Loading mobile */
    .loading-content {
        padding: var(--spacing-lg);
        margin: var(--spacing-md);
    }
    
    .loading-message {
        font-size: var(--font-size-base);
    }
    
    .progress-bar {
        width: 150px;
    }
    
    /* Company indicators mobile */
    .company-indicator {
        font-size: var(--font-size-xs);
        text-align: center;
    }
    
    /* Form help text mobile */
    .form-help {
        font-size: var(--font-size-xs);
        margin-top: var(--spacing-xs);
    }
}

/* ==================== SMALL MOBILE (320px - 480px) ==================== */
@media (max-width: 480px) {
    :root {
        /* Further reduce spacing for very small screens */
        --spacing-xs: 0.2rem;
        --spacing-sm: 0.3rem;
        --spacing-md: 0.6rem;
        --spacing-lg: 0.8rem;
        --spacing-xl: 1rem;
        --spacing-xxl: 1.2rem;
    }
    
    body {
        padding: var(--spacing-xs);
    }
    
    .main-header {
        padding: var(--spacing-md);
    }
    
    .main-title {
        font-size: var(--font-size-2xl);
        line-height: 1.1;
    }
    
    .card {
        padding: var(--spacing-md);
    }
    
    .btn {
        padding: var(--spacing-sm);
        font-size: var(--font-size-xs);
    }
    
    .form-control {
        padding: var(--spacing-sm);
        font-size: var(--font-size-sm);
    }
    
    .modal-content {
        max-width: 98vw;
        margin: var(--spacing-xs);
    }
    
    .toast {
        padding: var(--spacing-sm);
        font-size: var(--font-size-xs);
    }
    
    /* Very small screens optimizations */
    .company-selector {
        padding: var(--spacing-sm);
    }
    
    .data-table th,
    .data-table td {
        padding: 2px 4px;
        font-size: 0.65rem;
    }
    
    .chat-message {
        padding: var(--spacing-xs);
        font-size: var(--font-size-xs);
    }
}

/* ==================== LANDSCAPE ORIENTATION ==================== */
@media (orientation: landscape) and (max-height: 600px) {
    .modal-content {
        max-height: 95vh;
    }
    
    .modal-body {
        max-height: 70vh;
    }
    
    .chat-messages {
        max-height: 200px;
    }
    
    .camera-container video {
        max-height: 200px;
    }
}

/* ==================== HIGH DPI DISPLAYS ==================== */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
    /* Optimize for retina displays */
    .spinner {
        border-width: 2px;
    }
    
    .btn::before {
        border-width: 1px;
    }
    
    /* Ensure crisp edges on high DPI */
    .card,
    .btn,
    .form-control,
    .modal-content {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
}

/* ==================== DARK MODE SUPPORT (OPTIONAL) ==================== */
@media (prefers-color-scheme: dark) {
    :root {
        --white: #1a1a1a;
        --light-gray: #2d2d2d;
        --gray: #888888;
        --dark-gray: #cccccc;
        --dark: #ffffff;
        --darker: #f5f5f5;
    }
    
    body {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    }
    
    .glass-bg {
        background: rgba(20, 20, 20, 0.95);
    }
}

/* ==================== REDUCED MOTION SUPPORT ==================== */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
    
    .spinner {
        animation: none;
    }
    
    .loading-spinner .spinner {
        border: 4px solid var(--primary-color);
        border-top-color: transparent;
    }
}

/* ==================== PRINT STYLES ==================== */
@media print {
    body {
        background: white !important;
        color: black !important;
        font-size: 12pt;
    }
    
    .main-header,
    .action-buttons,
    .btn,
    .modal,
    .toast-container,
    .loading-overlay {
        display: none !important;
    }
    
    .card {
        border: 1px solid #ccc;
        box-shadow: none;
        break-inside: avoid;
        margin-bottom: 1rem;
    }
    
    .section-title {
        color: black !important;
        text-shadow: none;
    }
}
