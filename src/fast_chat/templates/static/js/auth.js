
function switchForm(form) {
    const loginForm = document.querySelector('.login-form');
    const registerForm = document.querySelector('.register-form');

    if (form === 'register') {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        registerForm.classList.add('active-form');
        loginForm.classList.remove('active-form');
    } else {
        registerForm.style.display = 'none';
        loginForm.style.display = 'block';
        loginForm.classList.add('active-form');
        registerForm.classList.remove('active-form');
    }
}

function extractError(result, status) {
    if (result && result.detail) return result.detail;
    if (result && result.message) return result.message;
    return `Ошибка сервера (${status}). Попробуйте позже.`;
}

document.getElementById('loginForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    try {
        const response = await fetch('/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
            body: new URLSearchParams({ username: email, password }),
        });
        const result = await response.json().catch(() => null);
        if (response.ok) {
            window.location.href = '/';
        } else {
            showToast(extractError(result, response.status), 'error');
        }
    } catch (err) {
        console.error('Login error:', err);
        showToast('Нет связи с сервером. Проверьте соединение.', 'error');
    }
});

document.getElementById('registerForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const telegram = document.getElementById('telegram').value;
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (password !== confirmPassword) {
        showToast('Пароли не совпадают', 'error');
        return;
    }

    try {
        const response = await fetch('/v1/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name: name,
                email,
                telegram_unic_code: telegram,
                password,
                repeat_password: confirmPassword,
            }),
        });
        const result = await response.json().catch(() => null);
        if (response.ok) {
            showToast(result?.message || 'Регистрация выполнена успешно! Войдите в систему.', 'success');
        } else {
            showToast(extractError(result, response.status), 'error');
        }
    } catch (err) {
        console.error('Register error:', err);
        showToast('Нет связи с сервером. Проверьте соединение.', 'error');
    }
});
