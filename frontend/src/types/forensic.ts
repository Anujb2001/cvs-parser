export type OperatorType = 'AIRTEL' | 'JIO' | 'VI';
export type FileCategory = 'CDR' | 'IPDR' | 'IPDUMP';

export interface UploadResponse {
  status: string;
  case_id: string;
  filename: string;
  rows_ingested: number;
}

export interface AgentQueryResult {
  status: string;
  generated_sql: string;
  columns: string[];
  rows: any[][];
}

export interface ForensicRecord {
  msisdn: string;
  imei: string;
  imsi: string;
  operator: string;
  public_ip?: string;
  dest_ip?: string;
  timestamp: string;
  cell_id?: string;
}