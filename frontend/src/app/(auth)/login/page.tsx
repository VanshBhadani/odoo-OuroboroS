'use client';
import { useState } from 'react';
import api from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

import Link from 'next/link';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post('/auth/login', {
        email: email,
        password: password
      });
      const userRes = await api.get('/auth/me', { headers: { Authorization: `Bearer ${res.data.access_token}` } });
      login(res.data.access_token, userRes.data);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? 'Validation Error: Check your inputs' : (detail || 'Login failed'));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <form onSubmit={handleLogin} className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6">StockSense Login</h1>
        {error && <div className="text-red-500 mb-4 text-sm">{error}</div>}
        <input className="w-full border p-2 mb-4 rounded" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
        <input className="w-full border p-2 mb-4 rounded" type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
        
        <div className="flex justify-between items-center mb-6">
          <Link href="/signup" className="text-sm text-blue-600 hover:underline">Create Account</Link>
          <Link href="/forgot-password" className="text-sm text-blue-600 hover:underline">Forgot password?</Link>
        </div>
        
        <button className="w-full bg-blue-600 text-white p-2 rounded font-semibold hover:bg-blue-700">Sign In</button>
      </form>
    </div>
  );
}
