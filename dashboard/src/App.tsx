import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Machines from './pages/Machines';
import Alerts from './pages/Alerts';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

const DRAWER_WIDTH = 240;

export default function App() {
  return (
    <Box display="flex" minHeight="100vh" bgcolor="background.default">
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          ml: `${DRAWER_WIDTH}px`,
          p: 3,
          minHeight: '100vh',
        }}
      >
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/machines" element={<Machines />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Box>
    </Box>
  );
}