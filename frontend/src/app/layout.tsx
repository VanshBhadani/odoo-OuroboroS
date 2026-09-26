import './globals.css';
import { AuthProvider } from '@/context/AuthContext';

export const metadata = { title: 'StockSense UI', description: 'Inventory Management' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
