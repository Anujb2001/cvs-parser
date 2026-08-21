import { UploadResponse, AgentQueryResult } from '../types/forensic';

const API_BASE_URL = 'http://localhost:8001/api/v1';

export async function uploadTelecomFile(
  caseId: string,
  fileType: string,
  operator: string,
  file: File
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('case_id', caseId);
  formData.append('file_type', fileType);
  formData.append('operator', operator);
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/ingest/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Upload failed');
  }

  return response.json();
}

export async function queryLocalAgent(
  caseId: string,
  prompt: string
): Promise<AgentQueryResult> {
  const response = await fetch(`${API_BASE_URL}/agent/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_id: caseId, prompt }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Agent query failed');
  }

  return response.json();
}