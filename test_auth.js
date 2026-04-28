const http = require('http');

const run = async () => {
    try {
        const signupRes = await fetch('http://127.0.0.1:5000/api/auth/signup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: 'test5@example.com', password: 'password123', firstName: 'Abcd', lastName: 'Efgh'})
        });
        console.log('Signup:', await signupRes.json());
        
        const loginRes = await fetch('http://127.0.0.1:5000/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: 'test5@example.com', password: 'password123'})
        });
        console.log('Login:', await loginRes.json());
    } catch(err) {
        console.error(err);
    }
};
run();
