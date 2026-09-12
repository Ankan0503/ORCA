import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import { OrcaXponderAlert } from './components/alerts/OrcaXponderAlert';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    {/* A transponder warning must reach the fisherman on whatever screen is open. */}
    <OrcaXponderAlert />
  </StrictMode>,
);
