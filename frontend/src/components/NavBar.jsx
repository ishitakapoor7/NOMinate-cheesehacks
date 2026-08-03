import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Avatar } from './Avatar';

export function Wordmark({ dark = false }) {
  return (
    <span className="flex items-end gap-1">
      <span
        className={`font-display text-[28px] leading-none uppercase ${dark ? 'text-paper' : 'text-ink'}`}
      >
        NOM
      </span>
      <span className="mb-[2px] h-2 w-2 bg-yellow border border-ink" />
    </span>
  );
}

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="flex items-center justify-between border-b-2 border-ink px-5 py-4 sm:px-8 sm:py-5 lg:px-12">
      <Link to="/nominate" aria-label="NOMinate home">
        <Wordmark />
      </Link>
      <nav className="flex items-center gap-4 font-mono text-sm tracking-caps sm:gap-8">
        <Link
          to="/profile"
          className="flex items-center gap-2.5 text-ink hover:underline underline-offset-4"
        >
          <Avatar value={user?.avatar_url} name={user?.username} size={28} />
          <span className="hidden sm:inline">
            {user?.username ? user.username.toUpperCase() : 'MY PROFILE'}
          </span>
        </Link>
        <button
          type="button"
          onClick={() => {
            logout();
            navigate('/login');
          }}
          className="text-gray hover:text-ink hover:underline underline-offset-4"
        >
          LOG OUT
        </button>
      </nav>
    </header>
  );
}
