const fs = require('fs');
let html = fs.readFileSync('add-job.html', 'utf8');

// The issue is that setupCustomSelects() takes the <select> and transforms it into a custom div structure.
// Once transformed, modifying select.innerHTML DOES NOT update the custom UI!
// We need to re-render the custom UI, or modify the custom UI directly.

// Look at loadDictionaries, it's called BEFORE setupCustomSelects in DOMContentLoaded:
// await loadDictionaries();
// setupCustomSelects();

// Let's check how DOMContentLoaded is written.
