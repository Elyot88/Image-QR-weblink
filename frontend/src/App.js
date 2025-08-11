import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [activeTab, setActiveTab] = useState('link');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [storedImages, setStoredImages] = useState([]);
  
  // Camera states
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [stream, setStream] = useState(null);
  
  // Form states
  const [linkUrl, setLinkUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (activeTab === 'view') {
      fetchStoredImages();
    }
  }, [activeTab]);

  // Cleanup camera when component unmounts
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [stream]);

  const showMessage = (msg, type = 'info') => {
    setMessage(msg);
    setMessageType(type);
    setTimeout(() => {
      setMessage('');
      setMessageType('');
    }, 5000);
  };

  const fetchStoredImages = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/stored-images`);
      const data = await response.json();
      
      if (response.ok) {
        setStoredImages(data.images || []);
      } else {
        showMessage('Failed to load stored images', 'error');
      }
    } catch (error) {
      showMessage('Error loading stored images: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Use rear camera on mobile
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      });
      
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setIsCameraActive(true);
      showMessage('Camera started successfully', 'success');
    } catch (error) {
      showMessage('Failed to access camera: ' + error.message, 'error');
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setIsCameraActive(false);
    setCapturedImage(null);
  };

  const captureImage = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      canvas.toBlob(blob => {
        setCapturedImage(blob);
        showMessage('Photo captured successfully!', 'success');
      }, 'image/jpeg', 0.8);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    setCapturedImage(null); // Clear captured image if file is selected
  };

  const linkImageToUrl = async () => {
    if (!linkUrl) {
      showMessage('Please enter a URL', 'error');
      return;
    }

    const imageFile = capturedImage || selectedFile;
    if (!imageFile) {
      showMessage('Please select an image or capture a photo', 'error');
      return;
    }

    try {
      setIsLoading(true);
      const formData = new FormData();
      formData.append('url', linkUrl);
      formData.append('file', imageFile, imageFile.name || 'captured_image.jpg');

      const response = await fetch(`${API_BASE_URL}/api/link-image`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, 'success');
        setLinkUrl('');
        setSelectedFile(null);
        setCapturedImage(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        showMessage(result.detail || 'Failed to link image', 'error');
      }
    } catch (error) {
      showMessage('Error linking image: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const scanImageForUrl = async () => {
    const imageFile = capturedImage || selectedFile;
    if (!imageFile) {
      showMessage('Please select an image or capture a photo', 'error');
      return;
    }

    try {
      setIsLoading(true);
      setScanResult(null);
      
      const formData = new FormData();
      formData.append('file', imageFile, imageFile.name || 'scanned_image.jpg');
      formData.append('threshold', '10');

      const response = await fetch(`${API_BASE_URL}/api/scan-image`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (response.ok) {
        setScanResult(result);
        
        if (result.status === 'match_found' && result.redirect_url) {
          showMessage(`Match found! Opening: ${result.redirect_url}`, 'success');
          // Open URL in new tab after a short delay
          setTimeout(() => {
            window.open(result.redirect_url, '_blank');
          }, 2000);
        } else {
          showMessage('No matching images found', 'info');
        }
      } else {
        showMessage(result.detail || 'Failed to scan image', 'error');
      }
    } catch (error) {
      showMessage('Error scanning image: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const deleteImage = async (imageId) => {
    if (!confirm('Are you sure you want to delete this image link?')) {
      return;
    }

    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/stored-images/${imageId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        showMessage('Image link deleted successfully', 'success');
        fetchStoredImages(); // Refresh the list
      } else {
        const result = await response.json();
        showMessage(result.detail || 'Failed to delete image', 'error');
      }
    } catch (error) {
      showMessage('Error deleting image: ' + error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-4">
              📸 Image-to-URL Recognition
            </h1>
            <p className="text-lg text-gray-600">
              Link images to URLs, then scan images to navigate to linked websites
            </p>
          </div>

          {/* Message Display */}
          {message && (
            <div className={`p-4 rounded-lg mb-6 ${
              messageType === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
              messageType === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
              'bg-blue-100 text-blue-800 border border-blue-200'
            }`}>
              {message}
            </div>
          )}

          {/* Tab Navigation */}
          <div className="flex flex-wrap justify-center mb-8 bg-white rounded-lg shadow-md p-2">
            {[
              { key: 'link', label: '🔗 Link Image', icon: '🔗' },
              { key: 'scan', label: '🔍 Scan Image', icon: '🔍' },
              { key: 'view', label: '📋 View Stored', icon: '📋' }
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-6 py-3 mx-1 my-1 rounded-lg transition-all duration-300 ${
                  activeTab === tab.key
                    ? 'bg-blue-500 text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Main Content Area */}
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            {/* Link Image Tab */}
            {activeTab === 'link' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                  Link Image to URL
                </h2>
                
                {/* URL Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target URL
                  </label>
                  <input
                    type="url"
                    value={linkUrl}
                    onChange={(e) => setLinkUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Image Input Options */}
                <div className="grid md:grid-cols-2 gap-6">
                  {/* File Upload */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium text-gray-700">Upload Image</h3>
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    {selectedFile && (
                      <p className="text-sm text-green-600">
                        ✅ Selected: {selectedFile.name}
                      </p>
                    )}
                  </div>

                  {/* Camera Capture */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium text-gray-700">Camera Capture</h3>
                    <div className="flex flex-wrap gap-2">
                      {!isCameraActive ? (
                        <button
                          onClick={startCamera}
                          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                        >
                          📷 Start Camera
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={captureImage}
                            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                          >
                            📸 Capture
                          </button>
                          <button
                            onClick={stopCamera}
                            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                          >
                            🛑 Stop
                          </button>
                        </>
                      )}
                    </div>
                    {capturedImage && (
                      <p className="text-sm text-green-600">
                        ✅ Photo captured successfully!
                      </p>
                    )}
                  </div>
                </div>

                {/* Camera View */}
                {isCameraActive && (
                  <div className="text-center">
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="max-w-full h-auto rounded-lg shadow-md"
                    />
                  </div>
                )}

                {/* Submit Button */}
                <button
                  onClick={linkImageToUrl}
                  disabled={isLoading}
                  className="w-full px-6 py-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-lg"
                >
                  {isLoading ? '🔄 Processing...' : '🔗 Link Image to URL'}
                </button>
              </div>
            )}

            {/* Scan Image Tab */}
            {activeTab === 'scan' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                  Scan Image for URL
                </h2>

                {/* Image Input Options */}
                <div className="grid md:grid-cols-2 gap-6">
                  {/* File Upload */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium text-gray-700">Upload Image</h3>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    {selectedFile && (
                      <p className="text-sm text-green-600">
                        ✅ Selected: {selectedFile.name}
                      </p>
                    )}
                  </div>

                  {/* Camera Capture */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium text-gray-700">Camera Capture</h3>
                    <div className="flex flex-wrap gap-2">
                      {!isCameraActive ? (
                        <button
                          onClick={startCamera}
                          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                        >
                          📷 Start Camera
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={captureImage}
                            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                          >
                            📸 Capture
                          </button>
                          <button
                            onClick={stopCamera}
                            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                          >
                            🛑 Stop
                          </button>
                        </>
                      )}
                    </div>
                    {capturedImage && (
                      <p className="text-sm text-green-600">
                        ✅ Photo captured successfully!
                      </p>
                    )}
                  </div>
                </div>

                {/* Camera View */}
                {isCameraActive && (
                  <div className="text-center">
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="max-w-full h-auto rounded-lg shadow-md"
                    />
                  </div>
                )}

                {/* Scan Button */}
                <button
                  onClick={scanImageForUrl}
                  disabled={isLoading}
                  className="w-full px-6 py-4 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-lg"
                >
                  {isLoading ? '🔄 Scanning...' : '🔍 Scan for Matching URL'}
                </button>

                {/* Scan Results */}
                {scanResult && (
                  <div className={`p-6 rounded-lg border-2 ${
                    scanResult.status === 'match_found' 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-gray-50 border-gray-200'
                  }`}>
                    <h3 className="text-lg font-semibold mb-4">Scan Results</h3>
                    
                    {scanResult.status === 'match_found' ? (
                      <div className="space-y-3">
                        <p className="text-green-800 font-medium">
                          ✅ Match Found!
                        </p>
                        <div className="bg-white p-4 rounded border">
                          <p><strong>File:</strong> {scanResult.match.filename}</p>
                          <p><strong>URL:</strong> 
                            <a href={scanResult.match.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline ml-2">
                              {scanResult.match.url}
                            </a>
                          </p>
                          <p><strong>Similarity:</strong> {scanResult.match.similarity_percentage.toFixed(1)}%</p>
                          <p><strong>Algorithm:</strong> {scanResult.match.algorithm_used}</p>
                        </div>
                        <p className="text-sm text-gray-600">
                          🚀 The URL will open automatically in a new tab in 2 seconds...
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <p className="text-gray-700">
                          ❌ No matching images found
                        </p>
                        <p className="text-sm text-gray-600">
                          Searched through {scanResult.total_stored_images} stored images with threshold {scanResult.threshold_used}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* View Stored Images Tab */}
            {activeTab === 'view' && (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-2xl font-semibold text-gray-800">
                    Stored Image Links
                  </h2>
                  <button
                    onClick={fetchStoredImages}
                    disabled={isLoading}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
                  >
                    {isLoading ? '🔄' : '🔄 Refresh'}
                  </button>
                </div>

                {storedImages.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <p className="text-lg">No stored images yet</p>
                    <p>Link some images to URLs to see them here!</p>
                  </div>
                ) : (
                  <div className="grid gap-4">
                    {storedImages.map((image) => (
                      <div key={image.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h3 className="font-medium text-gray-800">{image.filename}</h3>
                            <p className="text-sm text-gray-600 mt-1">
                              <a href={image.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                {image.url}
                              </a>
                            </p>
                            <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
                              <span>📏 {image.image_size}</span>
                              <span>💾 {(image.file_size / 1024).toFixed(1)}KB</span>
                              <span>🕒 {new Date(image.created_at).toLocaleDateString()}</span>
                            </div>
                          </div>
                          <button
                            onClick={() => deleteImage(image.id)}
                            disabled={isLoading}
                            className="ml-4 px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50 transition-colors text-sm"
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Hidden canvas for image capture */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
}

export default App;