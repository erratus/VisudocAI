import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 60000
});

export async function uploadFile(file, onUploadProgress) {
  const form = new FormData();
  form.append('file', file);
  const res = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  });
  return res.data;
}

export async function analyzeDocument(fileId) {
  const res = await api.post('/analyze', { file_id: fileId });
  return res.data;
}

export async function queryDocument(fileId, question) {
  const res = await api.post('/query', { file_id: fileId, question });
  return res.data;
}

export async function summarizeDocument(fileId, summaryType) {
  const res = await api.post('/summarize', { file_id: fileId, summary_type: summaryType });
  return res.data;
}

export default api;
