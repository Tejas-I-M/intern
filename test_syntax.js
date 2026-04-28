const fs = require('fs');
const file = './ai-bi-chatbot-project-main/Team5_module/frontend/js/views/AdvancedView.js';
let content = fs.readFileSync(file, 'utf8');

// Replace all combinations of backticks at the end of the render string to be exactly one
content = content.replace(/<\/section>([\\\\s]+);/, '</section>\;');

// Write back
fs.writeFileSync(file, content, 'utf8');

// Verify parse tree
try {
    const vm = require('vm');
    new vm.Script(content);
    console.log("Syntax is valid!");
} catch (e) {
    console.error("Syntax Error:", e);
}
