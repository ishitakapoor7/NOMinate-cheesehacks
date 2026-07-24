import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import BrandPanel from '../components/BrandPanel';
import GoogleButton from '../components/GoogleButton';
import { Wordmark } from '../components/NavBar';

export default function SignUpPage() {
  const { signup, googleSignIn } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      await signup(username, email, password);
      navigate('/setup');
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function handleGoogle(credential) {
    setError('');
    try {
      const user = await googleSignIn(credential);
      navigate(user.has_profile ? '/nominate' : '/setup');
    } catch (err) {
      setError(err.response?.data?.error || 'Google sign-up failed. Try again.');
    }
  }

  return (
    <div className="flex min-h-screen">
      <BrandPanel />

      <main className="flex flex-grow items-center justify-center px-6 py-12">
        <div className="w-full max-w-[420px]">
          <Wordmark />
          <h2 className="mt-10 text-[28px] font-semibold text-ink">Create your account</h2>
          <p className="mt-2 text-gray">
            Tell us your tastes once — get a fresh nomination every day.
          </p>

          {error && (
            <p role="alert" className="mt-6 border-2 border-red px-4 py-3 text-sm text-red">
              {error}
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-6">
            <label className="flex flex-col gap-2">
              <span className="font-mono text-xs tracking-caps text-ink">USERNAME</span>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="nom_champion"
                className="h-14 border-2 border-ink px-4 text-base placeholder:text-gray/60"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className="font-mono text-xs tracking-caps text-ink">EMAIL</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@college.edu"
                className="h-14 border-2 border-ink px-4 text-base placeholder:text-gray/60"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className="font-mono text-xs tracking-caps text-ink">PASSWORD</span>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                className="h-14 border-2 border-ink px-4 text-base placeholder:text-gray/60"
              />
            </label>

            <button
              type="submit"
              disabled={busy}
              className="h-14 bg-ink font-semibold text-paper shadow-sticker-yellow transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-60"
            >
              {busy ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <div className="mt-6">
            <GoogleButton onCredential={handleGoogle} text="signup_with" />
          </div>

          <p className="mt-8 text-center text-gray">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-ink underline underline-offset-4">
              Log in
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
