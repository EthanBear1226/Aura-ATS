const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;
const html = fs.readFileSync('add-job.html', 'utf8');

const dom = new JSDOM(html);
const document = dom.window.document;
const s = document.getElementById('jobDepartment');
console.log('Is jobDepartment present in raw DOM?', !!s);
if (s) {
    console.log('HTML:', s.outerHTML);
} else {
    const mainContent = document.querySelector('.main-content');
    console.log('mainContent length:', mainContent ? mainContent.innerHTML.length : 'N/A');
}
