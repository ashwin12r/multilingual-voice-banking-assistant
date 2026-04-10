import { useState } from 'react';
import { useStore } from '../store/useStore';

export default function LoginForm() {
  const setToken = useStore((state) => state.setToken);
  const [email, setEmail] = useState('ashwin@aurex.com');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await fetch('http://127.0.0.1:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });

      if (!res.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await res.json();
      setToken(data.access_token);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-950 items-center justify-center p-4 selection:bg-teal-500 font-sans">
      <div className="w-full max-w-md bg-gray-900 rounded-3xl border border-gray-800 shadow-2xl p-8 transform transition-all">
        <div className="text-center mb-10">
          <div className="bg-yellow-500 text-gray-950 font-bold p-3 rounded-xl text-3xl flex items-center justify-center h-16 w-16 mx-auto mb-4 shadow-lg shadow-yellow-500/20 shadow-[0_0_20px_rgba(234,179,8,0.4)]">A</div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Login to AUR<span className="text-teal-400">EX</span></h1>
          <p className="text-gray-400 mt-2 text-sm">Welcome to your intelligent voice bank.</p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-sm p-3 rounded-xl mb-6 text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Email / Username</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl p-3.5 text-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all"
              required
            />
          </div>
          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl p-3.5 text-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-teal-500 hover:bg-teal-400 text-gray-950 font-bold text-lg py-3.5 rounded-xl shadow-lg shadow-teal-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Authenticating...' : 'Secure Login'}
          </button>
        </form>
      </div>
    </div>
  );
}