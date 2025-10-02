import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadFile } from '../api/client';

const MAX_SIZE = 16 * 1024 * 1024;

export default function Upload({ onUploaded }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles, fileRejections) => {
    setUploadError(null);
    if (fileRejections?.length) {
      setUploadError(fileRejections[0]?.errors?.[0]?.message || 'File rejected');
      return;
    }
    const file = acceptedFiles[0];
    if (!file) return;
    setSelectedFile(file);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    maxSize: MAX_SIZE,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    }
  });

  const clear = () => {
    setSelectedFile(null);
    setUploadError(null);
    setUploadProgress(0);
  };

  const doUpload = async () => {
    if (!selectedFile) return;
    try {
      const res = await uploadFile(selectedFile, (evt) => {
        if (evt.total) setUploadProgress(Math.round((evt.loaded / evt.total) * 100));
      });
      onUploaded(res.file_id);
    } catch (e) {
      setUploadError(e?.response?.data?.error || e.message);
    }
  };

  return (
    <div className="upload">
      <div {...getRootProps({ className: `dropzone ${isDragActive ? 'active' : ''}` })}>
        <input {...getInputProps()} />
        {isDragActive ? <p>Drop the file here…</p> : <p>Drag 'n' drop a PDF/Image here, or click to select</p>}
      </div>

      {selectedFile && (
        <div className="panel">
          <div>Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)</div>
          <div className="actions">
            <button onClick={doUpload}>Upload</button>
            <button className="secondary" onClick={clear}>Clear</button>
          </div>
          {uploadProgress > 0 && <div className="progress">Uploading: {uploadProgress}%</div>}
        </div>
      )}

      {uploadError && <div className="error">{uploadError}</div>}
    </div>
  );
}
