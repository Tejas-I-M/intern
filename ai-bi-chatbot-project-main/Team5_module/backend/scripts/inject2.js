const fs = require('fs');
let code = fs.readFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/api/analysis_routes.py', 'utf8');

const injection = `
@analysis_bp.after_request
def save_advanced_outputs(response):
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
        
        path = request.path
        if '/api/analysis/' in path and response.status_code == 200 and response.is_json:
            path_parts = path.strip('/').split('/')
            
            advanced_keys = [
               'cohort-analysis', 'geographic-analysis', 'timeseries-analysis', 'churn-prediction',
               'sales-forecast', 'product-affinity', 'clv', 'repeat-purchase',
               'health-score', 'anomalies', 'product-performance', 'promotional-impact'
            ]
            
            for key in advanced_keys:
                if key in path_parts:
                    file_id = None
                    for part in path_parts:
                        if len(part) >= 15:  # heuristic for file_id
                            file_id = part
                            break
                    if file_id and user_id in user_analyses and file_id in user_analyses[user_id]:
                        if 'advanced_outputs' not in user_analyses[user_id][file_id]:
                            user_analyses[user_id][file_id]['advanced_outputs'] = {}
                        
                        dict_key = path.split('/api/analysis/')[-1].split('/')[0]
                        user_analyses[user_id][file_id]['advanced_outputs'][dict_key] = response.get_json()
    except Exception as e:
        import traceback
        traceback.print_exc()
        pass
    return response
`;

const replaceLocation = 'analysis_bp = Blueprint(\'analysis\', __name__, url_prefix=\'/api/analysis\')';
if (code.includes(replaceLocation) && !code.includes('save_advanced_outputs')) {
    code = code.replace(replaceLocation, replaceLocation + '\n\n' + injection);
    fs.writeFileSync('c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/api/analysis_routes.py', code);
    console.log('Injected advanced outputs interceptor');
} else {
    console.log('Failed to inject or already injected');
}
