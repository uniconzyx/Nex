import React from 'react';
import { createRoot } from 'react-dom/client';
import CacheDesignLab from '../mw-ch04/CacheDesignLab';

const root = createRoot(document.getElementById('root')!);
root.render(
  <React.StrictMode>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '22px 18px 40px' }}>
      <CacheDesignLab />
    </div>
  </React.StrictMode>,
);
