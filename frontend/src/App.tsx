import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Events } from "./pages/Events";
import { EventDetailPage } from "./pages/EventDetail";
import { InputSecurity } from "./pages/InputSecurity";
import { OutputSecurity } from "./pages/OutputSecurity";
import { Policies } from "./pages/Policies";
import { Applications } from "./pages/Applications";
import { Testing } from "./pages/Testing";
import { Settings } from "./pages/Settings";
import { Inspector } from "./pages/Inspector";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout title="Dashboard"><Dashboard /></Layout>} />
      <Route path="/events" element={<Layout title="Security Events"><Events /></Layout>} />
      <Route path="/events/:id" element={<Layout title="Security Event"><EventDetailPage /></Layout>} />
      <Route path="/inspector" element={<Layout title="Request Inspector"><Inspector /></Layout>} />
      <Route path="/inspector/:id" element={<Layout title="Request Inspector"><Inspector /></Layout>} />
      <Route path="/input-security" element={<Layout title="Input Security"><InputSecurity /></Layout>} />
      <Route path="/output-security" element={<Layout title="Output Security"><OutputSecurity /></Layout>} />
      <Route path="/policies" element={<Layout title="Policies"><Policies /></Layout>} />
      <Route path="/applications" element={<Layout title="Applications"><Applications /></Layout>} />
      <Route path="/testing" element={<Layout title="Security Testing"><Testing /></Layout>} />
      <Route path="/settings" element={<Layout title="Settings"><Settings /></Layout>} />
      <Route path="*" element={<Layout title="Not Found"><div className="empty">Page not found.</div></Layout>} />
    </Routes>
  );
}
