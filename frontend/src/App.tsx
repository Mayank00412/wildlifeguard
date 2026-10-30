import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { VideosPage } from './pages/VideosPage'
import { UploadPage } from './pages/UploadPage'
import { VideoAnalysisPage } from './pages/VideoAnalysisPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { AnimalsPage } from './pages/AnimalsPage'
import { RiskEventsPage } from './pages/RiskEventsPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/videos" element={<VideosPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/animals" element={<AnimalsPage />} />
          <Route path="/risk-events" element={<RiskEventsPage />} />
          <Route path="/analysis/:videoId" element={<VideoAnalysisPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}
