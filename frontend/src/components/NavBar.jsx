import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

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
  const { logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="flex items-center justify-between border-b-2 border-ink px-12 py-5">
      <Link to="/nominate" aria-label="NOMinate home">
        <Wordmark />
      </Link>
      <nav className="flex items-center gap-8 font-mono text-sm tracking-caps">
        <Link to="/profile" className="text-ink hover:underline underline-offset-4">
          MY PROFILE
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
