const fs = require('fs');
let code = fs.readFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/api/analysis_routes.py', 'utf8');

const target = "analysis_results['customer_summary'] = customer_summary";
const injection = `
    # Export advanced_outputs if they exist
    analysis_results['advanced_outputs'] = analysis_results.get('advanced_outputs', {})
`;

if (code.includes(target)) {
    code = code.replace(target, target + '\n' + injection);
    fs.writeFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/api/analysis_routes.py', code);
    console.log('Appended advanced_outputs to payload builder.');
} else {
    console.log('Target not found!');
}
