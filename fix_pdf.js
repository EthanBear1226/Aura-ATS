const fs = require('fs');
let html = fs.readFileSync('candidate-detail.html', 'utf8');

// In the catch block, if candidate.pdf_path is present, we should also try to load it!
// Because even if it's from sessionStorage, the file MIGHT still exist in the current container session.
html = html.replace(
    /\/\/ PDF Viewer Fallback[\s\S]*?<\/div>";/,
    `// PDF Viewer Fallback
                if (candidate.pdf_path) {
                    document.getElementById('pdf-viewer').src = \`\${candidate.pdf_path}\`;
                    document.getElementById('pdf-download-btn').href = \`\${candidate.pdf_path}\`;
                    document.getElementById('pdf-download-btn').style.display = 'inline-flex';
                } else {
                    document.getElementById('pdf-loading-fallback').style.display = 'none';
                    document.getElementById('pdf-viewer').srcdoc = "<div style='padding:20px;font-family:sans-serif;text-align:center;'><h4>演示模式 (脱机状态)</h4><p>当前运行在静态演示模式，无法加载本地 PDF 附件。</p></div>";
                }`
);

fs.writeFileSync('candidate-detail.html', html);
console.log('Fixed pdf logic in catch block');
