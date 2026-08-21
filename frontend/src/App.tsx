import React, { useState } from 'react';
import { Shield, Database, Search, Terminal, Cpu, MapPin, Network, Table } from 'lucide-react';
import { FileUploadModal } from './components/FileUploadModal';
import { queryLocalAgent } from './services/api';
import { AgentQueryResult } from './types/forensic';

export const App: React.FC = () => {
  const [caseId, setCaseId] = useState<string>('CR-DELHI-2026-0089');
  const [activeTab, setActiveTab] = useState<'GRID' | 'GRAPH' | 'MAP'>('GRID');
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [prompt, setPrompt] = useState<string>('');
  const [agentLoading, setAgentLoading] = useState<boolean>(false);
  const [queryResults, setQueryResults] = useState<AgentQueryResult | null>(null);

  const handleAgentSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setAgentLoading(true);
    try {
      const res = await queryLocalAgent(caseId, prompt);
      setQueryResults(res);
    } catch (err: any) {
      alert(`Agent Query Error: ${err.message}`);
    } finally {
      setAgentLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navbar */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-600/20 border border-blue-500/30 rounded-lg">
            <Shield className="w-6 h-6 text-blue-500" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-wide">i9 Forensic Intelligence Platform</h1>
            <p className="text-xs text-slate-400">Air-Gapped CDR, IPDR & IPDump Analyzer (Offline Mode)</p>
          </div>
        </div>

        {/* Active Case Selector & Ingestion Trigger */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg">
            <span className="text-xs text-slate-400 uppercase font-semibold">Active Case:</span>
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              className="bg-transparent text-sm font-bold text-blue-400 focus:outline-none w-44"
            />
          </div>

          <button
            onClick={() => setShowUploadModal(!showUploadModal)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 font-semibold text-sm rounded-lg shadow-lg shadow-blue-500/20 flex items-center space-x-2 transition-all"
          >
            <Database className="w-4 h-4" />
            <span>Upload Telecom Logs</span>
          </button>
        </div>
      </header>

      {/* Main Layout Content */}
      <main className="flex-1 p-6 space-y-6 max-w-7xl w-full mx-auto">
        {/* File Ingestion Modal Overlay */}
        {showUploadModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="relative">
              <button
                onClick={() => setShowUploadModal(false)}
                className="absolute -top-3 -right-3 bg-slate-800 hover:bg-slate-700 text-slate-400 p-1.5 rounded-full border border-slate-700"
              >
                ✕
              </button>
              <FileUploadModal
                currentCaseId={caseId}
                onUploadSuccess={() => setShowUploadModal(false)}
              />
            </div>
          </div>
        )}

        {/* Air-Gapped Local AI Agent Query Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
          <form onSubmit={handleAgentSearch} className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
              <Cpu className="w-5 h-5 text-emerald-400" />
            </div>
            <input
              type="text"
              placeholder="Ask local AI Agent in English (e.g., 'Find all numbers hitting Signal IP 141.101.90.1 across Airtel, Jio & VI')..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={agentLoading}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-semibold text-sm rounded-lg flex items-center space-x-2 transition-all"
            >
              <Search className="w-4 h-4" />
              <span>{agentLoading ? 'Analyzing...' : 'Run Query'}</span>
            </button>
          </form>

          {/* Generated SQL Display */}
          {queryResults && (
            <div className="mt-3 pt-3 border-t border-slate-800 flex items-start space-x-2 text-xs font-mono text-slate-400">
              <Terminal className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="overflow-x-auto">
                <span className="text-blue-400 font-bold">Sanitized ClickHouse SQL: </span>
                <code>{queryResults.generated_sql}</code>
              </div>
            </div>
          )}
        </div>

        {/* View Mode Tabs */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('GRID')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition-all ${
                activeTab === 'GRID'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:bg-slate-800'
              }`}
            >
              <Table className="w-4 h-4" />
              <span>Data Grid</span>
            </button>
            <button
              onClick={() => setActiveTab('GRAPH')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition-all ${
                activeTab === 'GRAPH'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:bg-slate-800'
              }`}
            >
              <Network className="w-4 h-4" />
              <span>Link Network Graph</span>
            </button>
            <button
              onClick={() => setActiveTab('MAP')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition-all ${
                activeTab === 'MAP'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:bg-slate-800'
              }`}
            >
              <MapPin className="w-4 h-4" />
              <span>Cell Tower Map</span>
            </button>
          </div>
          <span className="text-xs text-slate-500 font-semibold">
            {queryResults ? `${queryResults.rows.length} records returned` : 'Ready for case analysis'}
          </span>
        </div>

        {/* View Component Display */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 min-h-[450px]">
          {activeTab === 'GRID' && (
            <div className="overflow-x-auto">
              {queryResults && queryResults.rows.length > 0 ? (
                <table className="w-full text-left text-xs text-slate-300 font-mono">
                  <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                    <tr>
                      {queryResults.columns.map((col, idx) => (
                        <th key={idx} className="p-3">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {queryResults.rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className="p-3 whitespace-nowrap">
                            {String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center h-80 text-slate-500">
                  <Table className="w-12 h-12 mb-3 stroke-1" />
                  <p className="text-sm font-medium">No active search query results to display.</p>
                  <p className="text-xs text-slate-600 mt-1">Upload telecom files or run a prompt above.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'GRAPH' && (
            <div className="flex flex-col items-center justify-center h-80 text-slate-500">
              <Network className="w-12 h-12 mb-3 stroke-1" />
              <p className="text-sm font-medium">Link Analysis Network Graph Component</p>
              <p className="text-xs text-slate-600 mt-1">Cytoscape.js visualizes call chains and target node relationships.</p>
            </div>
          )}

          {activeTab === 'MAP' && (
            <div className="flex flex-col items-center justify-center h-80 text-slate-500">
              <MapPin className="w-12 h-12 mb-3 stroke-1" />
              <p className="text-sm font-medium">Geospatial Cell Tower Mapping Component</p>
              <p className="text-xs text-slate-600 mt-1">Leaflet.js renders offline vector map tiles and movement trails.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;