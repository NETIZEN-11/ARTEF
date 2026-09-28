if (typeof window !== 'undefined') {
  const originalError = console.error;
  console.error = (...args: any[]) => {
    const errorString = args.join(' ');
    const suppressedPatterns = [
      'Cannot read properties of undefined',
      'startTime',
      'web-vitals',
      'reportAllChanges',
      'et.reportAllChanges',
      'VM',
      '<anonymous>:2:',
    ];
    const shouldSuppress = suppressedPatterns.some(pattern => 
      errorString.includes(pattern)
    );
    if (!shouldSuppress) {
      originalError.apply(console, args);
    }
  };
  window.addEventListener('error', (event) => {
    const errorMessage = event.message || '';
    const errorSource = event.filename || '';
    if (
      errorMessage.includes('startTime') || 
      errorMessage.includes('web-vitals') ||
      errorMessage.includes('reportAllChanges') ||
      errorSource.includes('<anonymous>') ||
      errorSource.includes('VM')
    ) {
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  }, true);
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason?.message || String(event.reason) || '';
    if (
      reason.includes('startTime') || 
      reason.includes('web-vitals') ||
      reason.includes('reportAllChanges')
    ) {
      event.preventDefault();
      return false;
    }
  });
}
export {};
