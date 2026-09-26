import { Operation } from '@/types';
import { format } from 'date-fns';

export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    DRAFT: 'bg-slate-200 text-slate-800',
    WAITING: 'bg-yellow-100 text-yellow-800',
    READY: 'bg-yellow-100 text-yellow-800',
    DONE: 'bg-emerald-100 text-emerald-800',
    CANCELED: 'bg-red-100 text-red-800',
  };
  return (
    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${colors[status] || 'bg-slate-100'}`}>
      {status}
    </span>
  );
}

interface OperationTableProps {
  operations: Operation[];
  onValidate?: (id: string) => void;
  onDelete?: (id: string) => void;
  onDownloadPdf?: (op: Operation) => void;
}

export default function OperationTable({ operations, onValidate, onDelete, onDownloadPdf }: OperationTableProps) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 uppercase text-xs">
          <tr>
            <th className="p-4 font-semibold">Reference</th>
            <th className="p-4 font-semibold">Partner / Notes</th>
            <th className="p-4 font-semibold">Date</th>
            <th className="p-4 font-semibold">Lines</th>
            <th className="p-4 font-semibold">Status</th>
            <th className="p-4 font-semibold text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {operations.map((op) => (
            <tr key={op.id} className="hover:bg-slate-50 transition-colors">
              <td className="p-4 font-medium text-slate-900">{op.reference}</td>
              <td className="p-4 text-slate-600">{op.partner_name || op.notes || '-'}</td>
              <td className="p-4 text-slate-600">{format(new Date(op.created_at), 'MMM d, yyyy HH:mm')}</td>
              <td className="p-4 text-slate-600">{op.lines?.length || 0} items</td>
              <td className="p-4">
                <StatusBadge status={op.status} />
              </td>
              <td className="p-4 text-right flex justify-end gap-2">
                {op.status === 'DONE' && onDownloadPdf && (
                  <button
                    onClick={() => onDownloadPdf(op)}
                    className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded border border-slate-300 font-medium transition-colors"
                  >
                    Download Receipt
                  </button>
                )}
                {op.status === 'DRAFT' && onDelete && (
                  <button
                    onClick={() => {
                      if(window.confirm('Are you sure you want to delete this draft?')) {
                        onDelete(op.id);
                      }
                    }}
                    className="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded border border-red-200 font-medium transition-colors"
                  >
                    Delete
                  </button>
                )}
                {op.status !== 'DONE' && op.status !== 'CANCELED' && onValidate && (
                  <button
                    onClick={() => onValidate(op.id)}
                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded shadow-sm font-medium transition-colors"
                  >
                    Validate
                  </button>
                )}
              </td>
            </tr>
          ))}
          {operations.length === 0 && (
            <tr>
              <td colSpan={6} className="p-8 text-center text-slate-400">
                No operations found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
