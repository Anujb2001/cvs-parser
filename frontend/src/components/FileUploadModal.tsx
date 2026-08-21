import React, { useState } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadTelecomFile } from '../services/api';
import { OperatorType, FileCategory } from '../types/forensic';

interface Props {
  currentCaseId: string;
  onUploadSuccess: (rows: number, filename: string) => void;
}

export const FileUploadModal: React.FC<Props> = ({ currentCaseId, onUploadSuccess }) => {
  const [operator, setOperator] = useState<OperatorType>('AIRTEL');
  const [fileType, setFileType] = useState<FileCategory>('CDR');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setStatusMessage(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setStatusMessage({ type: 'error', text: 'Please select a CDR, IPDR, or IPDump file first.' });
      return;
    }

    setUploading(true);
    setStatusMessage(null);

    try {
      const res = await uploadTelecomFile(currentCaseId, fileType, operator, selectedFile);
      setStatusMessage({
        type: 'success',
        text: `Successfully ingested ${res.rows_ingested.toLocaleString()} records into ClickHouse!`,
      });
      onUploadSuccess(res.rows_ingested, res.filename);
      setSelectedFile(null);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Error uploading file.' });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl text-slate-100 max-w-xl w-full">
      <div className="flex items-center space-x-3 mb-6 border-b border-slate-800 pb-4">
        <Upload className="w-6 h-6 text-blue-500" />
        <div>
          <h2 className="text-lg font-bold">Ingest Telecom Dump</h2>
          <p className="text-xs text-slate-400">Supports CDR, IPDR, and IPDump for Airtel, Jio & Vodafone Idea</p>
        </div>
      </div>

      <form onSubmit={handleUpload} className="space-y-5">
        {/* Operator Selection */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            1. Select Telecom Operator
          </label>
          <div className="grid grid-cols-3 gap-3">
            {(['AIRTEL', 'JIO', 'VI'] as OperatorType[]).map((op) => (
              <button
                type="button"
                key={op}
                onClick={() => setOperator(op)}
                className={`py-2 px-3 rounded-lg text-sm font-semibold border transition-all ${
                  operator === op
                    ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {op === 'VI' ? 'Vodafone Idea (VI)' : op}
              </button>
            ))}
          </div>
        </div>

        {/* File Category Selection */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            2. Select Dump Category
          </label>
          <div className="grid grid-cols-3 gap-3">
            {(['CDR', 'IPDR', 'IPDUMP'] as FileCategory[]).map((cat) => (
              <button
                type="button"
                key={cat}
                onClick={() => setFileType(cat)}
                className={`py-2 px-3 rounded-lg text-sm font-semibold border transition-all ${
                  fileType === cat
                    ? 'bg-emerald-600 border-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {cat === 'IPDUMP' ? 'IP Dump (App)' : cat}
              </button>
            ))}
          </div>
        </div>

        {/* Dropzone File Upload Input */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            3. Select File (.csv, .xlsx, .txt)
          </label>
          <div className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-6 text-center bg-slate-950 transition-colors">
            <input
              type="file"
              id="file-input"
              accept=".csv,.xlsx,.txt"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="file-input" className="cursor-pointer flex flex-col items-center justify-center space-y-2">
              <FileText className="w-10 h-10 text-slate-500" />
              <span className="text-sm text-slate-300 font-medium">
                {selectedFile ? selectedFile.name : 'Click to browse or drop file here'}
              </span>
              <span className="text-xs text-slate-500">Supports Airtel, Jio, VI exports up to 2GB</span>
            </label>
          </div>
        </div>

        {/* Status Alerts */}
        {statusMessage && (
          <div
            className={`p-4 rounded-lg flex items-center space-x-3 text-sm font-medium ${
              statusMessage.type === 'success'
                ? 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'
                : 'bg-rose-950/80 border border-rose-800 text-rose-300'
            }`}
          >
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            )}
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={uploading || !selectedFile}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold rounded-lg shadow-lg flex items-center justify-center space-x-2 transition-all"
        >
          {uploading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Parsing & Streaming into ClickHouse...</span>
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              <span>Ingest {operator} {fileType} Log File</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};