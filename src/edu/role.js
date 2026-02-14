window.GrokRole = 'student';
if (window.location.hash.includes('teacher')) GrokRole = 'teacher';
localStorage.setItem('grok_role', GrokRole);