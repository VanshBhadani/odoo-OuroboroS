"use client";

import { useState, useEffect } from 'react';
import api from '@/lib/api';

export default function SettingsPage() {
  const [companyName, setCompanyName] = useState('Loading...');
  const [savingCompany, setSavingCompany] = useState(false);

  const [locations, setLocations] = useState<any[]>([]);
  const [warehouses, setWarehouses] = useState<any[]>([]);
  
  const [newWhName, setNewWhName] = useState('');
  const [newWhCode, setNewWhCode] = useState('');
  
  const [newLocName, setNewLocName] = useState('');
  const [newLocCode, setNewLocCode] = useState('');
  const [selectedWhId, setSelectedWhId] = useState('');

  const [newCatName, setNewCatName] = useState('');
  const [newCatDesc, setNewCatDesc] = useState('');

  const [members, setMembers] = useState<any[]>([]);
  const [newMemberEmail, setNewMemberEmail] = useState('');

  useEffect(() => {
    fetchCompany();
    fetchWarehouses();
    fetchLocations();
    fetchMembers();
  }, []);

  const fetchCompany = async () => {
    try {
      const res = await api.get('/settings/company');
      setCompanyName(res.data.company_name);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchWarehouses = async () => {
    try {
      const res = await api.get('/settings/warehouses');
      setWarehouses(res.data);
      if (res.data.length > 0) {
        setSelectedWhId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchLocations = async () => {
    try {
      const res = await api.get('/dashboard/locations');
      setLocations(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchMembers = async () => {
    try {
      const res = await api.get('/settings/members');
      setMembers(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const saveCompany = async () => {
    setSavingCompany(true);
    try {
      await api.post('/settings/company', { key: 'company_name', value: companyName });
      alert('Company Name Saved!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error saving company');
    } finally {
      setSavingCompany(false);
    }
  };

  const createWarehouse = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/settings/warehouses', { name: newWhName, code: newWhCode });
      setNewWhName('');
      setNewWhCode('');
      fetchWarehouses();
      alert('Warehouse Created!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error creating warehouse');
    }
  };

  const createLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/settings/locations', { name: newLocName, code: newLocCode, warehouse_id: selectedWhId });
      setNewLocName('');
      setNewLocCode('');
      fetchLocations();
      alert('Location Created!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error creating location');
    }
  };

  const createCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/settings/categories', { name: newCatName, description: newCatDesc });
      setNewCatName('');
      setNewCatDesc('');
      alert('Category Created!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error creating category');
    }
  };

  const addMember = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/settings/members', { email: newMemberEmail });
      setNewMemberEmail('');
      fetchMembers();
      alert('Member added to allowlist!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error adding member');
    }
  };

  const removeMember = async (email: string) => {
    if (!confirm(`Are you sure you want to remove ${email} from the allowlist?`)) return;
    try {
      await api.delete(`/settings/members/${email}`);
      fetchMembers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error removing member');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-1">Manage company profile, warehouses, and locations.</p>
      </div>

      <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
          <h2 className="font-semibold text-slate-800">Company Profile</h2>
        </div>
        <div className="p-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">Company Name (Appears on Receipts)</label>
          <div className="flex gap-4">
            <input 
              type="text" 
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="flex-1 border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <button 
              onClick={saveCompany}
              disabled={savingCompany}
              className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {savingCompany ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
            <h2 className="font-semibold text-slate-800">Add New Warehouse</h2>
          </div>
          <div className="p-6">
            <form onSubmit={createWarehouse} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-600 mb-1">Warehouse Name</label>
                <input required type="text" value={newWhName} onChange={e=>setNewWhName(e.target.value)} className="w-full border p-2 rounded outline-none" placeholder="e.g. South Annex" />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Code (Short)</label>
                <input required type="text" value={newWhCode} onChange={e=>setNewWhCode(e.target.value)} className="w-full border p-2 rounded outline-none" placeholder="e.g. WH02" />
              </div>
              <button type="submit" className="w-full bg-slate-800 text-white px-4 py-2 rounded font-medium hover:bg-slate-900">Create Warehouse</button>
            </form>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
            <h2 className="font-semibold text-slate-800">Add New Location (Aisle/Rack)</h2>
          </div>
          <div className="p-6">
            <form onSubmit={createLocation} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-600 mb-1">Parent Warehouse</label>
                <select value={selectedWhId} onChange={e=>setSelectedWhId(e.target.value)} className="w-full border p-2 rounded outline-none text-slate-900 bg-white">
                  {warehouses.map(w => <option key={w.id} value={w.id} className="text-slate-900 bg-white">{w.name} ({w.code})</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Location Name</label>
                <input required type="text" value={newLocName} onChange={e=>setNewLocName(e.target.value)} className="w-full border p-2 rounded outline-none" placeholder="e.g. Aisle 5" />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Location Code</label>
                <input required type="text" value={newLocCode} onChange={e=>setNewLocCode(e.target.value)} className="w-full border p-2 rounded outline-none" placeholder="e.g. WH02/A5" />
              </div>
              <button type="submit" className="w-full bg-slate-800 text-white px-4 py-2 rounded font-medium hover:bg-slate-900">Create Location</button>
            </form>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
            <h2 className="font-semibold text-slate-800">Add New Category</h2>
          </div>
          <div className="p-6">
            <form onSubmit={createCategory} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-600 mb-1">Category Name</label>
                <input required type="text" value={newCatName} onChange={e=>setNewCatName(e.target.value)} className="w-full border p-2 rounded outline-none" placeholder="e.g. Electronics" />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Description (Optional)</label>
                <input type="text" value={newCatDesc} onChange={e=>setNewCatDesc(e.target.value)} className="w-full border p-2 rounded outline-none" placeholder="e.g. Gadgets and Devices" />
              </div>
              <button type="submit" className="w-full bg-slate-800 text-white px-4 py-2 rounded font-medium hover:bg-slate-900">Create Category</button>
            </form>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden md:col-span-2">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
            <h2 className="font-semibold text-slate-800">Authorized Members (Allowlist)</h2>
            <p className="text-xs text-slate-500 mt-1">Only emails listed here can register and log in to the application.</p>
          </div>
          <div className="p-6">
            <form onSubmit={addMember} className="flex gap-4 mb-6">
              <input required type="email" value={newMemberEmail} onChange={e=>setNewMemberEmail(e.target.value)} className="flex-1 border p-2 rounded outline-none" placeholder="new.member@gmail.com" />
              <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700">Add Member</button>
            </form>

            <div className="border rounded-md overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="p-3 font-semibold text-slate-600">Email Address</th>
                    <th className="p-3 font-semibold text-slate-600 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {members.map(m => (
                    <tr key={m.email} className="hover:bg-slate-50">
                      <td className="p-3 text-slate-800">{m.email}</td>
                      <td className="p-3 text-right">
                        <button onClick={() => removeMember(m.email)} className="text-red-600 hover:text-red-800 font-medium text-xs">Remove</button>
                      </td>
                    </tr>
                  ))}
                  {members.length === 0 && (
                    <tr>
                      <td colSpan={2} className="p-4 text-center text-slate-500">No members in allowlist.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
