import { useState, useEffect } from 'react';

export default function App() {
  const [backendData, setBackendData] = useState("Attempting to contact Pitch.io backend ...")

  useEffect(() => {
    // Firing request to Python server
    // URL can be changed to hit specific endpoints
    fetch('http://127.0.0.1:8000/')
      .then(response => {
        if(!response.ok) throw new Error("Network response was not ok");
        return response.json();
      })
      .then(data => {
        // If successfull, we turn the raw JSON into a string and display it
        setBackendData(JSON.stringify(data, null, 2));
      }) 
      .catch(error => {
        // If it fails, we catch the error so that the app doesn't crash
        setBackendData("Connection Failed: " + error.message);
      });
  }, []); // Only runs once

  return (
    <div className='min-h-screen bg-black text-green-500 p-8 font-mono'>
      <h1 className='text-xl mb-4 text-white'>API Radar Ping:</h1>
      <pre className='bg-slate-900 p-4 rounded-lg overflow-x-auto border border-green-500/30'>
      {backendData}
      </pre>
    </div>
  )
}