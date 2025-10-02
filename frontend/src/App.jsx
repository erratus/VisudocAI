import React, { useState } from 'react';
import Upload from './components/Upload.jsx';
import DocumentViewer from './components/DocumentViewer.jsx';
import QueryPanel from './components/QueryPanel.jsx';
import SummaryPanel from './components/SummaryPanel.jsx';
import './styles/App.css';

export default function App() {
  const [currentStep, setCurrentStep] = useState('upload');
  const [fileId, setFileId] = useState(null);
  const [documentData, setDocumentData] = useState(null);

  const handleUploaded = (id) => {
    setFileId(id);
    setCurrentStep('analyze');
  };

  const handleAnalysisComplete = (data) => {
    setDocumentData(data);
    setCurrentStep('interact');
  };

  const resetAll = () => {
    setCurrentStep('upload');
    setFileId(null);
    setDocumentData(null);
  };

  return (
    <div className="container">
      <header>
        <h1>VisuDocAI</h1>
        <button className="reset" onClick={resetAll}>Reset</button>
      </header>

      {currentStep === 'upload' && (
        <Upload onUploaded={handleUploaded} />
      )}

      {currentStep === 'analyze' && fileId && (
        <DocumentViewer fileId={fileId} onAnalysisComplete={handleAnalysisComplete} />
      )}

      {currentStep === 'interact' && fileId && documentData && (
        <div className="grid">
          <DocumentViewer fileId={fileId} initialData={documentData} onAnalysisComplete={setDocumentData} />
          <div className="sidepanels">
            <QueryPanel fileId={fileId} extractedText={documentData.extracted_text} />
            <SummaryPanel fileId={fileId} />
          </div>
        </div>
      )}
    </div>
  );
}
