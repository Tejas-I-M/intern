const fs = require('fs');
let code = fs.readFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/services/report_generator.py', 'utf8');

// For Markdown:
const mdTarget = `        if qa_entries:
            md_lines.extend([
                '',
                '---',
                '',
                '## 5. Q&A and Chat History Insights',
                ''
            ])`;

const mdReplacement = `        advanced_outputs = self.report_data.get('advanced_outputs', {})
        if advanced_outputs:
            md_lines.extend([
                '',
                '---',
                '',
                '## 5. Advanced Analytics',
                ''
            ])
            for mod_name, mod_data in advanced_outputs.items():
                md_lines.append(f'### {mod_name.title()}')
                if isinstance(mod_data, dict):
                    inner_data = mod_data.get('analysis') or mod_data.get('metrics') or mod_data.get('results') or mod_data.get('insights') or mod_data.get('cohorts') or mod_data.get('anomalies') or mod_data.get('recommendations') or mod_data.get('data') or mod_data
                    if isinstance(inner_data, dict):
                        for k, v in list(inner_data.items())[:12]:
                            md_lines.append(f'- **{k}**: {str(v)[:200]}')
                    elif isinstance(inner_data, list):
                        for item in inner_data[:5]:
                            if isinstance(item, dict):
                                line = ", ".join([f"{k}: {v}" for k, v in list(item.items())[:3]])
                                md_lines.append(f"- {line}")
                            else:
                                md_lines.append(f"- {str(item)[:200]}")
                    else:
                         md_lines.append(f"{str(inner_data)[:200]}")
                else:
                    md_lines.append(f"{str(mod_data)[:200]}")
                md_lines.append('')
        
        if qa_entries:
            md_lines.extend([
                '',
                '---',
                '',
                '## 6. Q&A and Chat History Insights',
                ''
            ])`;

code = code.replace(mdTarget, mdReplacement);

// For HTML:
const htmlTarget = `        if qa_entries:
            html_parts.extend([
                '<div class="section qa-section">',
                '<h2>Q&A and Chat History Insights</h2>'
            ])`;

const htmlReplacement = `        advanced_outputs = self.report_data.get('advanced_outputs', {})
        if advanced_outputs:
            html_parts.extend([
                '<div class="section advanced-section" style="page-break-before: always;">',
                '<h2>Advanced Analytics</h2>'
            ])
            for mod_name, mod_data in advanced_outputs.items():
                html_parts.append(f'<h3>{mod_name.title()}</h3>')
                html_parts.append('<ul>')
                if isinstance(mod_data, dict):
                    inner_data = mod_data.get('analysis') or mod_data.get('metrics') or mod_data.get('results') or mod_data.get('insights') or mod_data.get('cohorts') or mod_data.get('anomalies') or mod_data.get('recommendations') or mod_data.get('data') or mod_data
                    if isinstance(inner_data, dict):
                        for k, v in list(inner_data.items())[:12]:
                            html_parts.append(f'<li><strong>{k}</strong>: {str(v)[:200]}</li>')
                    elif isinstance(inner_data, list):
                        for item in inner_data[:5]:
                            if isinstance(item, dict):
                                line = ", ".join([f"{k}: {str(v)[:100]}" for k, v in list(item.items())[:3]])
                                html_parts.append(f"<li>{line}</li>")
                            else:
                                html_parts.append(f"<li>{str(item)[:200]}</li>")
                    else:
                        html_parts.append(f"<li>{str(inner_data)[:200]}</li>")
                else:
                    html_parts.append(f"<li>{str(mod_data)[:200]}</li>")
                html_parts.append('</ul>')
            html_parts.append('</div>')

        if qa_entries:
            html_parts.extend([
                '<div class="section qa-section" style="page-break-before: always;">',
                '<h2>Q&A and Chat History Insights</h2>'
            ])`;

// To ensure we get the right replacement we replace regex dynamically if exact match fails
if (!code.includes(mdTarget)) { console.log('mdTarget not found'); }
else { code = code.replace(mdTarget, mdReplacement); console.log("mdTarget injected"); }

if (!code.includes(htmlTarget)) { console.log('htmlTarget not found'); }
else { code = code.replace(htmlTarget, htmlReplacement); console.log("htmlTarget injected"); }

fs.writeFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/services/report_generator.py', code);
