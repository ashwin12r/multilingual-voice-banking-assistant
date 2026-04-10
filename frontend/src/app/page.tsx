'use client';
import { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import VoiceAssistant from '../components/VoiceAssistant';
import LoginForm from '../components/LoginForm';

export default function Dashboard() {
  const { token, activeLanguage, setLanguage } = useStore();
  const [data, setData] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  const fetchDashboard = () => {
    if(!token) return;
    Promise.all([
      fetch('http://127.0.0.1:8000/balance', { headers: { Authorization: `Bearer ${token}` }}).then(r=>r.json()),
      fetch('http://127.0.0.1:8000/credit-score', { headers: { Authorization: `Bearer ${token}` }}).then(r=>r.json()),
      fetch('http://127.0.0.1:8000/emi', { headers: { Authorization: `Bearer ${token}` }}).then(r=>r.json()),
      fetch('http://127.0.0.1:8000/insights', { headers: { Authorization: `Bearer ${token}` }}).then(r=>r.json())
    ]).then(([balance, credit, emi, insights]) => {
      setData({ balance, credit, emi, insights });
    }).catch(e => console.error("Error loading dashboard data", e));
  };

  useEffect(() => {
    fetchDashboard();
  }, [token]);

  if (!token) {
    return <LoginForm />;
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if(!e.target.files?.[0] || !token) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", e.target.files[0]);
    
    try {
      const res = await fetch('http://127.0.0.1:8000/upload-statement', {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      if(res.ok) fetchDashboard();
      else alert("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  if (!token) return <div className="text-white p-10 flex flex-col items-center justify-center min-h-screen bg-gray-950 font-sans tracking-tight">
    <div className="animate-spin text-teal-400 mb-4 text-4xl">⟳</div>
    <div className="text-xl font-medium text-gray-400">Connecting to Aurex Backend...</div>
    <VoiceAssistant /> {/* Required to get the initial login token via voice if not provided */}
  </div>

  return (
    <main className="p-8 bg-gray-950 min-h-screen text-white font-sans selection:bg-teal-500 selection:text-white">
      <header className="flex justify-between items-center mb-10 pb-4 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <div className="bg-yellow-500 text-gray-950 font-bold p-3 rounded-xl text-2xl flex items-center justify-center h-12 w-12 shadow-lg shadow-yellow-500/20">A</div>
          <h1 className="text-3xl font-extrabold tracking-tight">AUR<span className="text-teal-400">EX</span></h1>
        </div>
        
        <select value={activeLanguage} onChange={(e) => setLanguage(e.target.value)} className="bg-gray-800 border border-gray-700 p-2.5 rounded-lg text-sm text-gray-200 focus:ring-2 focus:ring-teal-500 outline-none">
          <option value="en">English (EN)</option>
          <option value="hi">हिंदी (Hindi)</option>
          <option value="ta">தமிழ் (Tamil)</option>
        </select>
      </header>

      <h2 className="text-2xl font-bold mb-6 text-gray-100 flex items-center justify-between">
         <div className="flex items-center gap-2">📊 Financial Overview</div>
         <label className="cursor-pointer bg-teal-600 hover:bg-teal-500 text-white text-sm font-bold py-2 px-4 rounded-xl shadow-lg transition-colors flex items-center gap-2">
            {uploading ? '⏳ Processing...' : '📄 Upload Statement'}
            <input type="file" accept=".pdf,.csv" className="hidden" onChange={handleFileUpload} disabled={uploading} />
         </label>
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
         {/* Balance Card */}
         <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl transition-transform hover:-translate-y-1">
            <h3 className="text-gray-400 text-xs font-semibold mb-3 uppercase tracking-wider flex items-center gap-2">💳 Available Balance</h3>
            <div className="text-4xl font-extrabold text-white mb-2">₹{data?.balance?.balance?.toLocaleString() || '---'}</div>
            <div className="inline-flex items-center gap-1 bg-green-500/10 text-green-400 text-xs font-bold px-2.5 py-1 rounded-full mt-2">▲ 2.4% from last month</div>
         </div>

         {/* Credit Score Card */}
         <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl transition-transform hover:-translate-y-1">
            <h3 className="text-gray-400 text-xs font-semibold mb-3 uppercase tracking-wider flex items-center gap-2">🌟 Credit Score</h3>
            <div className="flex items-baseline gap-3 mb-2">
              <div className="text-4xl font-extrabold text-white">{data?.credit?.score || '---'}</div>
              <div className="text-teal-400 text-xs font-bold px-2.5 py-1 rounded-full bg-teal-500/10 uppercase tracking-wide border border-teal-500/20">{data?.credit?.status || 'Good'}</div>
            </div>
            <div className="text-gray-400 text-sm mt-3 pt-3 border-t border-gray-800 leading-snug">{data?.credit?.suggestion || 'Keep up the good work!'}</div>
         </div>

         {/* EMI Card */}
         <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl transition-transform hover:-translate-y-1">
            <h3 className="text-gray-400 text-xs font-semibold mb-3 uppercase tracking-wider flex items-center gap-2">🗓️ Pending EMIs</h3>
            <div className="text-4xl font-extrabold text-white mb-2">₹{data?.emi?.total_pending?.toLocaleString() || '---'}</div>
            <div className="text-red-400 text-xs font-semibold mt-3 flex items-center gap-1">⚠️ Due soon: {data?.emi?.emis?.filter((e:any) => e.status === 'Pending')[0]?.dueDate || 'None'}</div>
         </div>

         {/* Insights Card */}
         <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl transition-transform hover:-translate-y-1">
            <h3 className="text-gray-400 text-xs font-semibold mb-3 uppercase tracking-wider flex items-center gap-2">🤖 AI Insights</h3>
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 mt-2 h-full">
                <p className="text-yellow-400 text-sm font-medium leading-relaxed">{data?.insights?.alert || 'Analyzing spending patterns...'}</p>
            </div>
         </div>
      </div>

      <div className="fixed bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-gray-950 via-gray-950 to-transparent flex justify-center pointer-events-none">
          <div className="pointer-events-auto">
             <VoiceAssistant />
          </div>
      </div>
    </main>
  );
}
