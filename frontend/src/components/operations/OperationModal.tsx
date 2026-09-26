import { useState } from 'react';
import { Product, Location } from '@/types';
import { X, Plus, Trash2 } from 'lucide-react';

interface OperationLineInput {
  product_id: string;
  quantity: number;
}

interface OperationModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  operationType: 'RECEIPT' | 'DELIVERY' | 'INTERNAL';
  products: Product[];
  locations: Location[];
  onSubmit: (data: { partner_name?: string; source_location_id?: string; dest_location_id?: string; lines: OperationLineInput[] }) => Promise<void>;
}

export default function OperationModal({ isOpen, onClose, title, operationType, products, locations, onSubmit }: OperationModalProps) {
  const [partnerName, setPartnerName] = useState('');
  const [sourceLoc, setSourceLoc] = useState('');
  const [destLoc, setDestLoc] = useState('');
  const [lines, setLines] = useState<OperationLineInput[]>([{ product_id: '', quantity: 1 }]);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleAddLine = () => setLines([...lines, { product_id: '', quantity: 1 }]);
  const handleRemoveLine = (index: number) => setLines(lines.filter((_, i) => i !== index));
  const handleLineChange = (index: number, field: keyof OperationLineInput, value: string | number) => {
    const newLines = [...lines];
    newLines[index] = { ...newLines[index], [field]: value };
    setLines(newLines);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        partner_name: partnerName,
        source_location_id: sourceLoc || undefined,
        dest_location_id: destLoc || undefined,
        lines: lines.filter(l => l.product_id && l.quantity > 0)
      });
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl flex flex-col max-h-[90vh]">
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-xl font-bold text-slate-800">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={24} /></button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1 space-y-6">
          {(operationType === 'RECEIPT' || operationType === 'DELIVERY') && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Partner (Vendor/Customer)</label>
              <input required type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={partnerName} onChange={e => setPartnerName(e.target.value)} />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {(operationType === 'DELIVERY' || operationType === 'INTERNAL') && (
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Source Location</label>
                <select required className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={sourceLoc} onChange={e => setSourceLoc(e.target.value)}>
                  <option value="">Select location...</option>
                  {locations.filter(l => l.location_type === 'INTERNAL').map(l => (
                    <option key={l.id} value={l.id}>{l.name} ({l.code})</option>
                  ))}
                </select>
              </div>
            )}
            {(operationType === 'RECEIPT' || operationType === 'INTERNAL') && (
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Destination Location</label>
                <select required className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={destLoc} onChange={e => setDestLoc(e.target.value)}>
                  <option value="">Select location...</option>
                  {locations.filter(l => l.location_type === 'INTERNAL').map(l => (
                    <option key={l.id} value={l.id}>{l.name} ({l.code})</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-semibold text-slate-700">Line Items</label>
              <button type="button" onClick={handleAddLine} className="text-sm flex items-center gap-1 text-blue-600 hover:text-blue-700 font-medium">
                <Plus size={16} /> Add Line
              </button>
            </div>
            <div className="space-y-3">
              {lines.map((line, idx) => (
                <div key={idx} className="flex gap-3 items-center bg-slate-50 p-3 rounded border">
                  <div className="flex-1">
                    <select required className="w-full border p-2 rounded outline-none" value={line.product_id} onChange={e => handleLineChange(idx, 'product_id', e.target.value)}>
                      <option value="">Select Product...</option>
                      {products.map(p => <option key={p.id} value={p.id}>{p.name} [{p.sku}]</option>)}
                    </select>
                  </div>
                  <div className="w-32">
                    <input required type="number" min="0.01" step="0.01" className="w-full border p-2 rounded outline-none" value={line.quantity} onChange={e => handleLineChange(idx, 'quantity', parseFloat(e.target.value))} />
                  </div>
                  <button type="button" onClick={() => handleRemoveLine(idx)} className="text-red-500 hover:bg-red-50 p-2 rounded transition-colors"><Trash2 size={18} /></button>
                </div>
              ))}
            </div>
          </div>
        </form>

        <div className="p-6 border-t bg-slate-50 rounded-b-xl flex justify-end gap-3">
          <button type="button" onClick={onClose} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded transition-colors">Cancel</button>
          <button onClick={handleSubmit} disabled={submitting} className="px-4 py-2 bg-blue-600 text-white font-medium hover:bg-blue-700 rounded shadow-sm disabled:opacity-50 transition-colors">
            {submitting ? 'Saving...' : 'Save & Validate'}
          </button>
        </div>
      </div>
    </div>
  );
}
