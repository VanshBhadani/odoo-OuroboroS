'use client';
import { useState } from 'react';
import api from '@/lib/api';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Package, UserPlus } from 'lucide-react';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('WAREHOUSE_STAFF');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await api.post('/auth/signup', {
        email,
        password,
        name,
        role
      });
      // Redirect to login after successful signup
      router.push('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create account. Email might already exist.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 py-12">
      <div className="bg-white p-10 rounded-xl shadow-lg w-full max-w-md border border-slate-100">
        <div className="flex flex-col items-center justify-center mb-8">
          <div className="bg-blue-600 p-3 rounded-lg text-white mb-4">
            <UserPlus size={32} />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">Create an Account</h1>
          <p className="text-slate-500 text-sm mt-2">Join StockSense to manage inventory</p>
        </div>
        
        {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-6 text-sm">{error}</div>}
        
        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
            <input 
              className="w-full border border-slate-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" 
              value={name} 
              onChange={e => setName(e.target.value)} 
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input 
              type="email"
              className="w-full border border-slate-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input 
              type="password"
              className="w-full border border-slate-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Role (e.g. INVENTORY_MANAGER, WAREHOUSE_STAFF)</label>
            <input 
              className="w-full border border-slate-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              value={role}
              onChange={e => setRole(e.target.value)}
              placeholder="Enter your role"
              required
            />
          </div>
          <button 
            disabled={loading}
            className="w-full bg-blue-600 text-white p-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 mt-4"
          >
            {loading ? 'Creating...' : 'Sign Up'}
          </button>
        </form>
        
        <div className="mt-6 text-center text-sm text-slate-500">
          Already have an account? <Link href="/login" className="text-blue-600 font-semibold hover:underline">Sign In</Link>
        </div>
      </div>
    </div>
  );
}
