'use client';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { LayoutDashboard, Package, ArrowRightLeft, History, Settings, LogOut } from 'lucide-react';

export default function Sidebar() {
  const { user, logout } = useAuth();
  
  return (
    <aside className="w-64 bg-slate-900 text-white h-screen flex flex-col fixed left-0 top-0">
      <div className="p-4 text-2xl font-bold border-b border-slate-800">StockSense</div>
      <nav className="flex-1 p-4 space-y-2">
        <Link href="/" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded"><LayoutDashboard size={20} /> Dashboard</Link>
        <Link href="/products" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded"><Package size={20} /> Products</Link>
        
        <div className="pt-4 pb-2 text-xs font-semibold text-slate-400 uppercase">Operations</div>
        <Link href="/operations/receipts" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded pl-6">Receipts</Link>
        <Link href="/operations/deliveries" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded pl-6">Deliveries</Link>
        <Link href="/operations/transfers" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded pl-6">Transfers</Link>
        <Link href="/operations/adjustments" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded pl-6">Adjustments</Link>
        
        <div className="pt-4 pb-2 text-xs font-semibold text-slate-400 uppercase">Reporting</div>
        <Link href="/ledger" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded"><History size={20} /> Move History</Link>
        <Link href="/settings" className="flex items-center gap-3 p-2 hover:bg-slate-800 rounded"><Settings size={20} /> Settings</Link>
      </nav>
      <div className="p-4 border-t border-slate-800 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold">{user?.name || 'Guest'}</div>
          <div className="text-xs text-slate-400">{user?.role || 'No Role'}</div>
        </div>
        <button onClick={logout} className="p-2 hover:bg-slate-800 rounded"><LogOut size={18}/></button>
      </div>
    </aside>
  );
}
