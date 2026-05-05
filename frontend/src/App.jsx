import { Outlet } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'

export default function App() {
  return (
    <div className="h-screen flex bg-surface text-on-surface">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col h-screen overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto bg-surface-container-low">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
