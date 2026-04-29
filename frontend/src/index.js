/**
 * React entry point. Mounts &lt;App /&gt; into the #root element and wires up
 * the optional Create React App web-vitals reporter.
 *
 * @module index
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

reportWebVitals();
