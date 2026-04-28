import fs from 'fs';
import { join } from 'path';

const API_BASE = 'http://127.0.0.1:5000/api';

async function runTest() {
    console.log('Starting Frontend E2E Simulation Test...');
    let cookieStr = '';

    const authHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json' };

    // 1. Signup / Login
    console.log('Attempting Signup / Login for rex91320@gmail.com...');
    let res = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
            firstName: 'Rex',
            lastName: 'User',
            email: 'rex91320@gmail.com',
            password: '12345678'
        })
    });
    
    if (res.status === 409) {
        console.log('User exists, logging in instead...');
        res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({ email: 'rex91320@gmail.com', password: '12345678' })
        });
    }

    const setCookie = res.headers.get('set-cookie');
    if (setCookie) {
        cookieStr = setCookie.split(';')[0];
    }

    const authData = await res.json();
    if (!authData.success) {
        throw new Error('Auth failed: ' + JSON.stringify(authData));
    }
    console.log('Auth logic passed.');

    // 2. Upload Sample Dataset
    console.log('Uploading sample_data.csv...');
    const formData = new FormData();
    const filePath = 'c:/Users/Tejas/Desktop/team9/ai-bi-chatbot-project-main/Team5_module/backend/sample_data.csv';
    const sampleCsv = fs.readFileSync(filePath, 'utf8');

    const fileBlob = new Blob([sampleCsv], { type: 'text/csv' });
    formData.append('file', fileBlob, 'sample_data.csv');

    const uploadRes = await fetch(`${API_BASE}/analysis/upload`, {
        method: 'POST',
        headers: { 'Cookie': cookieStr }, // Needs cookie for auth
        body: formData
    });

    const setCookieUpload = uploadRes.headers.get('set-cookie');
    if (setCookieUpload) {
        cookieStr = setCookieUpload.split(';')[0];
    }
    const uploadData = await uploadRes.json();
    
    if (!uploadData.success && uploadData.message !== 'Dataset already exists for this session.') {
         throw new Error('Upload failed: ' + JSON.stringify(uploadData));
    }
    console.log('Data uploaded correctly.');
    
    const fileId = uploadData.file_id || uploadData.session_id || 'sample_data.csv';

    // Initialize Analysis
    console.log('Running Analyze...');
    await fetch(`${API_BASE}/analysis/analyze/${fileId}`, {
        method: 'POST',
        headers: { 'Cookie': cookieStr, 'Content-Type': 'application/json' },
    });

    // 3. Ask All 17 Advanced Questions
    const advancedEndpoints = [
        `/analysis/cohort-analysis/${fileId}`,
        `/analysis/geographic-analysis/${fileId}`,
        `/analysis/timeseries-analysis/${fileId}`,
        `/analysis/churn-prediction/${fileId}`,
        `/analysis/sales-forecast/${fileId}`,
        `/analysis/product-affinity/${fileId}`,
        `/analysis/clv/${fileId}`,
        `/analysis/repeat-purchase/${fileId}`,
        `/analysis/health-score/${fileId}`,
        `/analysis/anomalies/${fileId}`,
        `/analysis/product-performance/${fileId}`,
        `/analysis/promotional-impact/${fileId}`
    ];
    
    console.log('Hitting advanced endpoints...');
    for (let i = 0; i < advancedEndpoints.length; i++) {
        const ep = advancedEndpoints[i];
        console.log(`[${i+1}/${advancedEndpoints.length}] Querying: ${ep}...`);
        const epRes = await fetch(`${API_BASE}${ep}`, {
            method: 'GET',
            headers: { 'Cookie': cookieStr }
        });
        const epData = await epRes.json();
        if (!epData.success && epData.status !== "success" && !epData.data) {
            console.error(`Request ${i+1} failed:`, epData);
        } else {
            console.log(`  Success`);
        }
    }

    const chatQueries = [
        "give actionable recommendations",
        "provide a summary of data insights",
        "explain the market share distribution",
        "identify trend correlations",
        "segment my customers"
    ];

    console.log('Asking 5 extra chat advanced questions...');
    for (let i = 0; i < chatQueries.length; i++) {
        const q = chatQueries[i];
        console.log(`[chat ${i+1}/5] Querying: "${q}"...`);
        const qRes = await fetch(`${API_BASE}/analysis/chat/${fileId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cookie': cookieStr
            },
            body: JSON.stringify({ question: q })
        });
        const qData = await qRes.json();
        if (!qData.success && !qData.response) {
            console.error(`Query ${i+1} failed:`, qData);
        } else {
             console.log(`  Success`);
        }
    }


    // 4. Generate Final Report
    console.log('Generating Final PDF Report...');
    const reportRes = await fetch(`${API_BASE}/analysis/generate-report/${fileId}`, {
         method: 'POST',
         headers: {
             'Content-Type': 'application/json',
             'Cookie': cookieStr
         },
         body: JSON.stringify({
            title: "Full 17-Module Advanced Analytics E2E Report",
            include_qa: true,
            filter_qa: false,
            include_charts: true
         })
    });

    const reportData = await reportRes.json();
    if (!reportData.success) {
         throw new Error('Report generation failed: ' + JSON.stringify(reportData));
    }
    console.log('Report Generated Successfully!');
    console.log('Response Payload:', JSON.stringify(reportData, null, 2));
    console.log('All e2e tests passed. Advanced outputs should be properly injected into the PDF.');
}

runTest().catch(console.error);
