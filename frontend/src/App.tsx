import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './pages/Dashboard';
import UploadPage from './pages/Upload';
import ProgressPage from './pages/Progress';
import ReportPage from './pages/Report';

export default function App() {
    return (
        <BrowserRouter>
            <Layout>
                <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/upload" element={<UploadPage />} />
                    <Route path="/progress/:id" element={<ProgressPage />} />
                    <Route path="/report/:id" element={<ReportPage />} />
                </Routes>
            </Layout>
        </BrowserRouter>
    );
}
