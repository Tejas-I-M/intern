const fs = require('fs');
let code = fs.readFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/services/real_analytics_service.py', 'utf8');

code = code.replace(/region_candidates = \[col for col in df\.columns\s*if col\.lower\(\) in \[.*?\]\]/g, 
  "region_keywords = ['region', 'location', 'country', 'city', 'state', 'province', 'area', 'zone']\n                region_candidates = [col for col in df.columns if any(k in col.lower() for k in region_keywords)]");

code = code.replace(/amount_candidates = \[col for col in df\.columns\s*if col\.lower\(\) in \[.*?\]\]/g, 
  "amount_keywords = ['amount', 'revenue', 'total', 'sales', 'total amount', 'price', 'value']\n                amount_candidates = [col for col in df.columns if any(k in col.lower() for k in amount_keywords)]");

code = code.replace(/customer_candidates = \[col for col in df\.columns\s*if col\.lower\(\) in \[.*?\]\]/g, 
  "customer_keywords = ['customer', 'customer id', 'customer_id', 'client', 'buyer', 'id']\n                customer_candidates = [col for col in df.columns if any(k in col.lower() for k in customer_keywords)]");

fs.writeFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/services/real_analytics_service.py', code);
console.log('Regex Replaced all correctly!');