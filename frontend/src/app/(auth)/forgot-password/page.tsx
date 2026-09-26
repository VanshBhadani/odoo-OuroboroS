'use client';
import { useState } from 'react';
import api from '@/lib/api';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    
    try {
      await api.post('/auth/otp/send', { email });
      setMessage('OTP has been sent to your email (check server logs for the code).');
      setStep(2);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send OTP. Is the email registered?');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await api.post('/auth/otp/verify-and-reset', {
        email,
        otp_code: otp,
        new_password: newPassword
      });
      setMessage('Password successfully reset! Redirecting to login...');
      setTimeout(() => router.push('/login'), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid or expired OTP code.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="bg-white p-10 rounded-xl shadow-lg w-full max-w-md border border-slate-100">
        <div className="flex flex-col items-center justify-center mb-6">
          <div className="bg-slate-100 p-3 rounded-lg text-slate-700 mb-4">
            <ShieldAlert size={32} />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">Password Reset</h1>
          <p className="text-slate-500 text-sm mt-2 text-center">
            {step === 1 ? 'Enter your email to receive a One-Time Password (OTP).' : 'Enter the OTP and your new password.'}
          </p>
        </div>
        
        {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-6 text-sm">{error}</div>}
        {message && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-6 text-sm">{message}</div>}
        
        {step === 1 ? (
          <form onSubmit={handleRequestOtp} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Registered Email</label>
              <input 
                type="email"
                className="w-full border border-slate-300 p-3 rounded-lg focus:ring-2 focus:ring-slate-500 outline-none" 
                value={email} 
                onChange={e => setEmail(e.target.value)} 
                required
              />
            </div>
            <button 
              disabled={loading}
              className="w-full bg-slate-800 text-white p-3 rounded-lg font-semibold hover:bg-slate-900 transition disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send OTP'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleResetPassword} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">6-Digit OTP</label>
              <input 
                type="text"
                maxLength={6}
                placeholder="123456"
                className="w-full border border-slate-300 p-3 rounded-lg focus:ring-2 focus:ring-slate-500 outline-none text-center tracking-widest font-mono text-lg" 
                value={otp} 
                onChange={e => setOtp(e.target.value.replace(/\\D/g, ''))} 
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">New Password</label>
              <input 
                type="password"
                className="w-full border border-slate-300 p-3 rounded-lg focus:ring-2 focus:ring-slate-500 outline-none" 
                value={newPassword} 
                onChange={e => setNewPassword(e.target.value)} 
                required
                minLength={8}
              />
            </div>
            <button 
              disabled={loading}
              className="w-full bg-blue-600 text-white p-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Reset Password'}
            </button>
          </form>
        )}
        
        <div className="mt-8 text-center">
          <Link href="/login" className="text-sm text-slate-500 hover:text-slate-800 flex items-center justify-center gap-2">
            <ArrowLeft size={16} /> Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
