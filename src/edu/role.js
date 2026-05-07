(() => {
  const isBrowser = typeof window !== 'undefined' && typeof window.document !== 'undefined';

  const hasTeacherFlag = isBrowser
    ? Boolean(window.location && typeof window.location.hash === 'string' && window.location.hash.includes('teacher'))
    : process.argv.some((arg) => arg.includes('teacher'));

  const role = hasTeacherFlag ? 'teacher' : 'student';

  if (isBrowser) {
    window.GrokRole = role;
    if (typeof localStorage !== 'undefined') localStorage.setItem('grok_role', role);
    return;
  }

  globalThis.GrokRole = role;
  process.env.GROK_ROLE = role;
  process.stdout.write(`${role}\n`);
})();
